"""
Ranking service for comparing CVs against job descriptions.

This module provides:
1. Functions for comparing CVs against JDs using LLM
2. CV ranking and scoring logic
"""

import json
import litellm
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from src.llm.llmclient import get_litellm_params
from src.schemas.schemas import LLMJdCvComparisonOutput
from src.vector_db.vectordb_client import JD_COLLECTION_NAME, CV_COLLECTION_NAME
from src.vector_db.jd_repository import get_jd_chunks, get_full_jd_text
from src.vector_db.cv_repository import get_cv_chunks, get_full_cv_text, search_cv_chunks
from src.utils.logging import get_logger

logger = get_logger(__name__)

async def get_llm_comparison_for_cv(
    jd_text: str, 
    cv_text: str, 
    cv_id: str
) -> Optional[LLMJdCvComparisonOutput]:
    """
    Uses an LLM to compare a single CV against a JD and provide structured reasoning.

    Args:
        jd_text: The full text of the Job Description.
        cv_text: The full text of the Curriculum Vitae.
        cv_id: The ID of the CV.

    Returns:
        An LLMJdCvComparisonOutput object with matched/unmatched points, or None on error.
    """
    from src.llm.utils import load_prompt
    
    try:
        comparison_prompt_template = load_prompt("src/prompts/cv_ranking_prompt.md")
    except Exception as e:
        logger.error(f"Error loading JD-CV comparison prompt: {e}")
        return None

    prompt = comparison_prompt_template.replace("{{JD_TEXT}}", jd_text)
    prompt = prompt.replace("{{CV_TEXT}}", cv_text)
    prompt = prompt.replace("{{CV_ID}}", cv_id)

    try:
        # Using the default model from config.py
        llm_params = get_litellm_params(model_alias="gemini_2_5_flash_preview") 
        
        # Ensure response_format for JSON is correctly set
        llm_params_for_json = {**llm_params, "response_format": {"type": "json_object"}}

        logger.info(f"Calling LLM for JD-CV comparison for CV ID: {cv_id}. Model: {llm_params.get('model')}")
        response = await litellm.acompletion(
            **llm_params_for_json,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_content = response.choices[0].message.content
        if not response_content:
            logger.error(f"LLM returned empty content for CV ID: {cv_id}")
            return None

        # Parse the JSON string into our Pydantic model
        llm_output_data = json.loads(response_content)
        comparison_result = LLMJdCvComparisonOutput(**llm_output_data)
        
        # Ensure the cv_id from LLM matches the one we sent, as a sanity check.
        if comparison_result.cv_id != cv_id:
            logger.warning(f"Warning: LLM output cv_id '{comparison_result.cv_id}' does not match expected '{cv_id}'. Using expected.")
            # Correct it or handle as an error. For now, we can overwrite it to be sure.
            comparison_result.cv_id = cv_id 
            
        return comparison_result

    except json.JSONDecodeError as json_e:
        logger.error(f"Error decoding LLM JSON response for CV ID {cv_id}: {json_e}")
        logger.error(f"LLM Raw Response: {response_content[:500]}...")
        return None
    except Exception as e:
        logger.error(f"Error during LLM comparison for CV ID {cv_id}: {type(e).__name__} - {e}")
        return None

async def calculate_cv_ranking(
    current_jd_id: str,
    active_session_cvs: List[Dict[str, Any]],
    top_n: Optional[int] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Calculates CV rankings: 
    1. Vector similarity to get top N CVs (SKIPPED if ranking all CVs).
    2. LLM-based reasoning for the selected CVs against the JD.

    OPTIMIZATION: If top_n >= total_cvs, skip vector similarity stage entirely
    and proceed directly to LLM evaluation for all CVs.

    Args:
        current_jd_id: ID of the job description to rank CVs against
        active_session_cvs: List of CV information dictionaries
        top_n: Maximum number of CVs to rank (None for all)
        
    Returns:
        A list of the ranked CVs, augmented with LLM reasoning,
        or None if critical errors occur.
    """
    logger.info("Starting CV ranking process.")
    if not active_session_cvs:
        logger.warning("No active CVs to rank.")
        return []

    jd_collection_name = JD_COLLECTION_NAME()
    cv_collection_name = CV_COLLECTION_NAME()

    cv_id_to_filename = {cv_info["cv_id"]: cv_info.get("filename", f"CV_{cv_info['cv_id']}") for cv_info in active_session_cvs}
    active_cv_ids = list(cv_id_to_filename.keys())

    if not active_cv_ids:
        logger.error("No CV IDs extracted from active_session_cvs.")
        return []

    total_cvs = len(active_cv_ids)
    
    # OPTIMIZATION: Skip vector similarity if ranking ALL CVs
    if top_n is None or top_n >= total_cvs:
        logger.info(f"🚀 OPTIMIZATION: Ranking ALL {total_cvs} CVs - skipping vector similarity stage for faster processing")
        
        # Create initial ranking with neutral scores for all CVs
        top_cvs_for_llm_stage = []
        for cv_info in active_session_cvs:
            top_cvs_for_llm_stage.append({
                "cv_id": cv_info["cv_id"],
                "filename": cv_info.get("filename", f"CV_{cv_info['cv_id']}"),
                "initial_vector_score": 0.5,  # Neutral score since we're skipping vector similarity
                "vector_match_details": "Skipped vector similarity - ranking all CVs for efficiency",
                "raw_total_score": 0.0,
                "match_count": 0
            })
        
        logger.info(f"Proceeding directly to LLM evaluation for all {total_cvs} CVs")
        
    else:
        # Use existing vector similarity logic for selective ranking
        logger.info(f"Performing vector similarity ranking to select top {top_n} from {total_cvs} CVs")
        
        # --- Stage 1: Vector Similarity Ranking ---
        jd_chunks = await get_jd_chunks(current_jd_id)
        if not jd_chunks:
            logger.error(f"Failed to retrieve JD chunks for JD ID: {current_jd_id}")
            return None

        cv_scores_aggregator: Dict[str, Dict[str, Any]] = {
            cv_id: {"total_score": 0.0, "max_weighted_contribution": 0.0, "match_count": 0, "filename": cv_id_to_filename[cv_id], "explanation_details": []}
            for cv_id in active_cv_ids
        }
        
        TOP_K_CV_CHUNKS_PER_JD_CHUNK = 15

        # Detailed logging for Stage 1
        logger.info(f"[Ranking Stage 1 - Analysis] Starting Stage 1 for JD ID: {current_jd_id}. CVs to consider: {active_cv_ids}")

        for jd_chunk_index, jd_chunk in enumerate(jd_chunks):
            jd_chunk_text = jd_chunk.get("enriched_text", "")
            jd_chunk_weight = jd_chunk.get("weight", 1)
            if not isinstance(jd_chunk_weight, int) or not (1 <= jd_chunk_weight <= 3):
                jd_chunk_weight = 1 # Defaulting already handled
            
            logger.info(f"[Ranking Stage 1 - Analysis] Processing JD Chunk {jd_chunk_index+1}/{len(jd_chunks)} (Weight: {jd_chunk_weight}): '{jd_chunk_text[:150]}...'")

            if not jd_chunk_text.strip():
                logger.warning(f"[Ranking Stage 1] JD Chunk {jd_chunk_index+1} is empty or whitespace, skipping search.")
                continue
            
            cv_chunk_matches = await search_cv_chunks(
                query_text=jd_chunk_text,
                top_k=TOP_K_CV_CHUNKS_PER_JD_CHUNK, 
                filter_by_doc_ids=active_cv_ids 
            )

            logger.info(f"[Ranking Stage 1] For JD Chunk {jd_chunk_index+1}, found {len(cv_chunk_matches)} CV chunk matches.")

            for i, cv_match in enumerate(cv_chunk_matches):
                matched_cv_id = cv_match.get("original_doc_id")
                match_score = cv_match.get("_score", 0.0)
                
                if matched_cv_id and matched_cv_id in cv_scores_aggregator:
                    weighted_score_contribution = (match_score ** 2) * jd_chunk_weight
                    cv_scores_aggregator[matched_cv_id]["total_score"] += weighted_score_contribution
                    cv_scores_aggregator[matched_cv_id]["match_count"] += 1
                    # Update the maximum weighted contribution if the current one is higher
                    if weighted_score_contribution > cv_scores_aggregator[matched_cv_id]["max_weighted_contribution"]:
                        cv_scores_aggregator[matched_cv_id]["max_weighted_contribution"] = weighted_score_contribution
                    
                    # Log detailed match info for analysis
                    logger.info(f"[Ranking Stage 1 - Analysis] Match for JD Chunk {jd_chunk_index+1} (Weight: {jd_chunk_weight}): "
                                f"CV ID: {matched_cv_id} (File: {cv_scores_aggregator[matched_cv_id].get('filename', 'N/A')}), "
                                f"Raw Score: {match_score:.4f}, Weighted Contribution: {weighted_score_contribution:.4f}, "
                                f"CV Chunk Enriched Text: '{cv_match.get('enriched_text', '')[:100]}...'")

                    if len(cv_scores_aggregator[matched_cv_id]["explanation_details"]) < 3: 
                        cv_scores_aggregator[matched_cv_id]["explanation_details"].append(
                            f"JD chunk {jd_chunk_index+1} (weight: {jd_chunk_weight}) matched CV (raw score: {match_score:.3f})"
                        )
        
        initial_ranked_cvs = []
        logger.info("[Ranking Stage 1 - Analysis] Final Aggregated Scores before primary sorting (by max_weighted_contribution):")
        for cv_id_log, data_log in cv_scores_aggregator.items():
            logger.info(f"[Ranking Stage 1 - Analysis] CV ID: {cv_id_log} (File: {data_log.get('filename', 'N/A')}), "
                        f"Max Weighted Contribution: {data_log['max_weighted_contribution']:.4f}, "
                        f"Total Weighted Score (for info): {data_log['total_score']:.4f}, Match Count: {data_log['match_count']}")

        for cv_id, data in cv_scores_aggregator.items():
            initial_ranked_cvs.append({
                "cv_id": cv_id,
                "filename": data["filename"],
                "initial_vector_score": data["max_weighted_contribution"], # Primary score for Stage 1
                "vector_match_details": f"Max contribution score. Aggregated from {data['match_count']} vector matches. Details: {'; '.join(data['explanation_details'])}",
                "raw_total_score": data["total_score"], # Keep for info
                "match_count": data["match_count"] # Keep for info
            })

        initial_ranked_cvs.sort(key=lambda x: x["initial_vector_score"], reverse=True)
        
        # Use the provided top_n for selective ranking
        num_llm_candidates = top_n if top_n is not None and top_n > 0 else 5
        top_cvs_for_llm_stage = initial_ranked_cvs[:num_llm_candidates]

        if not top_cvs_for_llm_stage:
            logger.warning("No CVs found after initial vector ranking stage.")
            return []

    # --- Stage 2: LLM Reasoning for Top N CVs ---
    async def _get_llm_reasoning_for_single_cv_task(cv_data_item: Dict[str, Any], jd_full_text: str, collection_name_cv: str) -> Dict[str, Any]:
        """Async helper to get LLM reasoning for one CV and augment its data."""
        cv_id = cv_data_item["cv_id"]
        augmented_cv_data_item = {**cv_data_item} # Work on a copy

        full_cv_text = await get_full_cv_text(cv_id)
        if not full_cv_text:
            logger.error(f"Failed to get full CV text for {cv_id}. Skipping LLM reasoning for this CV.")
            augmented_cv_data_item["llm_skills_evaluation"] = ["Error: Could not retrieve full CV text."]
            augmented_cv_data_item["llm_experience_evaluation"] = []
            augmented_cv_data_item["llm_additional_points"] = []
            augmented_cv_data_item["llm_overall_assessment"] = "N/A: Could not retrieve full CV text."
            augmented_cv_data_item["llm_ranking_score"] = 0.0
        else:
            logger.info(f"Performing LLM comparison for CV: {cv_id}")
            llm_reasoning = await get_llm_comparison_for_cv(jd_full_text, full_cv_text, cv_id)
            if llm_reasoning:
                augmented_cv_data_item["llm_skills_evaluation"] = llm_reasoning.skills_evaluation
                augmented_cv_data_item["llm_experience_evaluation"] = llm_reasoning.experience_evaluation
                augmented_cv_data_item["llm_additional_points"] = llm_reasoning.additional_points
                augmented_cv_data_item["llm_overall_assessment"] = llm_reasoning.overall_assessment
                augmented_cv_data_item["llm_ranking_score"] = llm_reasoning.llm_ranking_score if llm_reasoning.llm_ranking_score is not None else 0.0
            else:
                logger.error(f"LLM reasoning failed for CV: {cv_id}")
                augmented_cv_data_item["llm_skills_evaluation"] = ["Error: LLM reasoning failed."]
                augmented_cv_data_item["llm_experience_evaluation"] = []
                augmented_cv_data_item["llm_additional_points"] = []
                augmented_cv_data_item["llm_overall_assessment"] = "N/A: LLM reasoning failed."
                augmented_cv_data_item["llm_ranking_score"] = 0.0
                
        return augmented_cv_data_item

    # Get full JD text for LLM reasoning
    jd_full_text = await get_full_jd_text(current_jd_id)
    if not jd_full_text:
        logger.error(f"Failed to get full JD text for {current_jd_id}. Cannot perform LLM reasoning.")
        return top_cvs_for_llm_stage # Return the vector similarity results only
        
    # Process each CV with LLM reasoning
    llm_reasoning_tasks = []
    for cv_data in top_cvs_for_llm_stage:
        llm_reasoning_tasks.append(_get_llm_reasoning_for_single_cv_task(cv_data, jd_full_text, cv_collection_name))
        
    # Wait for all LLM reasoning tasks to complete
    llm_augmented_cv_data = await asyncio.gather(*llm_reasoning_tasks)
    
    # Sort by LLM ranking score (descending)
    final_ranked_cvs = sorted(llm_augmented_cv_data, key=lambda x: x.get("llm_ranking_score", 0.0), reverse=True)
    
    logger.info(f"CV ranking completed. Ranked {len(final_ranked_cvs)} CVs.")
    return final_ranked_cvs 