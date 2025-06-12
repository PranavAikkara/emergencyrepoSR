from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from typing import List, Dict, Any, Optional
import uvicorn
import asyncio
import uuid
from contextlib import asynccontextmanager

# Updated imports from new module structure - direct imports from specific modules
from src.vector_db.vectordb_client import (
    JD_COLLECTION_NAME, 
    CV_COLLECTION_NAME, 
    initialize_qdrant_collections,
    get_full_document_text_from_db
)
from src.vector_db.jd_repository import add_jd_to_db
from src.vector_db.cv_repository import add_cv_to_db
from src.services.jd_service import parse_jd_with_llm
from src.services.cv_service import parse_cv_with_llm as parse_cv_with_llm
from src.services.ranking_service import calculate_cv_ranking
from src.services.question_service import generate_candidate_questions as core_generate_questions
from src.utils.logging import get_logger
from src.utils.s3_handler import s3_handler

# Import the schema models from new location
from src.schemas.api_schemas import (
    JDUploadResponse, 
    CVUploadResponse, 
    RankingRequest, 
    RankingResponse,
    RankingResult,
    QuestionGenerationRequest, 
    QuestionGenerationResponse,
    Question,
    S3JDUploadRequest,
    S3CVUploadRequest,
)

# Setup logger
logger = get_logger(__name__)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup event
    logger.info("Application startup: Initializing Qdrant collections...")
    await initialize_qdrant_collections()
    logger.info("Qdrant collections initialization complete.")
    yield
    # Shutdown event (if any cleanup needed in the future)
    logger.info("Application shutdown.")

app = FastAPI(
    title="Smart Recruit API", 
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS to allow requests from your Streamlit app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to your Streamlit URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint to check if API is running"""
    return {"message": "Smart Recruit API is running"}

# S3-based JD endpoint
@app.post("/s3-upload-jd", response_model=JDUploadResponse, operation_id="s3_upload_jd")
async def s3_upload_jd(request: S3JDUploadRequest):
    """Upload and process JD from S3 path"""
    try:
        logger.info(f"Processing JD from S3: {request.s3_uri}")
        
        # Get file from S3
        s3_file_data = await s3_handler.get_file_from_s3(request.s3_uri)
        
        if s3_file_data.get("error"):
            logger.error(f"S3 file processing error for JD {s3_file_data.get('filename')}: {s3_file_data.get('error')}")
            raise HTTPException(status_code=400, detail=s3_file_data.get("error"))

        filename = s3_file_data["filename"]
        raw_text = s3_file_data["raw_text_content"]
        base64_encoded = s3_file_data["base64_content"]
        actual_content_type = s3_file_data["content_type"]
        
        jd_id = await add_jd_to_db(
            jd_base64_content=base64_encoded,
            jd_raw_text_content=raw_text,
            content_type=actual_content_type,
            jd_specific_metadata={
                "original_filename": filename,
                "source_s3_uri": request.s3_uri,
                "source_bucket": s3_file_data["bucket"],
                "source_key": s3_file_data["key"],
                "file_size_mb": s3_file_data["file_size_mb"]
            }
        )
        
        if not jd_id:
            logger.error(f"Failed to add JD to vector DB: {filename}")
            raise HTTPException(status_code=500, detail="Failed to add JD to vector DB")
        
        logger.info(f"Parsing JD with LLM for structured data: {filename}")
        jd_data_from_llm = await parse_jd_with_llm(
            jd_base64_content=base64_encoded,
            jd_raw_text_content=raw_text,
            content_type=actual_content_type
        )

        if "error" in jd_data_from_llm:
            logger.warning(f"LLM parsing for JD {filename} resulted in an error or no data: {jd_data_from_llm.get('error')}")
            return JDUploadResponse(jd_id=jd_id, filename=filename, jd_data=jd_data_from_llm)

        logger.info(f"JD processing successful (DB & LLM) from S3: {filename}, JD ID: {jd_id}")
        return JDUploadResponse(jd_id=jd_id, filename=filename, jd_data=jd_data_from_llm)

    except HTTPException as http_exc:
        raise http_exc
    except ValueError as val_err:
        # S3-specific errors (invalid S3 URI, access errors, etc.)
        logger.error(f"S3 validation error in /s3-upload-jd: {str(val_err)}")
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error processing JD from S3 in /s3-upload-jd endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing JD from S3: {str(e)}")

# S3-based CV endpoint
@app.post("/s3-upload-cv", response_model=CVUploadResponse, operation_id="s3_upload_cv")
async def s3_upload_cv(request: S3CVUploadRequest):
    """Upload and process single CV from S3 path"""
    try:
        logger.info(f"Processing CV from S3: {request.s3_uri} for JD ID: {request.jd_id}")
        
        if not request.jd_id:
            logger.error("S3 CV upload endpoint called without jd_id.")
            raise HTTPException(status_code=400, detail="jd_id is required.")
        
        # Get file from S3
        s3_file_data = await s3_handler.get_file_from_s3(request.s3_uri)
        
        if s3_file_data.get("error"):
            logger.error(f"S3 file processing error for CV {s3_file_data.get('filename')}: {s3_file_data.get('error')}")
            raise HTTPException(status_code=400, detail=s3_file_data.get("error"))

        filename = s3_file_data["filename"]
        raw_text = s3_file_data["raw_text_content"]
        base64_encoded = s3_file_data["base64_content"]
        actual_content_type = s3_file_data["content_type"]
        
        # Use the existing CV processing logic with retry mechanism
        cv_id_generated = str(uuid.uuid4())
        max_attempts = 2
        retry_delay_seconds = 3

        last_error_for_response = "Processing failed after all attempts."
        last_cv_data_for_response = {"error": last_error_for_response}
        db_add_successful_last_attempt = False

        for attempt in range(max_attempts):
            logger.info(f"Processing CV from S3: {filename}, CV ID: {cv_id_generated}, JD ID: {request.jd_id}, Attempt: {attempt + 1}/{max_attempts}")
            current_attempt_error = None
            cv_data_from_llm_this_attempt = None
            db_add_successful_this_attempt = False

            try:
                # Step 1: Add to DB
                db_add_result_cv_id = await add_cv_to_db(
                    cv_base64_content=base64_encoded,
                    cv_raw_text_content=raw_text,
                    content_type=actual_content_type,
                    cv_metadata_with_links={
                        "original_doc_id": cv_id_generated,
                        "associated_jd_id": request.jd_id,
                        "original_filename": filename,
                        "source_s3_uri": request.s3_uri,
                        "source_bucket": s3_file_data["bucket"],
                        "source_key": s3_file_data["key"],
                        "file_size_mb": s3_file_data["file_size_mb"]
                    }
                )
                
                if not db_add_result_cv_id:
                    current_attempt_error = "Failed to add CV to vector DB."
                    logger.error(f"{current_attempt_error} - Filename: {filename} (Attempt {attempt + 1})")
                else:
                    db_add_successful_this_attempt = True
                    db_add_successful_last_attempt = True
                    logger.info(f"CV added to DB successfully from S3: {filename}, CV ID: {cv_id_generated} (Attempt {attempt + 1})")

                    # Step 2: Parse with LLM
                    llm_parse_result_dict = await parse_cv_with_llm( 
                        cv_base64_content=base64_encoded,
                        cv_raw_text_content=raw_text,
                        content_type=actual_content_type
                    )
                    cv_data_from_llm_this_attempt = llm_parse_result_dict.get("structured_data")

                    if not cv_data_from_llm_this_attempt or (isinstance(cv_data_from_llm_this_attempt, dict) and "error" in cv_data_from_llm_this_attempt):
                        llm_error_msg = cv_data_from_llm_this_attempt.get('error', 'Unknown LLM parsing error') if isinstance(cv_data_from_llm_this_attempt, dict) else "LLM parsing returned no data"
                        current_attempt_error = f"LLM Parsing Error: {llm_error_msg}"
                        logger.warning(f"{current_attempt_error} for {filename} (Attempt {attempt + 1})")
                    else:
                        logger.info(f"CV processing fully successful on attempt {attempt + 1} for {filename} from S3")
                        return CVUploadResponse(cv_id=cv_id_generated, success=True, filename=filename,
                                                cv_data=cv_data_from_llm_this_attempt, error=None)
            except Exception as e:
                current_attempt_error = f"Unexpected exception: {str(e)}"
                logger.error(f"{current_attempt_error} during CV processing from S3: {filename} (Attempt {attempt + 1})", exc_info=True)
                if not cv_data_from_llm_this_attempt: 
                    cv_data_from_llm_this_attempt = {"error": current_attempt_error}

            last_error_for_response = current_attempt_error or "Unknown error in attempt."
            last_cv_data_for_response = cv_data_from_llm_this_attempt if cv_data_from_llm_this_attempt else {"error": last_error_for_response}
            
            if attempt < max_attempts - 1:
                logger.info(f"Attempt {attempt + 1} failed for {filename} from S3. Error: {last_error_for_response}. Retrying in {retry_delay_seconds}s...")
                await asyncio.sleep(retry_delay_seconds)
            else:
                logger.error(f"All {max_attempts} attempts failed for CV {filename} from S3. Last error: {last_error_for_response}")
                if db_add_successful_last_attempt and "LLM Parsing Error" in last_error_for_response:
                    return CVUploadResponse(cv_id=cv_id_generated, 
                                           success=False, 
                                           filename=filename,
                                           cv_data=last_cv_data_for_response, 
                                           error=last_error_for_response)
                return CVUploadResponse(cv_id=cv_id_generated, success=False, filename=filename,
                                       cv_data=last_cv_data_for_response, error=last_error_for_response)
        
        # Fallback
        return CVUploadResponse(cv_id=cv_id_generated, success=False, filename=filename, 
                               cv_data=last_cv_data_for_response, error=last_error_for_response)

    except HTTPException as http_exc:
        raise http_exc
    except ValueError as val_err:
        # S3-specific errors (invalid S3 URI, access errors, etc.)
        logger.error(f"S3 validation error in /s3-upload-cv: {str(val_err)}")
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error processing CV from S3 in /s3-upload-cv endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing CV from S3: {str(e)}")

@app.post("/rank-cvs", response_model=RankingResponse, operation_id="rank_cvs")
async def rank_cvs(request: RankingRequest):
    """Rank CVs against a job description using vector similarity and LLM reasoning."""
    logger.info(f"Received ranking request for JD ID: {request.jd_id} with {len(request.cv_ids)} CVs.")
    try:
        jd_id = request.jd_id
        cv_ids_from_request = request.cv_ids
        top_n_to_rank = request.top_n
        
        if not jd_id or not cv_ids_from_request:
            logger.warning("Missing jd_id or cv_ids in ranking request.")
            raise HTTPException(status_code=400, detail="Missing jd_id or cv_ids")
        
        cv_details_for_ranking = []
        for cv_id_str in cv_ids_from_request:
            cv_details_for_ranking.append({
                "cv_id": cv_id_str,
                "filename": f"CV_{cv_id_str}", 
                "llm_data": None 
            })

        logger.info(f"Calling calculate_cv_ranking for JD ID: {jd_id}")
        ranked_cv_data = await calculate_cv_ranking(
            current_jd_id=jd_id,
            active_session_cvs=cv_details_for_ranking,
            top_n=top_n_to_rank
        )
        
        if ranked_cv_data is None:
            logger.error(f"calculate_cv_ranking returned None for JD ID: {jd_id}. Ranking failed.")
            return RankingResponse(rankings=[]) 

        final_rankings_for_api = []
        for cv_rank_item in ranked_cv_data:
            final_rankings_for_api.append(
                RankingResult(
                    cv_id=cv_rank_item.get("cv_id", "unknown_cv_id"),
                    score=float(cv_rank_item.get("llm_ranking_score", 0.0)),
                    evaluation={
                        "filename": cv_rank_item.get("filename", "N/A"),
                        "initial_vector_score": cv_rank_item.get("initial_vector_score", 0.0),
                        "vector_match_details": cv_rank_item.get("vector_match_details", "N/A"),
                        "llm_skills_evaluation": cv_rank_item.get("llm_skills_evaluation", []),
                        "llm_experience_evaluation": cv_rank_item.get("llm_experience_evaluation", []),
                        "llm_additional_points": cv_rank_item.get("llm_additional_points", []),
                        "llm_overall_assessment": cv_rank_item.get("llm_overall_assessment", "N/A")
                    }
                )
            )

        logger.info(f"Successfully ranked {len(final_rankings_for_api)} CVs for JD ID: {jd_id}.")
        return RankingResponse(rankings=final_rankings_for_api)

    except HTTPException as http_exc:
        logger.error(f"HTTPException in rank_cvs for JD ID {request.jd_id if request else 'unknown'}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in rank_cvs for JD ID {request.jd_id if request else 'unknown'}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error ranking CVs: {str(e)}")

@app.post("/generate-questions", response_model=QuestionGenerationResponse, operation_id="generate_questions")
async def generate_questions(request: QuestionGenerationRequest):
    """Generate interview questions based on JD and selected CV."""
    logger.info(f"Received request to generate questions for JD ID: {request.jd_id} and CV ID: {request.cv_id}")
    try:
        jd_id = request.jd_id
        cv_id = request.cv_id
        
        if not jd_id or not cv_id:
            logger.warning("Missing jd_id or cv_id in generate_questions request.")
            raise HTTPException(status_code=400, detail="Missing jd_id or cv_id")
        
        logger.info(f"Fetching full JD text for ID: {jd_id}")
        full_jd_text = await get_full_document_text_from_db(jd_id, JD_COLLECTION_NAME())
        if not full_jd_text:
            logger.error(f"Could not retrieve full JD text for ID: {jd_id}. Cannot generate questions.")
            raise HTTPException(status_code=404, detail=f"JD text not found for ID: {jd_id}")

        logger.info(f"Fetching full CV text for ID: {cv_id}")
        full_cv_text = await get_full_document_text_from_db(cv_id, CV_COLLECTION_NAME())
        if not full_cv_text:
            logger.error(f"Could not retrieve full CV text for ID: {cv_id}. Cannot generate questions.")
            raise HTTPException(status_code=404, detail=f"CV text not found for ID: {cv_id}")
        
        logger.info(f"Calling core_generate_questions for CV ID: {cv_id}")
        candidate_questions_output = await core_generate_questions(
            jd_text=full_jd_text,
            cv_text=full_cv_text,
            candidate_name_or_id=cv_id
        )

        if not candidate_questions_output or (not candidate_questions_output.technical_questions and not candidate_questions_output.general_behavioral_questions):
            logger.warning(f"core_generate_questions returned no questions for CV ID: {cv_id}.")
            return QuestionGenerationResponse(technical_questions=[], general_behavioral_questions=[])
        
        api_technical_questions = []
        if candidate_questions_output.technical_questions:
            for q_item in candidate_questions_output.technical_questions:
                api_technical_questions.append(Question(
                    question=q_item.question,
                    category=q_item.category,
                    good_answer_pointers=q_item.good_answer_pointers,
                    unsure_answer_pointers=q_item.unsure_answer_pointers,
                    rationale=None 
                ))
        
        api_general_questions = []
        if candidate_questions_output.general_behavioral_questions:
            for q_item in candidate_questions_output.general_behavioral_questions:
                api_general_questions.append(Question(
                    question=q_item.question,
                    category=q_item.category,
                    good_answer_pointers=q_item.good_answer_pointers,
                    unsure_answer_pointers=q_item.unsure_answer_pointers,
                    rationale=None 
                ))
        
        logger.info(f"Successfully processed questions for CV ID: {cv_id}. Technical: {len(api_technical_questions)}, General: {len(api_general_questions)}.")
        return QuestionGenerationResponse(
            cv_id=cv_id,
            jd_id=jd_id,
            technical_questions=api_technical_questions, 
            general_behavioral_questions=api_general_questions
        )

    except HTTPException as http_exc:
        logger.error(f"HTTPException in generate_questions for JD ID {request.jd_id}, CV ID {request.cv_id}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in generate_questions for JD ID {request.jd_id}, CV ID {request.cv_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error generating questions: {str(e)}")

wiserecruit = FastApiMCP(app, include_operations=["s3_upload_jd", "s3_upload_cv", "rank_cvs", "generate_questions"])
wiserecruit.mount()

if __name__ == "__main__":
    uvicorn.run("routes:app", host="127.0.0.1", port=8000, reload=True) 