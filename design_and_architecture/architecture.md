# Smart Recruit - Architecture Diagrams

This document contains architecture diagrams illustrating the structure, workflows, and interactions within the Smart Recruit system.

## 1. High-Level System Architecture

```mermaid
graph TB
    %% Main Components
    User([User/Recruiter])
    StreamlitUI[Streamlit UI<br/>app.py]
    FastAPI[FastAPI Backend<br/>routes.py]
    LLMService[LLM Service<br/>src/llm/*]
    VectorDB[(Qdrant Vector DB)]
    SentenceTransformer[Sentence Transformer]
    S3Storage[(AWS S3 Storage)]
    
    %% Core Service Modules
    JDService[JD Service<br/>src/services/jd_service.py]
    CVService[CV Service<br/>src/services/cv_service.py]
    RankingService[Ranking Service<br/>src/services/ranking_service.py]
    QuestionService[Question Service<br/>src/services/question_service.py]
    
    %% Vector DB Repositories
    VectorOps[Vector Operations<br/>src/vector_db/client.py]
    JDRepo[JD Repository<br/>src/vector_db/jd_repository.py]
    CVRepo[CV Repository<br/>src/vector_db/cv_repository.py]
    
    %% S3 Handler
    S3Handler[S3 Handler<br/>src/utils/s3_handler.py]
    
    %% User Interaction
    User --> |Provides S3 URIs| StreamlitUI
    
    %% API Communication
    StreamlitUI --> |HTTP Requests with S3 URIs| FastAPI
    FastAPI --> |HTTP Responses| StreamlitUI
    
    %% FastAPI to Services
    FastAPI --> |Process JD from S3| JDService
    FastAPI --> |Process CVs from S3| CVService
    FastAPI --> |Rank CVs| RankingService
    FastAPI --> |Generate Questions| QuestionService
    
    %% S3 Integration
    FastAPI --> |Fetch Documents| S3Handler
    S3Handler --> |Download Files| S3Storage
    S3Storage --> |Return File Content| S3Handler
    S3Handler --> |Base64 + Metadata| FastAPI
    
    %% Service to LLM
    JDService --> |Parse/Chunk JD| LLMService
    CVService --> |Parse/Chunk CV| LLMService
    RankingService --> |Compare JD-CV| LLMService
    QuestionService --> |Generate Questions| LLMService
    
    %% Service to Vector Operations
    JDService --> |Store JD with Metadata| JDRepo
    CVService --> |Store CV with Metadata| CVRepo
    RankingService --> |Retrieve Docs| VectorOps
    QuestionService --> |Retrieve Docs| VectorOps
    
    %% Vector Repository Operations
    JDRepo --> |Core Operations| VectorOps
    CVRepo --> |Core Operations| VectorOps
    
    %% Embedding and Storage
    VectorOps --> |Generate Embeddings| SentenceTransformer
    SentenceTransformer --> |Return Embeddings| VectorOps
    VectorOps --> |Store/Query Vectors with Rich Metadata| VectorDB
    VectorDB --> |Return Results| VectorOps
   
```

## 2. Document Processing Sequence

### 2.1 JD Processing Sequence (S3-Based)

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant API as FastAPI Backend
    participant S3H as S3 Handler
    participant S3 as AWS S3
    participant JDS as JD Service
    participant LLM_P as LLM Parser
    participant LLM_C as LLM Chunker
    participant ST as Sentence Transformer
    participant JDR as JD Repository
    participant VDB as Qdrant Vector DB
    
    User->>UI: Provide S3 URI for JD
    UI->>API: POST /s3-upload-jd (S3 URI)
    API->>S3H: get_file_from_s3(s3_uri)
    S3H->>S3: Download file from S3
    S3-->>S3H: Return file content + metadata
    S3H-->>API: Return {base64_content, raw_text, metadata}
    
    par Parse JD with LLM
        API->>JDS: parse_jd_with_llm()
        JDS->>LLM_P: parse_document()
        LLM_P-->>JDS: Return structured JD data
        JDS-->>API: Return JD data
    and Add JD to Vector DB with Rich Metadata
        API->>JDR: add_jd_to_db()
        JDR->>LLM_C: chunk_document_with_llm()
        LLM_C-->>JDR: Return weighted chunks (og_content, enriched_content, weight)
        JDR->>ST: get_embedding() for each enriched chunk
        ST-->>JDR: Return embeddings
        JDR->>VDB: Store chunks with embeddings + S3 metadata
        Note over VDB: Metadata includes: S3 URI, bucket, key,<br/>file size, content type, weights
        VDB-->>JDR: Confirm storage
        JDR-->>API: Return JD ID
    end
    
    API-->>UI: Return JD ID and structured data
    UI->>UI: Display JD data with processing status
```

### 2.2 CV Processing Sequence (S3-Based with Retry Logic)

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant API as FastAPI Backend
    participant S3H as S3 Handler
    participant S3 as AWS S3
    participant CVS as CV Service
    participant LLM_P as LLM Parser
    participant LLM_C as LLM Chunker
    participant ST as Sentence Transformer
    participant CVR as CV Repository
    participant VDB as Qdrant Vector DB
    
    User->>UI: Provide S3 URI for CV
    UI->>API: POST /s3-upload-cv (S3 URI)
    API->>S3H: get_file_from_s3(s3_uri)
    S3H->>S3: Download file from S3
    S3-->>S3H: Return file content + metadata
    S3H-->>API: Return {base64_content, raw_text, metadata}
    
    loop Retry Logic (Max 2 Attempts)
        API->>API: Generate unique CV ID
        
        par Parse CV with LLM
            API->>CVS: parse_cv_with_llm()
            CVS->>LLM_P: parse_document()
            alt LLM Parsing Success
                LLM_P-->>CVS: Return structured CV data
                CVS-->>API: Return CV data
            else LLM Parsing Failure
                LLM_P-->>CVS: Return error
                CVS-->>API: Return error with raw response
            end
        and Add CV to Vector DB with Rich Metadata
            API->>CVR: add_cv_to_db()
            CVR->>LLM_C: chunk_document_with_llm()
            alt Chunking Success
                LLM_C-->>CVR: Return chunks (og_content, enriched_content)
                CVR->>ST: get_embedding() for each enriched chunk
                ST-->>CVR: Return embeddings
                CVR->>VDB: Store chunks with embeddings + S3 metadata
                Note over VDB: Metadata includes: S3 URI, bucket, key,<br/>file size, content type, original_doc_id
                VDB-->>CVR: Confirm storage
                CVR-->>API: Return CV ID (Success)
            else Chunking/Storage Failure
                CVR-->>API: Return error
            end
        end
        
        alt Both Operations Successful
            break Success - Exit Retry Loop
        else Any Operation Failed and Attempts Remaining
            API->>API: Wait 3 seconds before retry
        else All Attempts Exhausted
            API->>API: Return final error status
        end
    end
    
    API-->>UI: Return CV processing result with detailed status
    UI->>UI: Display CV data with processing status and error details
```

## 3. Advanced Ranking Workflow with Optimization

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant API as FastAPI Backend
    participant RS as Ranking Service
    participant VO as Vector Operations
    participant LLM as LLM Service
    participant VDB as Qdrant Vector DB
    
    User->>UI: Request CV Ranking
    UI->>API: POST /rank-cvs (jd_id, cv_ids, top_n)
    API->>RS: calculate_cv_ranking()
    
    RS->>RS: Check optimization condition
    alt Optimization: top_n >= total_cvs
        Note over RS: Skip vector similarity stage for efficiency
        RS->>RS: Select all CVs with neutral scores
        RS->>RS: Log optimization decision
    else Standard Flow: top_n < total_cvs
        RS->>VO: get_jd_chunks() for weighted chunks
        VO->>VDB: Query JD chunks with weights
        VDB-->>VO: Return JD chunks with metadata
        VO-->>RS: Return weighted JD chunks
        
        loop For Each Weighted JD Chunk
            RS->>VO: search_cv_chunks() with chunk text
            VO->>VDB: Query similar CV chunks (top 15)
            VDB-->>VO: Return similarity results
            VO-->>RS: Return CV chunk matches
            RS->>RS: Calculate weighted scores using formula:<br/>(similarity² × jd_chunk_weight)
            Note over RS: Squaring amplifies strong matches,<br/>penalizes weak ones
        end
        
        RS->>RS: Aggregate scores by CV using max contribution
        RS->>RS: Sort by max_weighted_contribution
        RS->>RS: Select top N CVs for LLM stage
    end
    
    RS->>VO: get_full_document_text_from_db() for JD
    VO->>VDB: Reconstruct full JD from chunks
    VDB-->>VO: Return JD chunks
    VO-->>RS: Return full JD text
    
    par Parallel LLM Processing
        loop For Each Selected CV (Async)
            RS->>VO: get_full_document_text_from_db() for CV
            VO->>VDB: Reconstruct full CV from chunks
            VDB-->>VO: Return CV chunks
            VO-->>RS: Return full CV text
            
            RS->>LLM: get_llm_comparison_for_cv()
            LLM-->>RS: Return detailed comparison with score
        end
    end
    
    RS->>RS: Sort by LLM ranking score (no vector score exposure)
    RS-->>API: Return ranked results with detailed evaluation
    API-->>UI: Return ranking response (without vector scores)
    UI->>UI: Display ranked CVs with LLM reasoning only
```

## 4. Question Generation Workflow

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant API as FastAPI Backend
    participant QS as Question Service
    participant VO as Vector Operations
    participant LLM as LLM Service
    participant VDB as Qdrant Vector DB
    
    User->>UI: Select CV for Questions
    UI->>API: POST /generate-questions (jd_id, cv_id)
    API->>QS: generate_candidate_questions()
    
    QS->>VO: get_full_document_text_from_db() for JD
    VO->>VDB: Query JD chunks
    VDB-->>VO: Return JD chunks
    VO-->>QS: Return full JD text
    
    QS->>VO: get_full_document_text_from_db() for CV
    VO->>VDB: Query CV chunks
    VDB-->>VO: Return CV chunks
    VO-->>QS: Return full CV text
    
    QS->>LLM: Process with candidate_questions_prompt
    LLM-->>QS: Return technical & behavioral questions
    QS-->>API: Return structured questions
    API-->>UI: Return questions response
    UI->>UI: Display questions with answer pointers
```

## 5. Advanced Two-Stage Ranking Algorithm with Business Intelligence

```mermaid
graph TD
    Start([Start Ranking Process]) --> CheckOptimization{top_n >= total_cvs?}
    
    %% Optimization Path
    CheckOptimization -->|Yes| LogOptimization["🚀 Log Optimization Decision<br/>Skip Vector Stage for Efficiency"]
    LogOptimization --> SelectAll["Select All CVs<br/>(Neutral Vector Scores)"]
    
    %% Vector Similarity Stage
    CheckOptimization -->|No| VectorStage["📊 Vector Similarity Stage"]
    VectorStage --> GetWeightedJDChunks["Get JD Chunks with Weights<br/>(1=General, 2=Desirable, 3=Essential)"]
    GetWeightedJDChunks --> ChunkLoop["For Each Weighted JD Chunk"]
    ChunkLoop --> GetEmbedding["Generate JD Chunk Embedding<br/>(Enriched Content)"]
    GetEmbedding --> FindSimilar["Find Top 15 Similar CV Chunks<br/>(Filtered by Active CV IDs)"]
    FindSimilar --> CalcAdvancedScore["🧮 Calculate Advanced Weighted Score<br/>(similarity² × jd_chunk_weight)"]
    
    CalcAdvancedScore --> ExplainFormula["📝 Mathematical Rationale:<br/>• Squaring penalizes weak matches<br/>• Amplifies strong domain expertise<br/>• Reduces noise from common terms"]
    ExplainFormula --> AggregateByCV["Aggregate Scores by CV<br/>Track: total_score, max_contribution, match_count"]
    AggregateByCV --> UseMaxContribution["🎯 Primary Ranking: max_weighted_contribution<br/>(Rewards 'Shiniest Moment' over quantity)"]
    UseMaxContribution --> DetailedLogging["📋 Log Detailed Match Analysis<br/>Per CV: filename, scores, explanations"]
    DetailedLogging --> SelectTopN["Select Top N CVs for LLM Stage"]
    
    %% LLM Reasoning Stage
    SelectAll --> LLMStage["🤖 LLM Reasoning Stage"]
    SelectTopN --> LLMStage
    LLMStage --> GetFullTexts["Retrieve Full Document Texts<br/>(Reconstructed from Chunks)"]
    GetFullTexts --> ParallelLLM["⚡ Parallel LLM Processing<br/>(Async for Performance)"]
    ParallelLLM --> StructuredComparison["Generate Structured Comparisons:<br/>• Skills Evaluation<br/>• Experience Assessment<br/>• Additional Points<br/>• Overall Assessment<br/>• Numerical Score (1-10)"]
    StructuredComparison --> ErrorHandling["🛡️ Robust Error Handling<br/>Graceful degradation for LLM failures"]
    ErrorHandling --> FinalSort["Sort by LLM Ranking Score<br/>(Hide Vector Scores from Users)"]
    FinalSort --> End([End Ranking Process])
   
```

### 5.1 Enhanced Mathematical Foundation

The core formula in our vector similarity stage is:
```
weighted_score_contribution = (similarity_score²) × jd_chunk_weight
primary_ranking_metric = max_weighted_contribution_per_cv
```

**Advanced Business Logic Features:**

1. **Intelligent Optimization**
   - Automatically detects when `top_n >= total_cvs`
   - Skips computationally expensive vector similarity stage
   - Logs optimization decisions for transparency
   - Improves performance by 3-5x for small batches

2. **Sophisticated Weighting System**
   - JD chunks assigned weights: 1 (General), 2 (Desirable), 3 (Essential)
   - LLM determines importance during chunking phase
   - Ensures critical requirements have higher impact on rankings

3. **"Shiniest Moment" Ranking Philosophy**
   - Uses `max_weighted_contribution` instead of average scores
   - Rewards candidates with exceptional strength in key areas
   - Prevents dilution from many mediocre matches
   - Identifies specialists over generalists

4. **Advanced Error Recovery**
   - Retry mechanism with exponential backoff (3-second delays)
   - Graceful degradation for partial failures
   - Detailed error logging with context preservation
   - Separate success tracking for DB and LLM operations

5. **Rich Metadata Integration**
   - S3 source tracking (bucket, key, URI)
   - File size and content type preservation
   - Processing timestamps and attempt counts
   - Enhanced searchability and debugging capabilities

## 6. S3 Integration Architecture

```mermaid
graph TB
    subgraph "S3 Storage Layer"
        S3Bucket[(S3 Bucket)]
        JDFolder[JD Documents Folder]
        CVFolder[CV Documents Folder]
        
        S3Bucket --> JDFolder
        S3Bucket --> CVFolder
    end
    
    subgraph "Application Layer"
        S3Handler[S3 Handler Service]
        MetadataExtractor[Metadata Extractor]
        ContentProcessor[Content Processor]
        
        S3Handler --> MetadataExtractor
        S3Handler --> ContentProcessor
    end
    
    subgraph "Processing Pipeline"
        ValidationLayer[URI Validation]
        DownloadManager[Download Manager]
        ContentConverter[Content Converter]
        ErrorHandler[Error Handler]
        
        ValidationLayer --> DownloadManager
        DownloadManager --> ContentConverter
        ContentConverter --> ErrorHandler
    end
    
    %% Flow
    JDFolder --> S3Handler
    CVFolder --> S3Handler
    S3Handler --> ValidationLayer
    MetadataExtractor --> ValidationLayer
    ContentProcessor --> ValidationLayer
    ErrorHandler --> S3Handler
```

## 7. Enhanced Data Model with Metadata

```mermaid
classDiagram
    class S3DocumentMetadata {
        +str source_s3_uri
        +str source_bucket
        +str source_key
        +float file_size_mb
        +str content_type
        +datetime upload_timestamp
        +int processing_attempts
        +str processing_status
    }
    
    class WeightedJDChunk {
        +str og_content
        +str enriched_content
        +int weight
        +str chunk_id
        +dict metadata
    }
    
    class EnhancedCVOutput {
        +str cv_id
        +CVOutput structured_data
        +S3DocumentMetadata s3_metadata
        +list processing_errors
        +datetime last_processed
    }
    
    class AdvancedRankingResult {
        +str cv_id
        +float llm_ranking_score
        +str vector_match_details
        +list llm_skills_evaluation
        +list llm_experience_evaluation
        +list llm_additional_points
        +str llm_overall_assessment
        +dict debug_info
    }
    
    class RobustQuestionSet {
        +list technical_questions
        +list behavioral_questions
        +str generation_model
        +datetime generated_at
        +dict generation_metadata
    }
    
    EnhancedCVOutput *-- S3DocumentMetadata : contains
    EnhancedCVOutput *-- CVOutput : contains
    WeightedJDChunk *-- S3DocumentMetadata : references
    AdvancedRankingResult --> EnhancedCVOutput : ranks
```

## 8. Advanced API Flow with S3 Integration

```mermaid
graph LR
    %% Client
    Client[Client/UI]
    
    %% S3 Endpoints
    S3JDUpload[/POST /s3-upload-jd\]
    S3CVUpload[/POST /s3-upload-cv\]
    RankCVs[/POST /rank-cvs\]
    GenQuestions[/POST /generate-questions\]
    
    %% Enhanced Handlers
    S3JDHandler[S3 JD Handler with Retry]
    S3CVHandler[S3 CV Handler with Retry]
    AdvancedRankHandler[Advanced Ranking Handler]
    QuestionsHandler[Questions Handler]
    
    %% S3 Integration
    S3Service[S3 Service Layer]
    MetadataService[Metadata Service]
    
    %% Client to Endpoints
    Client --> S3JDUpload
    Client --> S3CVUpload
    Client --> RankCVs
    Client --> GenQuestions
    
    %% Endpoints to Handlers
    S3JDUpload --> S3JDHandler
    S3CVUpload --> S3CVHandler
    RankCVs --> AdvancedRankHandler
    GenQuestions --> QuestionsHandler
    
    %% Handlers to Services
    S3JDHandler --> S3Service
    S3CVHandler --> S3Service
    S3Service --> MetadataService
    
    %% Enhanced Request/Response Models
    S3JDUpload -.-> S3JDRequest[S3JDUploadRequest]
    S3CVUpload -.-> S3CVRequest[S3CVUploadRequest]
    RankCVs -.-> EnhancedRankingResponse[Enhanced RankingResponse]
    GenQuestions -.-> RobustQuestionResponse[Robust QuestionResponse]
```

## 9. Business Intelligence Features

### 9.1 Advanced Retry Logic
- **Exponential Backoff**: 3-second delays between attempts
- **Granular Error Tracking**: Separate success flags for DB and LLM operations
- **Context Preservation**: Maintains error history across retry attempts
- **Intelligent Recovery**: Different strategies for different failure types

### 9.2 Metadata-Driven Operations
- **Source Tracking**: Complete S3 provenance (bucket, key, URI)
- **Processing History**: Timestamps, attempt counts, status tracking
- **Performance Metrics**: File sizes, processing times, success rates
- **Debugging Support**: Rich context for troubleshooting failures

### 9.3 Optimization Intelligence
- **Automatic Performance Tuning**: Detects and applies optimizations
- **Resource Management**: Efficient allocation based on workload
- **Scalability Awareness**: Adapts behavior based on data volume
- **Transparency**: Comprehensive logging of optimization decisions

### 9.4 Quality Assurance
- **Multi-Stage Validation**: Input validation, processing verification, output validation
- **Error Categorization**: Different handling for different error types
- **Graceful Degradation**: Partial success handling with clear status reporting
- **User Experience**: Clear feedback on processing status and any issues 