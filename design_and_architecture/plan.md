# Smart Recruit - High-Level Design

## 1. Project Overview

Smart Recruit is an AI-powered recruitment assistant system designed to streamline the hiring process by automating CV parsing, job description analysis, candidate ranking, and interview question generation. The system leverages Large Language Models (LLMs) and vector similarity search to provide accurate, context-aware matching between job descriptions and candidate resumes.

## 2. System Architecture

Smart Recruit employs a modern architecture with the following components:

1. **Frontend**: A Streamlit-based user interface for recruiter interaction
2. **Backend API**: A FastAPI application providing structured endpoints
3. **LLM Services**: Integration with multiple LLM providers for document analysis
4. **Vector Database**: Qdrant for efficient similarity search of documents
5. **Utilities**: Support modules for file handling, logging, and validation

```
Smart Recruit
├── Frontend (Streamlit) 
│   └── User Interface for JD/CV management, ranking, and questions
├── Backend API (FastAPI)
│   ├── JD Processing Endpoints
│   ├── CV Processing Endpoints
│   ├── Ranking Endpoints
│   └── Question Generation Endpoints
├── Core Services
│   ├── LLM Integration (Document parsing, enrichment, comparison)
│   ├── Vector Operations (Embedding generation, similarity search)
│   ├── JD/CV Repository Managers
│   └── Ranking/Question Generation Services
└── Supporting Infrastructure
    ├── Qdrant Vector Database
    ├── Logging System
    └── File Processing Utilities
```

## 3. Key Workflows

### 3.1 JD Processing Workflow
1. User uploads JD document (PDF/DOCX/TXT)
2. Backend processes document:
   - Extract structured data using LLM
   - Chunk document with LLM for semantic sections
   - Generate embeddings for each chunk
   - Store in vector database
3. Frontend displays structured JD data

### 3.2 CV Processing Workflow
1. User uploads multiple CV documents
2. Backend processes each CV:
   - Extract structured data using LLM
   - Chunk document with LLM for semantic sections
   - Generate embeddings for each chunk
   - Store in vector database with reference to active JD
3. Frontend displays structured CV data

### 3.3 CV Ranking Workflow
1. User requests ranking of CVs against active JD
2. Backend performs two-stage ranking:
   - Stage 1: Vector similarity ranking using embeddings
   - Stage 2: LLM-based detailed comparison for top candidates
3. Frontend displays ranked candidates with detailed reasoning

### 3.4 Question Generation Workflow
1. User selects a ranked candidate
2. Backend generates personalized interview questions:
   - Retrieves full JD and CV texts
   - LLM generates targeted technical and behavioral questions
3. Frontend displays categorized questions with answer pointers

## 4. Technology Stack

### 4.1 Core Technologies
- **Frontend**: Streamlit
- **Backend**: FastAPI
- **LLM Integration**: LiteLLM with support for multiple models
- **Vector Database**: Qdrant
- **Embedding Model**: Sentence Transformer (bge-large-en-v1.5)

### 4.2 Key Dependencies
- **Document Processing**: python-magic, python-docx
- **Data Validation**: Pydantic
- **API Communication**: Requests
- **Asynchronous Processing**: asyncio

## 5. Scalability Considerations

The system is designed with scalability in mind:

1. **Asynchronous Processing**: API endpoints and core processing functions use asyncio
2. **Modular Architecture**: Clear separation of concerns for easy component scaling
3. **Efficient Resource Usage**: Two-stage ranking to minimize expensive LLM calls
4. **Parallel Processing**: Batch processing capabilities for multiple documents
5. **Stateless Design**: Backend functions as a pure API service

## 6. Future Enhancement Areas

1. **Multimodal Analysis**: Enhanced capabilities for image-rich documents
2. **Feedback Loop**: Incorporate recruiter feedback to improve rankings
3. **Authentication & Authorization**: User management system
4. **Custom LLM Fine-tuning**: Domain-specific model optimization
5. **Integration**: Connections to ATS and HRIS systems
6. **Analytics Dashboard**: Metrics on hiring pipeline effectiveness
7. **Multi-language Support**: Handle documents in multiple languages

## 7. Deployment Architecture

The system can be deployed in various configurations:

1. **Development**: Local deployment with embedded Qdrant
2. **Production**: 
   - Containerized microservices (Docker)
   - Separate scaling for API and frontend
   - Managed Qdrant instance or self-hosted cluster
   - Secured access to LLM API providers
3. **Enterprise**: 
   - On-premises deployment options
   - Air-gapped LLM hosting for sensitive data
   - High-availability configuration

---

## 8. Module Responsibilities

### app.py (Streamlit App)
- Provides the user interface for uploading JDs and CVs.
- Handles user actions (upload, rank, generate questions) and navigation through a tab-based interface.
- Communicates with the FastAPI backend via HTTP requests to trigger processing.
- Maintains session state to preserve UI state across interactions.
- Displays structured data, processing status, ranking results, and generated questions.

### routes.py (FastAPI Backend)
- Defines RESTful API endpoints with FastAPI for JD processing, CV processing, ranking, and question generation.
- Receives requests from the Streamlit frontend and external clients.
- Handles file uploads with proper error handling and validation.
- Orchestrates calls to service layer modules in the src directory.
- Implements asynchronous request handling for better performance.
- Returns well-structured JSON responses following the defined schemas.

### config.py
- Stores global configuration settings for the application.
- Manages LLM model selection and API keys.
- Provides a function for retrieving appropriate LiteLLM parameters.
- Configures environment-specific settings.

### src/llm/ (LLM Integration)
- **client.py**: Configures LLM providers and model parameters
  - `get_litellm_params()`: Returns appropriate configuration for specified model
  - `get_api_key_for_model()`: Retrieves API key for a given model
- **parser.py**: Handles document parsing with LLM
  - `parse_document()`: Processes documents with LLM and validates against schema
- **chunker.py**: Manages document chunking with LLM
  - `chunk_document_with_llm()`: Divides documents into semantic chunks with LLM
- **utils.py**: Provides utility functions for LLM operations
  - `load_prompt()`: Loads and manages prompt templates

### src/services/ (Business Logic)
- **jd_service.py**: Handles JD processing workflows
  - `parse_jd_with_llm()`: Extracts structured data from JD
  - `process_jd()`: Complete JD processing including parsing and storage
- **cv_service.py**: Handles CV processing workflows
  - `parse_cv_with_llm()`: Extracts structured data from CV
  - `process_cv()`: Complete CV processing including parsing and storage
  - `process_multiple_cvs()`: Batch processes multiple CVs
- **ranking_service.py**: Implements CV ranking logic
  - `calculate_cv_ranking()`: Two-stage ranking process (vector similarity and LLM reasoning)
  - `get_llm_comparison_for_cv()`: Detailed LLM comparison between JD and CV
- **question_service.py**: Generates interview questions
  - `generate_candidate_questions()`: Creates personalized questions based on JD and CV

### src/vector_db/ (Vector Database Operations)
- **client.py**: Core vector operations
  - `initialize_qdrant_collections()`: Sets up vector collections
  - `get_embedding()`: Generates embeddings using Sentence Transformer
  - `search_similar_chunks()`: Performs similarity search
  - `get_full_document_text_from_db()`: Reconstructs full document text
- **jd_repository.py**: JD-specific vector operations
  - `add_jd_to_db()`: Processes and stores JD in vector DB
  - `get_jd_chunks()`: Retrieves chunks by JD ID
  - `get_full_jd_text()`: Gets full JD text
- **cv_repository.py**: CV-specific vector operations
  - `add_cv_to_db()`: Processes and stores CV in vector DB
  - `search_cv_chunks()`: Searches for CV chunks
  - `get_cvs_for_jd()`: Retrieves CVs associated with a JD

### src/schemas/ (Data Validation)
- **schemas.py**: Internal data models for validation
  - `JDOutput`: Structured JD data model
  - `CVOutput`: Structured CV data model
  - `LLMJdCvComparisonOutput`: CV comparison output model
  - `CandidateQuestionsOutput`: Question generation output model
- **api_schemas.py**: API request/response models
  - Request models for ranking, question generation
  - Response models for JD upload, CV upload, ranking, questions

### src/utils/ (Utilities)
- **file_handler.py**: Handles file operations
  - `process_uploaded_file_content()`: Processes uploaded files
- **logging.py**: Configures logging
  - `get_logger()`: Gets logger instance
- **validators.py**: Data validation utilities
  - Functions for validating IDs, file types, requests

### src/prompts/ (LLM Prompt Templates)
- **json_output_jd_prompt.md**: For JD parsing into structured JSON
- **json_output_cv_prompt.md**: For CV parsing into structured JSON
- **jd_enrich_prompt.md**: For JD chunking and enrichment
- **cv_enrich_prompt.md**: For CV chunking and enrichment
- **jd_cv_comparison_prompt.md**: For detailed JD-CV comparison
- **candidate_questions_prompt.md**: For interview question generation

---

## 9. Data Flow Summary

1.  **User uploads JD/CVs (PDFs, DOCX, TXT) via Streamlit UI.**
2.  **`app.py`** sends file contents to **`routes.py`** API endpoints via HTTP requests.
3.  **Backend Processing (JD Example):**
    *   **Structured Parsing**: `routes.py` calls `src/services/jd_service.parse_jd_with_llm()`, which uses `src/llm/parser.parse_document()` with `prompts/json_output_jd_prompt.md` to extract structured data from the JD.
    *   **Chunking & Vectorization**: `routes.py` calls `src/services/jd_service.process_jd()`, which:
        *   Uses `src/llm/chunker.chunk_document_with_llm()` with `prompts/jd_enrich_prompt.md` to divide the document into semantic chunks.
        *   Each chunk contains `og_content` (original text) and `enriched_content` (LLM-enhanced text).
        *   Calls `src/vector_db/jd_repository.add_jd_to_db()` to process and store chunks.
        *   For each chunk, the `enriched_content` is embedded using the Sentence Transformer model.
        *   Stores original content, enriched content, embeddings, and metadata in Qdrant.
4.  **CV Processing is analogous**, using `src/services/cv_service` with appropriate CV-specific prompts and repositories.
5.  **Ranking:**
    *   Triggered from UI, handled by `routes.py` calling `src/services/ranking_service.calculate_cv_ranking()`.
    *   Initial vector similarity stage uses `src/vector_db/client.search_similar_chunks()` to find best matches based on embedding similarity.
    *   LLM reasoning stage retrieves full documents via `get_full_document_text_from_db()` and compares with LLM using `prompts/jd_cv_comparison_prompt.md`.
6.  **Question Generation:**
    *   Triggered from UI, handled by `routes.py` calling `src/services/question_service.generate_candidate_questions()`.
    *   Retrieves full JD and CV texts, then uses LLM with `prompts/candidate_questions_prompt.md` to generate questions.
7.  **Results are returned to the frontend** for display to the user.

---

## 10. Extensibility

- Modular design allows for adding new LLM prompts, models (via `config.py`), or ranking strategies.
- Schemas in `schemas/` can be updated to change data structures.
- Centralized `config.py` for API keys and model choices.

---

## 11. Technology Used

| Category             | Technology                                     | Purpose                                                                 |
|----------------------|------------------------------------------------|-------------------------------------------------------------------------|
| Frontend Framework   | Streamlit                                      | User Interface                                                          |
| Backend Framework    | FastAPI                                        | API Endpoints, Orchestration                                            |
| Unified Model Access | LiteLLM                                        | Interface with various LLMs (Multimodal for parsing/chunking, Text for reasoning) |
| Validation Layer     | Pydantic                                       | Data validation and schema definition                                   |
| Embedding Model      | Sentence Transformer (`bge-large-en-v1.5`)      | Generating 1024-dimension embeddings from text chunks                     |
| Vector Database      | Qdrant                                         | Storage and similarity search of document chunk embeddings              |

---

## 12. Example Processing Scenario (Conceptual Update)

The core idea remains: unstructured PDF -> structured JSON -> chunked & enriched text -> embeddings -> similarity search -> LLM reasoning.

Key difference in flow:
- PDF base64 is first sent to a **Multimodal LLM** with an "enrichment" prompt (e.g., `prompts/JD_enrich_prompt.md`) to get `og_content` and `enriched_content` for each chunk.
- The `enriched_content` of these chunks is then fed to the **Sentence Transformer** to create embeddings for Qdrant.
- The `og_content` is stored and used later for reconstructing full documents for the **Text LLM** reasoning stages (ranking, question generation).

This ensures that embeddings are generated from LLM-refined text, potentially improving relevance, while the original text is preserved for human readability and detailed LLM analysis.

---

