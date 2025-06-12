# Smart Recruit - Low-Level Design

## 1. Directory Structure

```
Smart_Recruit_Scratch/
├── app.py                     # Streamlit frontend application
├── config.py                  # Configuration settings (LLM API keys, etc.)
├── routes.py                  # FastAPI routes/endpoints
├── requirements.txt           # Python dependencies
│
├── src/                       # Source code directory
│   ├── llm/                   # LLM interaction modules
│   │   ├── __init__.py
│   │   ├── chunker.py         # Document chunking with LLM
│   │   ├── client.py          # LLM client configuration
│   │   ├── parser.py          # Document parsing with LLM
│   │   └── utils.py           # LLM utility functions
│   │
│   ├── prompts/               # LLM prompt templates
│   │   ├── __init__.py
│   │   ├── candidate_questions_prompt.md    # For generating interview questions
│   │   ├── cv_enrich_prompt.md              # For CV chunking/enrichment
│   │   ├── jd_cv_comparison_prompt.md       # For CV-JD comparison
│   │   ├── jd_enrich_prompt.md              # For JD chunking/enrichment
│   │   ├── json_output_cv_prompt.md         # For CV structured parsing
│   │   └── json_output_jd_prompt.md         # For JD structured parsing
│   │
│   ├── schemas/               # Data models and validation
│   │   ├── __init__.py
│   │   ├── api_schemas.py     # API request/response models
│   │   └── schemas.py         # Internal data models
│   │
│   ├── services/              # Business logic services
│   │   ├── __init__.py
│   │   ├── cv_service.py      # CV processing services
│   │   ├── jd_service.py      # JD processing services
│   │   ├── question_service.py # Question generation service
│   │   └── ranking_service.py # CV ranking service
│   │
│   ├── utils/                 # Utility functions
│   │   ├── __init__.py
│   │   ├── file_handler.py    # File processing utilities
│   │   ├── logging.py         # Logging utilities
│   │   └── validators.py      # Data validation utilities
│   │
│   └── vector_db/             # Vector database operations
│       ├── __init__.py
│       ├── client.py          # Qdrant client and core vector operations
│       ├── cv_repository.py   # CV-specific vector DB operations
│       └── jd_repository.py   # JD-specific vector DB operations
│
├── design_and_architecture/   # Documentation
│   ├── architecture.md        # System architecture diagrams
│   ├── design.md              # Low-level design (this file)
│   └── plan.md                # High-level project plan
│
└── logs/                      # Application logs
```

## 2. Core Components

### 2.1 Frontend (app.py)

The Streamlit application serves as the user interface for the Smart Recruit system. It contains:

- **Tab-based Navigation**:
  - JD Processing tab
  - CV Processing & Matching tab
  - Ranking Results tab
  - Candidate Questions tab

- **Key UI Components**:
  - File uploaders for JD and CVs
  - Processing status indicators
  - JSON data viewers
  - Ranking display with expandable details
  - Question generation interface

- **API Integration**:
  - Communicates with FastAPI backend via HTTP requests
  - Handles file encoding/decoding for API transmission
  - Manages session state for UI persistence

### 2.2 Backend API (routes.py)

The FastAPI application provides RESTful endpoints for all core functionality:

| Endpoint | Method | Purpose | Request | Response |
|----------|--------|---------|---------|----------|
| `/` | GET | Health check | None | Status message |
| `/upload-jd` | POST | Process JD | File upload | JD ID, structured data |
| `/upload-cvs` | POST | Process CVs | Files upload, JD ID | CV IDs, structured data |
| `/rank-cvs` | POST | Rank CVs | JD ID, CV IDs, top_n | Ranked results with reasoning |
| `/generate-questions` | POST | Generate questions | JD ID, CV ID | Technical and behavioral questions |

- Uses FastAPI's dependency injection for request validation
- Implements comprehensive error handling
- Provides detailed logging
- Uses async/await pattern for non-blocking operations

### 2.3 LLM Integration (src/llm/)

Manages interactions with Large Language Models:

- **client.py**: Configures LLM providers and API parameters
  - `get_litellm_params()`: Returns configuration for specified model
  - `get_api_key_for_model()`: Retrieves API key for a model

- **parser.py**: Extracts structured data from documents
  - `parse_document()`: Processes document with LLM and validates against schema

- **chunker.py**: Splits documents into semantic chunks
  - `chunk_document_with_llm()`: Uses LLM to divide document into meaningful sections

- **utils.py**: Helper functions for LLM operations
  - `load_prompt()`: Loads and manages prompt templates

### 2.4 Vector Database Operations (src/vector_db/)

Handles vector embeddings and similarity search:

- **client.py**: Core vector operations
  - `initialize_qdrant_collections()`: Sets up vector collections
  - `get_embedding()`: Generates embeddings from text
  - `search_similar_chunks()`: Performs similarity search
  - `get_full_document_text_from_db()`: Reconstructs document from chunks

- **jd_repository.py**: JD-specific vector operations
  - `add_jd_to_db()`: Processes and stores JD in vector DB
  - `get_jd_chunks()`: Retrieves JD chunks by ID

- **cv_repository.py**: CV-specific vector operations
  - `add_cv_to_db()`: Processes and stores CV in vector DB
  - `get_cvs_for_jd()`: Finds CVs associated with a JD

### 2.5 Services (src/services/)

Implements core business logic:

- **jd_service.py**: JD processing service
  - `parse_jd_with_llm()`: Extracts structured data from JD
  - `process_jd()`: Complete JD processing workflow

- **cv_service.py**: CV processing service
  - `parse_cv_with_llm()`: Extracts structured data from CV
  - `process_multiple_cvs()`: Batch processes multiple CVs

- **ranking_service.py**: CV ranking service
  - `calculate_cv_ranking()`: Two-stage ranking process
  - `get_llm_comparison_for_cv()`: Detailed LLM comparison

- **question_service.py**: Interview question service
  - `generate_candidate_questions()`: Creates personalized questions

### 2.6 Data Models (src/schemas/)

Defines data structures and validation:

- **schemas.py**: Internal data models
  - `JDOutput`: Structured JD data
  - `CVOutput`: Structured CV data
  - `CandidateQuestionsOutput`: Question generation output

- **api_schemas.py**: API request/response models
  - `JDUploadResponse`: JD upload response
  - `CVUploadResponse`: CV upload response
  - `RankingRequest`/`RankingResponse`: Ranking models
  - `QuestionGenerationRequest`/`QuestionGenerationResponse`: Question models

## 3. Key Algorithms

### 3.1 Two-Stage CV Ranking Algorithm

The ranking process uses a sophisticated two-stage approach:

#### Stage 1: Vector Similarity

1. **Chunk-based Comparison**:
   - Each JD chunk (with assigned weight 1-3) is compared against all CV chunks
   - For each JD chunk, retrieve top K similar CV chunks
   - Calculate similarity score with weight: `(raw_similarity_score² * jd_chunk_weight)`
   - Aggregate scores for each CV: `total_weighted_score / match_count`

2. **Optimization**:
   - If `top_n >= total_number_of_cvs`, skip vector similarity
   - Improves performance for small batches

#### Stage 2: LLM Reasoning

1. **Input Preparation**:
   - Retrieve full text of JD and top N CVs from Stage 1
   - Format as input to LLM with comparison prompt

2. **LLM Evaluation**:
   - Model: "gemini/gemini-2.5-flash-preview-05-20"
   - Generates structured comparison with:
     - Skills evaluation (core skills present/missing)
     - Experience evaluation
     - Additional points
     - Overall assessment
     - Numerical ranking score (1-10)

3. **Final Ranking**:
   - Sort by LLM ranking score (descending)
   - Use vector similarity score as tiebreaker

### 3.2 Document Chunking and Enrichment

1. **Semantic Chunking**:
   - LLM identifies 4-6 logical sections in document
   - Each chunk limited to 512 tokens
   - Preserves original text as `og_content`

2. **Content Enrichment**:
   - LLM expands each chunk with:
     - Implied concepts and related skills
     - Synonyms and domain-specific terminology
     - Hierarchical relationships
   - Enhanced text stored as `enriched_content`

3. **JD Chunk Weighting**:
   - Weight 3: Essential qualifications, core technical skills
   - Weight 2: Desirable skills, secondary responsibilities
   - Weight 1: General info, boilerplate content

## 4. API Contract

### 4.1 JD Upload Endpoint

**Request**:
- URL: `/upload-jd`
- Method: POST
- Content-Type: multipart/form-data
- Body: 
  - file: File object (PDF, DOCX, TXT)

**Response**:
```json
{
  "jd_id": "unique-uuid-string",
  "filename": "original_filename.pdf",
  "jd_data": {
    "type": "Full-time",
    "location": "New York, NY",
    "experience": "3-5 years",
    "skills": ["Python", "Machine Learning", "SQL", "Docker"]
  }
}
```

### 4.2 CV Upload Endpoint

**Request**:
- URL: `/upload-cvs`
- Method: POST
- Content-Type: multipart/form-data
- Body: 
  - files: List of File objects (PDF, DOCX, TXT)
  - jd_id: string (UUID of the associated JD)

**Response**:
```json
[
  {
    "cv_id": "unique-uuid-string-1",
    "success": true,
    "filename": "candidate1_resume.pdf",
    "cv_data": {
      "candidate_name": "John Smith",
      "skills": ["Python", "TensorFlow", "AWS", "Docker"],
      "experience": [
        {
          "previous_company": "Tech Corp",
          "role": "Senior Developer",
          "duration": "2018-2022",
          "points_about_it": ["Led team of 5 developers", "Improved system performance by 30%"]
        }
      ]
    },
    "error": null
  },
  {
    "cv_id": "unique-uuid-string-2",
    "success": true,
    "filename": "candidate2_resume.pdf",
    "cv_data": {...},
    "error": null
  }
]
```

### 4.3 Ranking Endpoint

**Request**:
- URL: `/rank-cvs`
- Method: POST
- Content-Type: application/json
- Body:
```json
{
  "jd_id": "jd-uuid-string",
  "cv_ids": ["cv-uuid-1", "cv-uuid-2", "cv-uuid-3"],
  "top_n": 2
}
```

**Response**:
```json
{
  "rankings": [
    {
      "cv_id": "cv-uuid-2",
      "score": 8.5,
      "evaluation": {
        "filename": "candidate2_resume.pdf",
        "initial_vector_score": 0.78,
        "vector_match_details": "Strong matches on core skills and experience sections",
        "llm_skills_evaluation": ["Matches 8/10 required skills", "Strong in Python and ML"],
        "llm_experience_evaluation": ["5 years in similar role", "Led similar projects"],
        "llm_additional_points": ["Relevant certification", "Industry publications"],
        "llm_overall_assessment": "Strong candidate with excellent technical skills and leadership experience"
      }
    },
    {
      "cv_id": "cv-uuid-1",
      "score": 7.2,
      "evaluation": {...}
    }
  ]
}
```

### 4.4 Question Generation Endpoint

**Request**:
- URL: `/generate-questions`
- Method: POST
- Content-Type: application/json
- Body:
```json
{
  "jd_id": "jd-uuid-string",
  "cv_id": "cv-uuid-string"
}
```

**Response**:
```json
{
  "cv_id": "cv-uuid-string",
  "jd_id": "jd-uuid-string",
  "technical_questions": [
    {
      "question": "Can you describe your experience with Python in your previous role at Tech Corp?",
      "category": "Technical",
      "good_answer_pointers": ["Specific project examples", "Advanced features used", "Problem solving approach"],
      "unsure_answer_pointers": ["Vague descriptions", "Basic usage only", "No specific examples"]
    },
    {...}
  ],
  "general_behavioral_questions": [
    {
      "question": "Tell me about a time you had to learn a new technology quickly for a project.",
      "category": "General/Behavioral",
      "good_answer_pointers": ["Structured learning approach", "Successful implementation", "Lessons learned"],
      "unsure_answer_pointers": ["Generic response", "Lack of specifics", "Focus on difficulties only"]
    },
    {...}
  ]
}
```

## 5. Error Handling

The system implements comprehensive error handling:

1. **API Request Validation**:
   - Pydantic models validate all request data
   - Returns 400 Bad Request for invalid input

2. **Document Processing Errors**:
   - Graceful handling of unsupported file types
   - Detailed error messages for parsing failures
   - Retry mechanism for CV processing (2 attempts)

3. **LLM Interaction Errors**:
   - Fallback strategies for different failure modes
   - JSON parsing with multiple fallback approaches
   - Comprehensive logging of raw LLM responses

4. **Database Errors**:
   - Connection retry mechanism
   - Validation before vector operations
   - Proper error propagation to API layer

## 6. Security Considerations

1. **API Security**:
   - CORS configured to control access
   - Input validation against injection attacks
   - File type validation and safe handling

2. **Data Protection**:
   - No persistent storage of raw documents (only vectorized)
   - API keys stored in environment variables
   - Logging sanitized to prevent data leakage

3. **Third-party Integration**:
   - Secure handling of LLM API credentials
   - Timeout configuration for external services
   - Graceful degradation on service failures
