"""
Services for Smart Recruit.

This package provides service interfaces for:
1. JD (Job Description) processing
2. CV (Curriculum Vitae) processing
3. CV ranking against JDs
4. Candidate question generation
"""

from src.services.jd_service import parse_jd_with_llm, process_jd
from src.services.cv_service import parse_cv_with_llm, process_cv, process_multiple_cvs
from src.services.ranking_service import get_llm_comparison_for_cv, calculate_cv_ranking
from src.services.question_service import generate_candidate_questions

__all__ = [
    # JD service functions
    'parse_jd_with_llm',
    'process_jd',
    
    # CV service functions
    'parse_cv_with_llm',
    'process_cv',
    'process_multiple_cvs',
    
    # Ranking service functions
    'get_llm_comparison_for_cv',
    'calculate_cv_ranking',
    
    # Question service functions
    'generate_candidate_questions',
] 