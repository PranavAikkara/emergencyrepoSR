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
  - JD Processing tab (S3-based)
  - CV Processing & Matching tab (S3-based)
  - Ranking Results tab
  - Candidate Questions tab

- **Key UI Components**:
  - S3 URI input fields for JD and CVs
  - Processing status indicators with retry information
  - JSON data viewers for structured output
  - Ranking display with LLM reasoning (no vector scores exposed)
  - Question generation interface with answer pointers

- **Advanced API Integration**:
  - Communicates with FastAPI backend via HTTP requests using S3 URIs
  - Handles S3 metadata display and error reporting
  - Manages session state for UI persistence across processing attempts
  - Displays detailed processing logs and optimization decisions

### 2.2 Backend API (routes.py)

The FastAPI application provides RESTful endpoints for all core functionality with S3 integration:

| Endpoint | Method | Purpose | Request | Response |
|----------|--------|---------|---------|----------|
| `/` | GET | Health check | None | Status message |
| `/health` | GET | Container health check | None | Health status |
| `/s3-upload-jd` | POST | Process JD from S3 | S3 URI | JD ID, structured data, S3 metadata |
| `/s3-upload-cv` | POST | Process CV from S3 | S3 URI | CV ID, structured data, S3 metadata |
| `/rank-cvs` | POST | Rank CVs | JD ID, CV IDs, top_n | Ranked results with LLM reasoning |
| `/generate-questions` | POST | Generate questions | JD ID, CV ID | Technical and behavioral questions |

- **Advanced Features**:
  - S3 integration with comprehensive metadata tracking
  - Retry mechanism with exponential backoff (2 attempts, 3-second delays)
  - Parallel processing for LLM operations
  - Intelligent optimization (skips vector similarity when ranking all CVs)
  - Rich error handling with context preservation
  - Detailed logging of processing decisions and performance metrics
- Uses FastAPI's dependency injection for request validation
- Implements comprehensive error handling with graceful degradation
- Provides detailed logging with S3 provenance tracking
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

### 3.1 Advanced Two-Stage CV Ranking Algorithm

The ranking process uses a sophisticated two-stage approach with intelligent optimization:

#### Stage 1: Vector Similarity (with Smart Optimization)

1. **Intelligent Optimization Logic**:
   - Automatically detects when `top_n >= total_number_of_cvs`
   - **OPTIMIZATION**: Skips entire vector similarity stage for efficiency
   - Logs optimization decisions for transparency
   - Improves performance by 3-5x for small batches

2. **Advanced Chunk-based Comparison** (when not optimized):
   - Each JD chunk assigned weight (1=General, 2=Desirable, 3=Essential) by LLM
   - For each weighted JD chunk, retrieve top 15 similar CV chunks
   - **Mathematical Innovation**: `(raw_similarity_score² × jd_chunk_weight)`
   - **"Shiniest Moment" Philosophy**: Uses `max_weighted_contribution` per CV
   - Detailed logging of match analysis for each CV

3. **Mathematical Rationale**:
   - Squaring similarity scores penalizes weak matches exponentially
   - Amplifies strong domain expertise over keyword frequency
   - Reduces noise from common terms and semantic ambiguity
   - Rewards specialists over generalists

#### Stage 2: LLM Reasoning (Enhanced)

1. **Parallel Processing**:
   - Async processing of multiple CVs simultaneously
   - Retrieve full document texts reconstructed from chunks
   - Format as input to LLM with advanced comparison prompt

2. **Advanced LLM Evaluation**:
   - Model: "gemini/gemini-2.5-flash-preview" with JSON response format
   - Generates structured comparison with:
     - Skills evaluation (detailed analysis of core skills)
     - Experience evaluation (relevance and depth assessment)
     - Additional points (certifications, publications, leadership)
     - Overall assessment (comprehensive candidate summary)
     - Numerical ranking score (1-10 with reasoning)

3. **Robust Error Handling**:
   - Graceful degradation for LLM failures
   - Detailed error logging with raw response preservation
   - Fallback strategies for different failure modes

4. **Final Ranking**:
   - Sort by LLM ranking score (descending)
   - **User Experience**: Vector scores hidden from end users
   - Focus on interpretable LLM reasoning

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

## 4. API Contract (S3-Based)

### 4.1 S3 JD Upload Endpoint

**Request**:
- URL: `/s3-upload-jd`
- Method: POST
- Content-Type: application/json
- Body: 
```json
{
  "s3_uri": "s3://smartrecruit-dev/JD/Senior_Developer_JD.pdf"
}
```

**Response**:
```json
{
  "jd_id": "b4237167-cce9-4aa0-843c-365bdf6e257f",
  "filename": "Senior_Developer_JD.pdf",
  "jd_data": {
    "type": "Full-time",
    "location": "New York, NY",
    "experience": "3-5 years",
    "skills": ["Python", "Machine Learning", "SQL", "Docker", "AWS"]
  }
}
```

### 4.2 S3 CV Upload Endpoint

**Request**:
- URL: `/s3-upload-cv`
- Method: POST
- Content-Type: application/json
- Body: 
```json
{
  "s3_uri": "s3://smartrecruit-dev/resumes/John_Smith_Resume.pdf"
}
```

**Response**:
```json
{
  "cv_id": "e685aa11-04e8-46d2-8515-9a55bc4ccbfd",
  "success": true,
  "filename": "John_Smith_Resume.pdf",
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
    ],
    "contact_info": {
      "mobile_number": "+1-555-0123",
      "email": "john.smith@email.com",
      "other_links": ["LinkedIn", "GitHub"]
    },
    "personal_details": {
      "place": "New York, NY",
      "additional_points": ["AWS Certified", "Published 3 technical papers"]
    }
  },
  "error": null
}
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

## 5. Advanced Error Handling & Business Logic

The system implements comprehensive error handling with sophisticated business logic:

1. **S3 Integration Error Handling**:
   - URI validation with detailed error messages
   - S3 access permission validation
   - File existence and accessibility checks
   - Comprehensive metadata extraction with fallbacks

2. **Advanced Retry Mechanism**:
   - **Exponential Backoff**: 3-second delays between attempts
   - **Granular Tracking**: Separate success flags for DB and LLM operations
   - **Context Preservation**: Maintains error history across retry attempts
   - **Intelligent Recovery**: Different strategies for different failure types
   - **Maximum 2 Attempts**: Prevents infinite retry loops

3. **LLM Interaction Resilience**:
   - JSON response format enforcement with validation
   - Fallback strategies for different failure modes
   - Comprehensive logging of raw LLM responses for debugging
   - Graceful degradation with meaningful error messages
   - Timeout handling and rate limiting awareness

4. **Vector Database Robustness**:
   - Connection retry mechanism with exponential backoff
   - Validation before vector operations
   - Proper error propagation to API layer
   - Rich metadata preservation even during partial failures

5. **Business Intelligence Features**:
   - **Performance Optimization**: Automatic detection and application of efficiency improvements
   - **Detailed Logging**: Comprehensive audit trail of all processing decisions
   - **Metadata Tracking**: Complete provenance from S3 source to final results
   - **Quality Assurance**: Multi-stage validation with clear status reporting

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
