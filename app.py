import streamlit as st
from src.services.jd_service import parse_jd_with_llm
from src.services.cv_service import process_multiple_cvs
from src.vector_db.vectordb_client import (
    get_qdrantchunk_content, 
    search_similar_chunks, 
    JD_COLLECTION_NAME, 
    CV_COLLECTION_NAME, 
    get_full_document_text_from_db
)
from src.vector_db.jd_repository import add_jd_to_db
from src.vector_db.cv_repository import add_cv_to_db
import uuid
import asyncio
import numpy as np
from src.services.ranking_service import calculate_cv_ranking
from src.services.question_service import generate_candidate_questions
import requests
from src.utils.logging import get_logger

logger = get_logger(__name__)

API_BASE_URL = "http://localhost:8000"

st.set_page_config(layout="wide")

st.sidebar.title("🚀 Smart Recruiter Assistant")

# Initialize session state (ensure all keys are initialized here)
if 'jd_llm_output' not in st.session_state: st.session_state.jd_llm_output = None
if 'jd_vector_db_status' not in st.session_state: st.session_state.jd_vector_db_status = None
if 'current_jd_id' not in st.session_state: st.session_state.current_jd_id = None
if 'jd_file_name' not in st.session_state: st.session_state.jd_file_name = None
if 'active_session_cvs' not in st.session_state: st.session_state.active_session_cvs = []
if 'displayed_cv_processing_statuses' not in st.session_state: st.session_state.displayed_cv_processing_statuses = []
if 'cv_results' not in st.session_state: st.session_state.cv_results = None
if 'cv_vector_db_status' not in st.session_state: st.session_state.cv_vector_db_status = {}
if 'last_ranking_cv_count' not in st.session_state: st.session_state.last_ranking_cv_count = 0
if 'ranking_results' not in st.session_state: st.session_state.ranking_results = None
if 'selected_tab' not in st.session_state: st.session_state.selected_tab = "JD Processing"
if 'generated_questions_for_candidate' not in st.session_state: st.session_state.generated_questions_for_candidate = {}

# Sidebar Navigation
st.session_state.selected_tab = st.sidebar.radio(
    "Navigation",
    ["JD Processing", "CV Processing & Matching", "Ranking Results", "Candidate Questions"],
    key="sidebar_nav_radio"
)

st.title("📄 JD & CV Parser & Matcher")
st.write("""
Welcome! Use the sidebar to navigate through JD processing, CV uploading/matching, and ranking.
""")

# --- Tab 1: JD Processing ---
if st.session_state.selected_tab == "JD Processing":
    st.header("1. Job Description (JD) Processing")
    
    st.subheader("☁️ S3 Path Upload")
    s3_jd_uri = st.text_input("S3 URI for JD document", placeholder="s3://bucket-name/folder/jd.pdf", key="s3_jd_uri_input")

    # Check if S3 URI is provided
    use_s3_jd = bool(s3_jd_uri and s3_jd_uri.strip())
    
    if not use_s3_jd:
        st.info("📝 Please provide an S3 URI to process a JD.")

    # Process JD based on S3 input
    if use_s3_jd:
        current_jd_identifier = s3_jd_uri
        
        if st.session_state.jd_file_name != current_jd_identifier:
            st.session_state.jd_llm_output = None
            st.session_state.jd_vector_db_status = None
            st.session_state.current_jd_id = None
            st.session_state.active_session_cvs = []
            st.session_state.cv_results = None
            st.session_state.cv_vector_db_status = {}
            st.session_state.ranking_results = None
            st.session_state.generated_questions_for_candidate = {}
            st.session_state.jd_file_name = current_jd_identifier

        button_text = "Parse JD from S3 & Add to Knowledge Base"
        if st.button(button_text, key="parse_jd_button_main"):
            logger.info(f"User triggered JD processing via API using S3: {current_jd_identifier}")
            st.session_state.jd_llm_output = None
            st.session_state.jd_vector_db_status = None
            st.session_state.current_jd_id = None
            st.session_state.active_session_cvs = []
            st.session_state.ranking_results = None
            st.session_state.generated_questions_for_candidate = {}
            
            with st.spinner("Processing JD from S3 via Smart Recruit API..."):
                try:
                    # S3 processing
                    payload = {"s3_uri": s3_jd_uri.strip()}
                    response = requests.post(f"{API_BASE_URL}/s3-upload-jd", json=payload)
                    
                    response.raise_for_status()
                    
                    api_response_data = response.json()
                    jd_id = api_response_data.get("jd_id")
                    jd_llm_data = api_response_data.get("jd_data")

                    if jd_id:
                        st.session_state.current_jd_id = jd_id
                        db_status_msg = f"JD successfully processed via API (S3). Active JD ID: {jd_id}"
                        st.session_state.jd_vector_db_status = db_status_msg
                        logger.info(db_status_msg)
                        st.success(db_status_msg)

                        if jd_llm_data:
                            if "error" in jd_llm_data:
                                llm_error_msg = f"JD LLM Parsing Error (via API): {jd_llm_data.get('error')}"
                                st.session_state.jd_llm_output = jd_llm_data
                                logger.warning(llm_error_msg)
                            else:
                                st.session_state.jd_llm_output = jd_llm_data
                                logger.info(f"JD LLM data successfully retrieved via API for JD ID: {jd_id}")
                        else:
                            st.session_state.jd_llm_output = {"error": "LLM data not returned from API, but DB processing might be successful."}
                            logger.warning(f"LLM data not returned from API for JD ID: {jd_id}")
                    else:
                        error_detail = api_response_data.get("detail", "Unknown error from API")
                        st.session_state.jd_vector_db_status = f"Failed to process JD via API: {error_detail}"
                        st.session_state.jd_llm_output = {"error": f"API processing failed: {error_detail}"}
                        logger.error(st.session_state.jd_vector_db_status)
                        st.error(st.session_state.jd_vector_db_status)

                except requests.exceptions.HTTPError as http_err:
                    err_msg = f"HTTP error occurred: {http_err}. Response: {http_err.response.text if http_err.response else 'No response'}"
                    st.session_state.jd_vector_db_status = err_msg
                    st.session_state.jd_llm_output = {"error": err_msg}
                    logger.error(err_msg)
                    st.error(err_msg)
                except requests.exceptions.RequestException as req_err:
                    err_msg = f"Error connecting to API: {req_err}"
                    st.session_state.jd_vector_db_status = err_msg
                    st.session_state.jd_llm_output = {"error": err_msg}
                    logger.error(err_msg)
                    st.error(err_msg)
                except Exception as e:
                    err_msg = f"An unexpected error occurred: {e}"
                    st.session_state.jd_vector_db_status = err_msg
                    st.session_state.jd_llm_output = {"error": err_msg}
                    logger.error(err_msg)
                    st.error(err_msg)

    # Display JD Results within the JD tab
    if st.session_state.jd_llm_output:
        st.subheader("LLM Parsed JD Data:")
        if "error" in st.session_state.jd_llm_output:
            st.error(f"JD LLM Parsing Error: {st.session_state.jd_llm_output.get('error')}")
            if "raw_response" in st.session_state.jd_llm_output:
                st.expander("View JD Raw LLM Response").code(st.session_state.jd_llm_output['raw_response'])
        else:
            st.json(st.session_state.jd_llm_output)
    if st.session_state.jd_vector_db_status:
        status_color = "error" if "Failed" in st.session_state.jd_vector_db_status or "Error" in st.session_state.jd_vector_db_status else "success"
        getattr(st, status_color)(f"JD Knowledge Base Update: {st.session_state.jd_vector_db_status}")

# --- Tab 2: CV Processing & Matching ---
elif st.session_state.selected_tab == "CV Processing & Matching":
    st.header("2. Curriculum Vitae (CV) Processing & Matching")

    # Display current JD context if available
    if st.session_state.current_jd_id and st.session_state.jd_llm_output:
        with st.expander("Currently Active Job Description Summary", expanded=True):
            st.info(f"CVs uploaded below will be processed in context of JD ID: {st.session_state.current_jd_id}")
            jd_title = st.session_state.jd_llm_output.get("title", st.session_state.jd_llm_output.get("job_title", "N/A"))
            jd_company = st.session_state.jd_llm_output.get("company", st.session_state.jd_llm_output.get("company_name", "N/A"))
            st.markdown(f"**Title:** {jd_title}\n**Company:** {jd_company}")
    elif not st.session_state.current_jd_id:
        st.warning("No active JD. Please process a Job Description in the 'JD Processing' tab first.")

    st.subheader("☁️ S3 Path Upload")
    s3_cv_uri = st.text_input("S3 URI for CV document", placeholder="s3://bucket-name/folder/cv.pdf", key="s3_cv_uri_input", disabled=not st.session_state.current_jd_id)

    # Check if S3 URI is provided
    use_s3_cv = bool(s3_cv_uri and s3_cv_uri.strip())

    if not use_s3_cv:
        st.info("📝 Please provide an S3 URI to process a CV.")

    if use_s3_cv:
        button_text = "Parse CV from S3 & Add to DB"
        button_disabled = not st.session_state.current_jd_id or not s3_cv_uri.strip()

        if st.button(button_text, key="parse_cvs_button_main", disabled=button_disabled):
            logger.info(f"User triggered CV processing via API using S3 against JD ID: {st.session_state.current_jd_id}")
            
            # Results for the current batch to be added to the main display list
            current_batch_results_for_display = [] 
            current_batch_cv_info_for_active_list = [] 

            with st.spinner("Processing CV from S3 via Smart Recruit API..."):
                try:
                    # S3 processing
                    payload = {
                        "s3_uri": s3_cv_uri.strip(),
                        "jd_id": st.session_state.current_jd_id
                    }
                    response = requests.post(f"{API_BASE_URL}/s3-upload-cv", json=payload)
                    
                    response.raise_for_status() 
                    
                    # S3 returns single CV response, not a list
                    api_cv_response = response.json()

                    cv_filename = api_cv_response.get("filename", "Unknown Filename")
                    cv_id = api_cv_response.get("cv_id")
                    success = api_cv_response.get("success", False)
                    cv_llm_data = api_cv_response.get("cv_data") 
                    error_msg_from_api = api_cv_response.get("error")

                    current_cv_result_for_ui = {
                        "filename": cv_filename,
                        "structured_data": cv_llm_data if cv_llm_data else {"error": "No LLM data from API"},
                        "db_status_custom": "Unknown status"
                    }

                    if success: 
                        db_status_str = f"Added to DB. CV ID: {cv_id}"
                        if cv_llm_data and "error" in cv_llm_data:
                            db_status_str += f". LLM Parsing Error: {cv_llm_data.get('error')}"
                        
                        st.session_state.cv_vector_db_status[cv_filename] = db_status_str
                        current_cv_result_for_ui["db_status_custom"] = db_status_str
                        logger.info(f"CV API processing successful for: {cv_filename}, CV ID: {cv_id}")
                        
                        # Add to active_session_cvs for ranking
                        if not any(cv_entry['filename'] == cv_filename and cv_entry['cv_id'] == cv_id for cv_entry in st.session_state.active_session_cvs):
                            current_batch_cv_info_for_active_list.append({
                                "filename": cv_filename, 
                                "cv_id": cv_id, 
                                "llm_data": cv_llm_data if cv_llm_data and not (isinstance(cv_llm_data,dict) and "error" in cv_llm_data) else None 
                            })
                        
                        if cv_llm_data and isinstance(cv_llm_data,dict) and "error" in cv_llm_data:
                            logger.warning(f"LLM parsing error for {cv_filename} (via API), but DB add ok. LLM Error: {cv_llm_data.get('error')}")
                    else:
                        final_error_msg = error_msg_from_api if error_msg_from_api else "Processing failed via API (no specific error given)."
                        st.session_state.cv_vector_db_status[cv_filename] = final_error_msg
                        current_cv_result_for_ui["db_status_custom"] = final_error_msg
                        if not cv_llm_data or not (isinstance(cv_llm_data,dict) and "error" in cv_llm_data):
                            current_cv_result_for_ui["structured_data"] = {"error": final_error_msg}
                        logger.error(f"CV API processing failed for: {cv_filename}. Error: {final_error_msg}")
                    
                    # Add to current batch display list
                    current_batch_results_for_display.append(current_cv_result_for_ui)

                except requests.exceptions.HTTPError as http_err:
                    err_msg_batch = f"CV Upload HTTP error: {http_err}. Response: {http_err.response.text if http_err.response else 'No response'}"
                    logger.error(err_msg_batch)
                    st.error(err_msg_batch)
                    
                    current_batch_results_for_display.append({
                        "filename": f"S3 CV: {s3_cv_uri.split('/')[-1]}",
                        "structured_data": {"error": "API request failed"},
                        "db_status_custom": "API request failed, see error above."
                    })
                except requests.exceptions.RequestException as req_err:
                    err_msg_batch = f"CV Upload Connection error: {req_err}"
                    logger.error(err_msg_batch)
                    st.error(err_msg_batch)
                    
                    current_batch_results_for_display.append({
                        "filename": f"S3 CV: {s3_cv_uri.split('/')[-1]}",
                        "structured_data": {"error": "API connection failed"},
                        "db_status_custom": "API connection failed, see error above."
                    })
                except Exception as e:
                    err_msg_batch = f"An unexpected error occurred during CV upload: {e}"
                    logger.error(err_msg_batch)
                    st.error(err_msg_batch)
                    
                    current_batch_results_for_display.append({
                        "filename": f"S3 CV: {s3_cv_uri.split('/')[-1]}",
                        "structured_data": {"error": "Unexpected processing error"},
                        "db_status_custom": "Unexpected processing error, see logs."
                    })

            # Prepend current batch results to the main display list for statuses
            st.session_state.displayed_cv_processing_statuses = current_batch_results_for_display + st.session_state.displayed_cv_processing_statuses
            
            # Update active_session_cvs (used for ranking)
            for new_cv_info in current_batch_cv_info_for_active_list:
                if not any(existing_cv['cv_id'] == new_cv_info['cv_id'] for existing_cv in st.session_state.active_session_cvs):
                    st.session_state.active_session_cvs.append(new_cv_info)
            
            st.session_state.ranking_results = None 
            st.session_state.last_ranking_cv_count = 0

    # Display CV Parsing and DB status Results for all processed CVs in this session
    if st.session_state.displayed_cv_processing_statuses:
        st.subheader("CV Processing Statuses (Latest First):")
        for result_dict in st.session_state.displayed_cv_processing_statuses:
            cv_file_name = result_dict.get("filename", "CV (filename not found)")
            st.markdown(f"**File:** {cv_file_name}")
            
            structured_data = result_dict.get("structured_data", {})
            
            if "error" in structured_data:
                st.error(f"  LLM Parsing Error: {structured_data.get('error')}")
                raw_response = structured_data.get('raw_response')
                if raw_response:
                    with st.expander("View Raw LLM Response (Error)"):
                        st.code(raw_response, language='text') 
            else:
                st.success("  LLM Parsing Successful.")
                # Display the parsed CV data from LLM
                with st.expander("View Parsed CV Data (JSON)"):
                    st.json(structured_data)
            
            # Display DB status
            cv_db_status = result_dict.get("db_status_custom")
            if cv_db_status:
                status_color_cv = "error" if "Failed" in cv_db_status or "Error" in cv_db_status or "Skipped" in cv_db_status else "success"
                getattr(st, status_color_cv)(f"  Knowledge Base Update: {cv_db_status}")
            st.markdown("---")

# --- Tab 3: Ranking Results ---
elif st.session_state.selected_tab == "Ranking Results":
    st.header("3. CV Ranking against Active JD")

    if st.session_state.active_session_cvs:
        max_cvs = len(st.session_state.active_session_cvs)
        num_cvs_to_rank = st.number_input(
            f"Number of top CVs to rank (max {max_cvs}):",
            min_value=1,
            max_value=max_cvs,
            value=min(5, max_cvs) if max_cvs > 0 else 1, 
            step=1,
            key="num_cvs_to_rank_input",
            disabled=not st.session_state.active_session_cvs
        )
    else:
        st.info("Upload and process CVs in the 'CV Processing & Matching' tab to enable ranking.")

    # Determine if a re-rank is needed
    trigger_new_ranking = False
    if not st.session_state.ranking_results:
        trigger_new_ranking = True
    elif num_cvs_to_rank > len(st.session_state.ranking_results):
        trigger_new_ranking = True
    elif len(st.session_state.active_session_cvs) != st.session_state.last_ranking_cv_count:
        trigger_new_ranking = True

    if st.button("Rank Uploaded CVs against JD", key="rank_cvs_button_main", disabled=not st.session_state.active_session_cvs or num_cvs_to_rank == 0):
        if not st.session_state.current_jd_id:
            logger.warning("No active JD. Process a JD in 'JD Processing' tab first for ranking.")
            st.error("No active JD. Process a JD in 'JD Processing' tab.")
        elif not st.session_state.active_session_cvs:
            logger.warning("No CVs processed for the current JD session to rank.")
            st.error("No CVs processed for the current JD session.")
        elif trigger_new_ranking:
            logger.info(f"User triggered CV ranking via API for JD ID: {st.session_state.current_jd_id}, for top {num_cvs_to_rank} CVs. Trigger: new ranking required.")
            with st.spinner("Ranking CVs via Smart Recruit API..."):
                try:
                    cv_ids_to_rank_api = [cv_info["cv_id"] for cv_info in st.session_state.active_session_cvs if cv_info.get("cv_id")]
                    if not cv_ids_to_rank_api:
                        st.warning("No valid CV IDs found in the active session to send for ranking.")
                        st.session_state.ranking_results = []
                    else:
                        payload = {
                            "jd_id": st.session_state.current_jd_id,
                            "cv_ids": cv_ids_to_rank_api,
                            "top_n": num_cvs_to_rank
                        }
                        response = requests.post(f"{API_BASE_URL}/rank-cvs", json=payload)
                        response.raise_for_status()
                        
                        api_ranking_response = response.json()
                        reconstructed_results_for_ui = []
                        for api_rank_item in api_ranking_response.get("rankings", []):
                            cv_id = api_rank_item.get("cv_id")
                            original_cv_info = next((cv for cv in st.session_state.active_session_cvs if cv.get("cv_id") == cv_id), None)
                            filename_for_ui = original_cv_info.get("filename") if original_cv_info else api_rank_item.get("evaluation", {}).get("filename", f"CV_{cv_id}")

                            evaluation_data = api_rank_item.get("evaluation", {})
                            reconstructed_results_for_ui.append({
                                "cv_id": cv_id,
                                "filename": filename_for_ui,
                                "llm_ranking_score": api_rank_item.get("score", 0.0),
                                "initial_vector_score": evaluation_data.get("initial_vector_score", 0.0),
                                "vector_match_details": evaluation_data.get("vector_match_details", "N/A"),
                                "llm_skills_evaluation": evaluation_data.get("llm_skills_evaluation", []),
                                "llm_experience_evaluation": evaluation_data.get("llm_experience_evaluation", []),
                                "llm_additional_points": evaluation_data.get("llm_additional_points", []),
                                "llm_overall_assessment": evaluation_data.get("llm_overall_assessment", "N/A"),
                            })
                        
                        st.session_state.ranking_results = reconstructed_results_for_ui
                        st.session_state.last_ranking_cv_count = len(st.session_state.active_session_cvs)
                        logger.info(f"CV ranking successfully retrieved via API. Results count: {len(st.session_state.ranking_results)}")
                        if not st.session_state.ranking_results:
                            st.info("Ranking process completed, but no CVs were returned from the ranking API.")

                except requests.exceptions.HTTPError as http_err:
                    err_msg = f"Ranking API HTTP error: {http_err}. Response: {http_err.response.text if http_err.response else 'No response'}"
                    st.session_state.ranking_results = []
                    st.session_state.last_ranking_cv_count = 0
                    logger.error(err_msg)
                    st.error(err_msg)
                except requests.exceptions.RequestException as req_err:
                    err_msg = f"Error connecting to Ranking API: {req_err}"
                    st.session_state.ranking_results = []
                    st.session_state.last_ranking_cv_count = 0
                    logger.error(err_msg)
                    st.error(err_msg)
                except Exception as e:
                    err_msg = f"An unexpected error occurred during CV ranking via API: {e}"
                    st.session_state.ranking_results = []
                    st.session_state.last_ranking_cv_count = 0
                    logger.error(err_msg, exc_info=True)
                    st.error(err_msg)
        elif not trigger_new_ranking:
            st.info("Displaying previously fetched ranking results. Adjust the slider or add new CVs and click 'Rank' to re-fetch.")
    
    # Display Ranking Results
    if st.session_state.ranking_results is not None:
        results_to_display = st.session_state.ranking_results[:num_cvs_to_rank]

        if not results_to_display and st.session_state.current_jd_id and st.session_state.active_session_cvs:
             st.info("Ranking process returned no CVs for the selected criteria or an issue occurred.")
        elif not results_to_display:
            st.info("No ranking results to display. Ensure a JD and CVs are processed, then click 'Rank Uploaded CVs'.")
        else:
            st.subheader(f"Top {len(results_to_display)} CV Candidate(s) (after Vector Scan & LLM Reasoning):")
            
            for rank, item in enumerate(results_to_display):
                st.markdown(f"---Rank {rank + 1}---")
                st.markdown(f"**File:** `{item.get('filename', 'N/A')}`")
                st.markdown(f"**LLM Ranking Score:** `{item.get('llm_ranking_score', 0.0):.2f}/10.0`")
                st.markdown(f"_(Initial Vector Score: {item.get('initial_vector_score', 0.0):.4f})_")

                with st.expander(f"View Details for {item.get('filename', 'CV')}"):
                    st.markdown("**Vector Similarity Details:**")
                    st.caption(item.get('vector_match_details', 'No vector match details available.'))
                    st.markdown("---")
                    
                    st.markdown("**LLM Reasoning:**")
                    
                    skills_eval = item.get('llm_skills_evaluation', [])
                    experience_eval = item.get('llm_experience_evaluation', [])
                    additional_points_eval = item.get('llm_additional_points', [])
                    overall_assessment = item.get('llm_overall_assessment', 'N/A')

                    # Check if the first item in skills_eval indicates an error
                    is_error = skills_eval and isinstance(skills_eval, list) and skills_eval[0].startswith("Error:")

                    if is_error:
                        st.error(f"LLM Reasoning Error for {item.get('filename', 'this CV')}: {skills_eval[0]}")
                    else:
                        if skills_eval:
                            st.markdown("**🎯 Skills Evaluation:**")
                            for point in skills_eval:
                                st.markdown(f"- {point}")
                        else:
                            st.markdown("**🎯 Skills Evaluation:** Not provided by LLM.")

                        if experience_eval:
                            st.markdown("**🧠 Experience Evaluation:**")
                            for point in experience_eval:
                                st.markdown(f"- {point}")
                        else:
                            st.markdown("**🧠 Experience Evaluation:** Not provided by LLM.")

                        if additional_points_eval:
                            st.markdown("**✨ Additional Points:**")
                            for point in additional_points_eval:
                                st.markdown(f"- {point}")
                        else:
                            st.markdown("**✨ Additional Points:** Not provided by LLM.")
                        
                        if overall_assessment and overall_assessment != "N/A":
                            st.markdown("**📝 LLM's Overall Assessment:**")
                            st.success(overall_assessment)
                        else:
                            st.markdown("**📝 LLM's Overall Assessment:** Not provided by LLM.")
                st.markdown(" ")

# --- Tab 4: Candidate Questions ---
elif st.session_state.selected_tab == "Candidate Questions":
    st.header("4. Generate Interview Questions for Ranked Candidates")

    if not st.session_state.ranking_results:
        st.warning("No candidates have been ranked yet. Please go to the 'Ranking Results' tab and rank CVs first.")
    elif not st.session_state.current_jd_id:
        st.error("Critical error: No active JD ID found, but ranking results exist. Please reprocess JD.")
    else:
        current_ranking_results = st.session_state.ranking_results if isinstance(st.session_state.ranking_results, list) else []
        ranked_candidates_options = {
            f"{idx + 1}. {item.get('filename', 'N/A')} (Score: {item.get('llm_ranking_score', 0.0):.2f})": item.get('cv_id') 
            for idx, item in enumerate(current_ranking_results) if item.get('cv_id')
        }
        
        if not ranked_candidates_options:
            st.info("No candidates available from the ranking results to generate questions for.")
        else:
            selected_candidate_display_name = st.selectbox(
                "Select a Ranked Candidate:", 
                options=list(ranked_candidates_options.keys()),
                index=0
            )

            if selected_candidate_display_name:
                selected_cv_id = ranked_candidates_options[selected_candidate_display_name]
                candidate_identifier_for_logging = selected_candidate_display_name.split(' (')[0]

                if st.button(f"Generate Interview Questions for {candidate_identifier_for_logging}", key=f"generate_questions_{selected_cv_id}"):
                    st.session_state.generated_questions_for_candidate = {}
                    with st.spinner(f"Generating questions for {candidate_identifier_for_logging} via API..."):
                        try:
                            payload = {
                                "jd_id": st.session_state.current_jd_id,
                                "cv_id": selected_cv_id
                            }
                            response = requests.post(f"{API_BASE_URL}/generate-questions", json=payload)
                            response.raise_for_status()

                            api_response_data = response.json()
                            
                            st.session_state.generated_questions_for_candidate[selected_cv_id] = api_response_data
                            
                            num_tech = len(api_response_data.get("technical_questions", []))
                            num_gen = len(api_response_data.get("general_behavioral_questions", []))

                            if num_tech > 0 or num_gen > 0:
                                logger.info(f"Successfully retrieved {num_tech} technical and {num_gen} general questions for {candidate_identifier_for_logging} via API.")
                            else:
                                err_msg_q = f"API returned no questions (technical or general) for {candidate_identifier_for_logging}."
                                st.session_state.generated_questions_for_candidate[selected_cv_id] = {
                                    "technical_questions": [{"question": err_msg_q, "category": "Error", "good_answer_pointers":[], "unsure_answer_pointers":[]}],
                                    "general_behavioral_questions": []
                                }
                                logger.warning(err_msg_q)
                                st.info(err_msg_q)
                        
                        except requests.exceptions.HTTPError as http_err:
                            err_text = http_err.response.text if http_err.response else 'No response text'
                            detail = f"Question Generation API HTTP error: {http_err}. Response: {err_text}"
                            st.session_state.generated_questions_for_candidate[selected_cv_id] = {
                                "technical_questions": [{"question": detail, "category": "Error", "good_answer_pointers":[], "unsure_answer_pointers":[]}],
                                "general_behavioral_questions": []
                            }
                            logger.error(detail)
                            st.error(detail)
                        except requests.exceptions.RequestException as req_err:
                            detail = f"Error connecting to Question Generation API: {req_err}"
                            st.session_state.generated_questions_for_candidate[selected_cv_id] = {
                                "technical_questions": [{"question": detail, "category": "Error", "good_answer_pointers":[], "unsure_answer_pointers":[]}],
                                "general_behavioral_questions": []
                            }
                            logger.error(detail)
                            st.error(detail)
                        except Exception as e:
                            detail = f"An unexpected error occurred during question generation via API: {e}"
                            st.session_state.generated_questions_for_candidate[selected_cv_id] = {
                                "technical_questions": [{"question": detail, "category": "Error", "good_answer_pointers":[], "unsure_answer_pointers":[]}],
                                "general_behavioral_questions": []
                            }
                            logger.error(detail, exc_info=True)
                            st.error(detail)
                
                # Display generated questions for the selected candidate
                if selected_cv_id in st.session_state.generated_questions_for_candidate:
                    st.subheader(f"Interview Questions for: {candidate_identifier_for_logging}")
                    question_data_from_state = st.session_state.generated_questions_for_candidate[selected_cv_id]
                    
                    technical_questions = question_data_from_state.get("technical_questions", [])
                    general_questions = question_data_from_state.get("general_behavioral_questions", [])

                    if not technical_questions and not general_questions:
                        st.info("No questions available to display or an issue occurred previously.")
                    
                    if technical_questions:
                        if technical_questions[0].get("category") == "Error":
                            st.error(f"Error generating technical questions: {technical_questions[0].get('question')}")
                        else:
                            st.markdown("### Technical Questions")
                            for i, q_item in enumerate(technical_questions):
                                st.markdown(f"**{i+1}. {q_item.get('question')}**")
                                with st.expander("View Answer Pointers"):
                                    st.markdown("**Good Answer Pointers:**")
                                    for pointer in q_item.get('good_answer_pointers', []):
                                        st.markdown(f"- {pointer}")
                                    st.markdown("**Unsure Answer Pointers:**")
                                    for pointer in q_item.get('unsure_answer_pointers', []):
                                        st.markdown(f"- {pointer}")
                                if q_item.get('rationale'):
                                    st.caption(f"Rationale: {q_item.get('rationale')}")
                                st.markdown("---")
                    
                    if general_questions:
                        st.markdown("### General/Behavioral Questions")
                        for i, q_item in enumerate(general_questions):
                            st.markdown(f"**{i+1}. {q_item.get('question')}**")
                            with st.expander("View Answer Pointers"):
                                st.markdown("**Good Answer Pointers:**")
                                for pointer in q_item.get('good_answer_pointers', []):
                                    st.markdown(f"- {pointer}")
                                st.markdown("**Unsure Answer Pointers:**")
                                for pointer in q_item.get('unsure_answer_pointers', []):
                                    st.markdown(f"- {pointer}")
                            if q_item.get('rationale'):
                                st.caption(f"Rationale: {q_item.get('rationale')}")
                            st.markdown("---")

