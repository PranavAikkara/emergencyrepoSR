from pydantic import BaseModel, EmailStr
from typing import List, Optional, Union

# New model for detailed question structure
class DetailedQuestion(BaseModel):
    question: str
    category: str # "Technical" or "General/Behavioral"
    good_answer_pointers: List[str]
    unsure_answer_pointers: List[str]

class JDOutput(BaseModel):
    type: Optional[str] = None
    location: Optional[str] = None
    skills: List[str] = []
    experience: Optional[str] = None

class ExperienceDetail(BaseModel):
    previous_company: Optional[str] = None
    role: Optional[str] = None
    duration: Optional[str] = None
    points_about_it: List[str] = []

class ContactInfo(BaseModel):
    mobile_number: Optional[str] = None
    email: Optional[EmailStr] = None
    other_links: List[str] = []

class PersonalDetails(BaseModel):
    date_of_birth: Optional[str] = None
    place: Optional[str] = None
    language: List[str] = []
    additional_points: List[str] = []

class CVOutput(BaseModel):
    candidate_name: Optional[str] = None
    skills: List[str] = []
    experience: List[ExperienceDetail] = []
    contact_info: Optional[ContactInfo] = None
    personal_details: Optional[PersonalDetails] = None

class CVRankingOutput(BaseModel):
    ranking_score: int
    explanation: str

class ChunkPairScoreOutput(BaseModel):
    chunk_match_score: int
    chunk_match_explanation: str

class LLMJdCvComparisonOutput(BaseModel):
    cv_id: str
    skills_evaluation: List[str]
    experience_evaluation: List[str]
    additional_points: List[str]
    overall_assessment: Optional[str] = None
    llm_ranking_score: Optional[float] = None

# New Pydantic model for candidate questions output
class CandidateQuestionsOutput(BaseModel):
    technical_questions: List[DetailedQuestion]
    general_behavioral_questions: List[DetailedQuestion] 

# New Pydantic model for JD keyword extraction output
class JDKeywordsOutput(BaseModel):
    keywords: List[str] = [] 