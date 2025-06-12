"""
Question service for generating interview questions for candidates.

This module provides:
1. Functions for generating interview questions based on JD and CV
"""

import json
import litellm
from typing import List, Dict, Optional

from src.llm.llmclient import get_litellm_params
from src.schemas.schemas import CandidateQuestionsOutput
from src.utils.logging import get_logger

logger = get_logger(__name__)

async def generate_candidate_questions(
    jd_text: str,
    cv_text: str,
    candidate_name_or_id: str
) -> Optional[CandidateQuestionsOutput]:
    """
    Uses an LLM to generate interview questions for a candidate based on their CV and a JD.

    Args:
        jd_text: The full text of the Job Description.
        cv_text: The full text of the Curriculum Vitae.
        candidate_name_or_id: The name or ID of the candidate for personalization in the prompt.

    Returns:
        A CandidateQuestionsOutput object containing a list of questions, or None on error.
    """
    from src.llm.utils import load_prompt
    
    logger.info(f"Starting candidate question generation for: {candidate_name_or_id}")
    
    try:
        questions_prompt_template = load_prompt("src/prompts/candidate_questions_prompt.md")
    except Exception as e:
        logger.error(f"Error loading candidate questions prompt: {e}")
        return None

    prompt = questions_prompt_template.replace("{{JD_TEXT}}", jd_text)
    prompt = prompt.replace("{{CV_TEXT}}", cv_text)
    prompt = prompt.replace("{{CANDIDATE_NAME_OR_ID}}", candidate_name_or_id)

    try:
        llm_params = get_litellm_params()
        # Ensure response_format for JSON is correctly set if not already in get_litellm_params
        # The prompt already requests JSON, but this enforces it for some models.
        llm_params_for_json = {**llm_params, "response_format": {"type": "json_object"}}
        logger.info(f"Calling LLM for candidate question generation for: {candidate_name_or_id}.")
        response = await litellm.acompletion(
            **llm_params_for_json,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_content = response.choices[0].message.content
        if not response_content:
            logger.error(f"LLM returned empty content for candidate questions: {candidate_name_or_id}")
            return None

        # Parse the JSON string into our Pydantic model
        llm_output_data = json.loads(response_content)
        questions_result = CandidateQuestionsOutput(**llm_output_data)
            
        return questions_result

    except json.JSONDecodeError as json_e:
        logger.error(f"Error decoding LLM JSON response for candidate questions ({candidate_name_or_id}): {json_e}")
        logger.error(f"LLM Raw Response: {response_content[:500]}...")
        return None
    except Exception as e:
        logger.error(f"Error during LLM question generation for candidate {candidate_name_or_id}: {type(e).__name__} - {e}")
        return None 