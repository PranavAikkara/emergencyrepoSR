from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class JDUploadResponse(BaseModel):
    """Response model for JD upload endpoint"""
    jd_id: str
    filename: str
    jd_data: Optional[Dict[str, Any]] = None

class CVUploadResponse(BaseModel):
    """Response model for individual CV in the upload CVs endpoint"""
    cv_id: Optional[str] = None
    success: bool
    filename: str
    cv_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class RankingRequest(BaseModel):
    """Request model for CV ranking endpoint"""
    jd_id: str
    cv_ids: List[str]
    top_n: Optional[int] = None

class RankingResult(BaseModel):
    """Model for individual CV ranking result"""
    cv_id: str
    score: float
    evaluation: Dict[str, Any]

class RankingResponse(BaseModel):
    """Response model for CV ranking endpoint"""
    rankings: List[RankingResult]

class QuestionGenerationRequest(BaseModel):
    """Request model for question generation endpoint"""
    jd_id: str
    cv_id: str

class Question(BaseModel):
    """Model for individual interview question"""
    category: str
    question: str
    good_answer_pointers: Optional[List[str]] = None
    unsure_answer_pointers: Optional[List[str]] = None

class QuestionGenerationResponse(BaseModel):
    """Response model for question generation endpoint"""
    cv_id: str
    jd_id: str
    technical_questions: Optional[List[Question]] = None
    general_behavioral_questions: Optional[List[Question]] = None
    error: Optional[str] = None

# New Schemas for Excel Report Generation
class CandidateReportRequest(BaseModel):
    jd_id: str
    cv_ids: List[str]

class CandidateReportDataForExcel(BaseModel):
    cv_id: str
    cv_filename: Optional[str] = "N/A"
    rank_score: Optional[float] = 0.0
    llm_overall_assessment: Optional[str] = "N/A"
    parsed_cv_summary: Optional[str] = "N/A"
    parsed_skills: Optional[List[str]] = Field(default_factory=list)
    parsed_experience_summary: Optional[str] = "N/A"
    technical_questions: Optional[List[Question]] = Field(default_factory=list) # Using existing Question schema
    general_behavioral_questions: Optional[List[Question]] = Field(default_factory=list) # Using existing Question schema
    error_message: Optional[str] = None # To capture any errors for a specific CV processing 

# S3-based upload request models
class S3JDUploadRequest(BaseModel):
    """Request model for JD upload from S3"""
    s3_uri: str  # Format: s3://bucket-name/folder/file.pdf

class S3CVUploadRequest(BaseModel):
    """Request model for single CV upload from S3"""
    s3_uri: str  # Format: s3://bucket-name/folder/file.pdf
    jd_id: str 