# Smart Recruit API Documentation

## Overview
The Smart Recruit API is a FastAPI-based service for processing job descriptions (JDs) and CVs, ranking candidates, generating interview questions, and extracting searchable keywords. The API uses vector databases for similarity matching and LLM integration for intelligent processing.

**Base URL**: `http://localhost:8000`  
**API Version**: 1.0.0

---

## Endpoints

### 1. Health Check

#### `GET /`
**Description**: Root endpoint to check if the API is running.

**Request**: No parameters required

**Response**:
```json
{
  "message": "Smart Recruit API is running"
}
```

**Status Codes**:
- `200 OK`: API is running successfully

---

### 2. Upload Job Description from S3

#### `POST /s3-upload-jd`
**Description**: Upload and process a job description from an S3 location.

**Request Body**:
```json
{
  "s3_uri": "s3://bucket-name/path/to/job-description.pdf"
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `s3_uri` | string | Yes | S3 URI path to the job description file |

**Response**:
```json
{
  "jd_vectordb_id": "uuid-generated-jd-id",
  "filename": "job-description.pdf",
  "jd_data": {
    "job_title": "Senior Software Engineer",
    "company": "Tech Corp",
    "requirements": ["Python", "FastAPI", "Docker"],
    "experience_level": "Senior",
    "location": "Remote"
  }
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| `jd_vectordb_id` | string | Unique identifier for the job description |
| `filename` | string | Original filename of the uploaded file |
| `jd_data` | object | Structured data extracted from the JD by LLM |

**Status Codes**:
- `200 OK`: JD processed successfully
- `400 Bad Request`: Invalid S3 URI or file processing error
- `500 Internal Server Error`: Server error during processing

**Error Response Example**:
```json
{
  "detail": "S3 file processing error: File not found"
}
```

---

### 3. Upload CV from S3

#### `POST /s3-upload-cv`
**Description**: Upload and process a CV from an S3 location. CV will be stored independently and can be associated with job descriptions during the ranking phase.

**Request Body**:
```json
{
  "s3_uri": "s3://bucket-name/path/to/resume.pdf"
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `s3_uri` | string | Yes | S3 URI path to the CV file |

**Response**:
```json
{
  "cv_vectordb_id": "uuid-generated-cv-id",
  "success": true,
  "filename": "john-doe-resume.pdf",
  "cv_data": {
    "name": "John Doe",
    "email": "john.doe@email.com",
    "phone": "+1-555-0123",
    "skills": ["Python", "Machine Learning", "Docker"],
    "experience": [
      {
        "company": "Previous Corp",
        "position": "Software Engineer",
        "duration": "2020-2023"
      }
    ],
    "education": [
      {
        "degree": "Bachelor of Computer Science",
        "institution": "University Name",
        "year": "2020"
      }
    ]
  },
  "error": null
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| `cv_vectordb_id` | string | Unique identifier for the CV |
| `success` | boolean | Whether the CV was processed successfully |
| `filename` | string | Original filename of the uploaded CV |
| `cv_data` | object | Structured data extracted from the CV by LLM |
| `error` | string/null | Error message if processing failed |

**Status Codes**:
- `200 OK`: CV processed successfully (check `success` field for actual status)
- `400 Bad Request`: Invalid S3 URI or file processing error
- `500 Internal Server Error`: Server error during processing

**Error Response Example**:
```json
{
  "cv_vectordb_id": "uuid-generated-cv-id",
  "success": false,
  "filename": "resume.pdf",
  "cv_data": {
    "error": "LLM Parsing Error: Unable to extract structured data"
  },
  "error": "LLM Parsing Error: Unable to extract structured data"
}
```

---

### 4. Rank CVs

#### `POST /rank-cvs`
**Description**: Rank multiple CVs against a job description using vector similarity and LLM reasoning.

**Request Body**:
```json
{
  "jd_id": "uuid-of-job-description",
  "cv_ids": [
    "uuid-cv-1",
    "uuid-cv-2",
    "uuid-cv-3"
  ],
  "top_n": 10
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jd_id` | string | Yes | Job description ID to rank against |
| `cv_ids` | array[string] | Yes | List of CV IDs to rank |
| `top_n` | integer | No | Number of top candidates to return (default: 10) |

**Response**:
```json
{
  "rankings": [
    {
      "cv_id": "uuid-cv-1",
      "score": 8.5,
      "evaluation": {
        "filename": "CV_uuid-cv-1",
        "llm_skills_evaluation": [
          "Excellent Python programming skills",
          "Strong experience with FastAPI",
          "Docker containerization expertise"
        ],
        "llm_experience_evaluation": [
          "5+ years relevant experience",
          "Led multiple projects",
          "Experience with similar technologies"
        ],
        "llm_additional_points": [
          "Open source contributions",
          "Technical leadership experience"
        ],
        "llm_overall_assessment": "Highly qualified candidate with strong technical background and leadership experience"
      }
    },
    {
      "cv_id": "uuid-cv-2",
      "score": 7.2,
      "evaluation": {
        "filename": "CV_uuid-cv-2",
        "llm_skills_evaluation": [
          "Good Python skills",
          "Basic FastAPI knowledge"
        ],
        "llm_experience_evaluation": [
          "3 years relevant experience",
          "Good project experience"
        ],
        "llm_additional_points": [
          "Quick learner",
          "Team collaboration skills"
        ],
        "llm_overall_assessment": "Solid candidate with good potential for growth"
      }
    }
  ]
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| `rankings` | array[object] | List of ranked CV results |
| `rankings[].cv_id` | string | CV identifier |
| `rankings[].score` | number | LLM-generated ranking score (0-10) |
| `rankings[].evaluation` | object | Detailed evaluation breakdown |
| `rankings[].evaluation.filename` | string | CV filename |
| `rankings[].evaluation.llm_skills_evaluation` | array[string] | Skills assessment points |
| `rankings[].evaluation.llm_experience_evaluation` | array[string] | Experience assessment points |
| `rankings[].evaluation.llm_additional_points` | array[string] | Additional positive points |
| `rankings[].evaluation.llm_overall_assessment` | string | Overall candidate assessment |

**Status Codes**:
- `200 OK`: Ranking completed successfully
- `400 Bad Request`: Missing jd_id or cv_ids
- `500 Internal Server Error`: Server error during ranking process

---

### 5. Generate JD Keywords

#### `POST /keyword_generation`
**Description**: Generate searchable keywords for a job description to enhance discoverability and improve candidate matching.

**Request Body**:
```json
{
  "jd_id": "uuid-of-job-description"
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jd_id` | string | Yes | Job description ID to generate keywords for |

**Response**:
```json
{
  "jd_id": "uuid-of-job-description",
  "keywords": [
    "Software Development",
    "Backend Development", 
    "Web Development",
    "Tech Company",
    "Remote Work",
    "Senior Level",
    "API Development",
    "Cloud Computing",
    "Agile Environment"
  ],
  "error": null
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| `jd_id` | string | Job description identifier |
| `keywords` | array[string] | List of extracted searchable keywords |
| `error` | string/null | Error message if keyword generation failed |

**Keyword Categories**:
The generated keywords fall into these categories:
- **Industry Terms**: Healthcare, Fintech, E-commerce, SaaS, Manufacturing
- **Job Functions**: Software Development, Data Analysis, Project Management, Sales, Marketing
- **Work Environment**: Startup, Enterprise, Remote Work, Agile Environment
- **Experience Level**: Entry Level, Mid-Level, Senior, Leadership
- **Company Types**: Tech Company, Consulting, Non-profit, Government
- **Domain Areas**: Frontend Development, Backend Development, Full Stack, DevOps
- **Work Arrangements**: Remote Work, Hybrid, On-site, Flexible Hours
- **Team Dynamics**: Cross-functional, Team Lead, Individual Contributor
- **Business Context**: B2B, B2C, Client Facing, Internal Tools

**Status Codes**:
- `200 OK`: Keywords generated successfully
- `400 Bad Request`: Missing or empty jd_id
- `404 Not Found`: JD not found in database
- `500 Internal Server Error`: Server error during keyword generation

**Error Response Example**:
```json
{
  "jd_id": "uuid-of-job-description",
  "keywords": [],
  "error": "JD not found for ID: uuid-of-job-description"
}
```

---

### 6. Generate Interview Questions

#### `POST /generate-questions`
**Description**: Generate interview questions based on a job description and selected CV.

**Request Body**:
```json
{
  "jd_id": "uuid-of-job-description",
  "cv_id": "uuid-of-selected-cv"
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jd_id` | string | Yes | Job description ID |
| `cv_id` | string | Yes | CV ID to generate questions for |

**Response**:
```json
{
  "cv_id": "uuid-of-selected-cv",
  "jd_id": "uuid-of-job-description",
  "technical_questions": [
    {
      "question": "Can you explain your experience with FastAPI and how you've used it in production environments?",
      "category": "Technical - Web Frameworks",
      "good_answer_pointers": [
        "Mentions specific FastAPI features used",
        "Discusses performance considerations",
        "Talks about API documentation and testing"
      ],
      "unsure_answer_pointers": [
        "Vague responses about web development",
        "No specific FastAPI experience mentioned",
        "Confuses FastAPI with other frameworks"
      ],
      "rationale": null
    },
    {
      "question": "How would you approach containerizing a Python application using Docker?",
      "category": "Technical - DevOps",
      "good_answer_pointers": [
        "Mentions Dockerfile best practices",
        "Discusses multi-stage builds",
        "Talks about security considerations"
      ],
      "unsure_answer_pointers": [
        "Only basic Docker knowledge",
        "No mention of optimization",
        "Security concerns not addressed"
      ],
      "rationale": null
    }
  ],
  "general_behavioral_questions": [
    {
      "question": "Tell me about a time when you had to lead a technical project with tight deadlines.",
      "category": "Leadership",
      "good_answer_pointers": [
        "Specific example with clear context",
        "Demonstrates leadership skills",
        "Shows problem-solving abilities"
      ],
      "unsure_answer_pointers": [
        "Vague or generic responses",
        "No specific examples",
        "Focuses only on individual work"
      ],
      "rationale": null
    }
  ]
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| `cv_id` | string | CV identifier |
| `jd_id` | string | Job description identifier |
| `technical_questions` | array[object] | List of technical interview questions |
| `general_behavioral_questions` | array[object] | List of behavioral interview questions |

**Question Object Schema**:
| Field | Type | Description |
|-------|------|-------------|
| `question` | string | The interview question text |
| `category` | string | Question category/topic |
| `good_answer_pointers` | array[string] | Points that indicate a good answer |
| `unsure_answer_pointers` | array[string] | Points that indicate uncertainty or poor answers |
| `rationale` | string/null | Reasoning behind the question (currently null) |

**Status Codes**:
- `200 OK`: Questions generated successfully
- `400 Bad Request`: Missing jd_id or cv_id
- `404 Not Found`: JD or CV not found in database
- `500 Internal Server Error`: Server error during question generation

---

## Error Handling

All endpoints follow consistent error response format:

```json
{
  "detail": "Error description message"
}
```

### Common Error Codes:
- `400 Bad Request`: Invalid input parameters or request format
- `404 Not Found`: Requested resource not found
- `500 Internal Server Error`: Unexpected server error

---


## Data Flow

1. **Upload JD**: Upload job description via S3 → Store in vector DB → Extract structured data via LLM
2. **Upload CV**: Upload CV via S3 → Store in vector DB → Extract structured data via LLM (independent of JDs)
3. **Generate JD Keywords**: Extract searchable keywords from existing JD using LLM for better discoverability
4. **Rank CVs**: Compare multiple CVs against JD using vector similarity and LLM evaluation (associates CVs with JDs)
5. **Generate Questions**: Create personalized interview questions based on JD-CV pair

---

## Dependencies

- **Vector Database**: Qdrant for similarity search
- **LLM Integration**: LiteLLM for structured data extraction and evaluation
- **File Storage**: AWS S3 for document storage
- **MCP Integration**: FastAPI-MCP for Model Context Protocol support
- **Keyword Extraction**: Specialized LLM prompts for extracting searchable keywords from job descriptions

---

## Notes

- All file processing supports PDF and DOCX formats
- The API includes retry mechanisms for CV processing (2 attempts with 3-second delays)
- LLM ranking scores range from 0-10
- All operations are logged for debugging and monitoring purposes 