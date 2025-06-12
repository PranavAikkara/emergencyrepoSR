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
    
    %% Core Service Modules
    JDService[JD Service<br/>src/services/jd_service.py]
    CVService[CV Service<br/>src/services/cv_service.py]
    RankingService[Ranking Service<br/>src/services/ranking_service.py]
    QuestionService[Question Service<br/>src/services/question_service.py]
    
    %% Vector DB Repositories
    VectorOps[Vector Operations<br/>src/vector_db/client.py]
    JDRepo[JD Repository<br/>src/vector_db/jd_repository.py]
    CVRepo[CV Repository<br/>src/vector_db/cv_repository.py]
    
    %% User Interaction
    User --> |Interacts with| StreamlitUI
    
    %% API Communication
    StreamlitUI --> |HTTP Requests| FastAPI
    FastAPI --> |HTTP Responses| StreamlitUI
    
    %% FastAPI to Services
    FastAPI --> |Process JD| JDService
    FastAPI --> |Process CVs| CVService
    FastAPI --> |Rank CVs| RankingService
    FastAPI --> |Generate Questions| QuestionService
    
    %% Service to LLM
    JDService --> |Parse/Chunk JD| LLMService
    CVService --> |Parse/Chunk CV| LLMService
    RankingService --> |Compare JD-CV| LLMService
    QuestionService --> |Generate Questions| LLMService
    
    %% Service to Vector Operations
    JDService --> |Store JD| JDRepo
    CVService --> |Store CV| CVRepo
    RankingService --> |Retrieve Docs| VectorOps
    QuestionService --> |Retrieve Docs| VectorOps
    
    %% Vector Repository Operations
    JDRepo --> |Core Operations| VectorOps
    CVRepo --> |Core Operations| VectorOps
    
    %% Embedding and Storage
    VectorOps --> |Generate Embeddings| SentenceTransformer
    SentenceTransformer --> |Return Embeddings| VectorOps
    VectorOps --> |Store/Query Vectors| VectorDB
    VectorDB --> |Return Results| VectorOps
   
```

## 2. Document Processing Sequence

### 2.1 JD Processing Sequence

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant API as FastAPI Backend
    participant JDS as JD Service
    participant LLM_P as LLM Parser
    participant LLM_C as LLM Chunker
    participant ST as Sentence Transformer
    participant JDR as JD Repository
    participant VDB as Qdrant Vector DB
    
    User->>UI: Upload JD Document
    UI->>API: POST /upload-jd (with file)
    API->>API: Process file content
    
    par Parse JD with LLM
        API->>JDS: parse_jd_with_llm()
        JDS->>LLM_P: parse_document()
        LLM_P-->>JDS: Return structured JD data
        JDS-->>API: Return JD data
    and Add JD to Vector DB
        API->>JDS: process_jd()
        JDS->>LLM_C: chunk_document_with_llm()
        LLM_C-->>JDS: Return chunks (og_content, enriched_content, weight)
        JDS->>JDR: add_jd_to_db()
        JDR->>ST: get_embedding() for each chunk
        ST-->>JDR: Return embeddings
        JDR->>VDB: Store chunks with embeddings
        VDB-->>JDR: Confirm storage
        JDR-->>JDS: Return JD ID
        JDS-->>API: Return JD ID
    end
    
    API-->>UI: Return JD ID and structured data
    UI->>UI: Display JD data
```

### 2.2 CV Processing Sequence

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant API as FastAPI Backend
    participant CVS as CV Service
    participant LLM_P as LLM Parser
    participant LLM_C as LLM Chunker
    participant ST as Sentence Transformer
    participant CVR as CV Repository
    participant VDB as Qdrant Vector DB
    
    User->>UI: Upload Multiple CVs
    UI->>API: POST /upload-cvs (with files, jd_id)
    
    loop For Each CV
        API->>API: Process file content
        
        par Parse CV with LLM
            API->>CVS: parse_cv_with_llm()
            CVS->>LLM_P: parse_document()
            LLM_P-->>CVS: Return structured CV data
            CVS-->>API: Return CV data
        and Add CV to Vector DB
            API->>CVS: process_cv()
            CVS->>LLM_C: chunk_document_with_llm()
            LLM_C-->>CVS: Return chunks (og_content, enriched_content)
            CVS->>CVR: add_cv_to_db()
            CVR->>ST: get_embedding() for each chunk
            ST-->>CVR: Return embeddings
            CVR->>VDB: Store chunks with embeddings and jd_id reference
            VDB-->>CVR: Confirm storage
            CVR-->>CVS: Return CV ID
            CVS-->>API: Return CV ID
        end
    end
    
    API-->>UI: Return CV IDs and structured data
    UI->>UI: Display CV data
```

## 3. Ranking Workflow

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
    
    alt Vector Similarity Stage (if top_n < total_cvs)
        RS->>VO: get_qdrantchunk_content() for JD
        VO->>VDB: Query JD chunks
        VDB-->>VO: Return JD chunks
        VO-->>RS: Return JD chunks
        
        loop For Each JD Chunk
            RS->>VO: search_similar_chunks()
            VO->>VDB: Query similar CV chunks
            VDB-->>VO: Return similar CV chunks
            VO-->>RS: Return similarity results
            RS->>RS: Calculate weighted scores
        end
        
        RS->>RS: Aggregate scores by CV
        RS->>RS: Select top N CVs
    else Skip Vector Stage (if top_n >= total_cvs)
        RS->>RS: Select all CVs
    end
    
    RS->>VO: get_full_document_text_from_db() for JD
    VO->>VDB: Query JD chunks
    VDB-->>VO: Return JD chunks
    VO-->>RS: Return full JD text
    
    loop For Each Selected CV
        RS->>VO: get_full_document_text_from_db() for CV
        VO->>VDB: Query CV chunks
        VDB-->>VO: Return CV chunks
        VO-->>RS: Return full CV text
        
        RS->>LLM: get_llm_comparison_for_cv()
        LLM-->>RS: Return detailed comparison
    end
    
    RS->>RS: Sort by LLM ranking score
    RS-->>API: Return ranked results with details
    API-->>UI: Return ranking response
    UI->>UI: Display ranked CVs with reasoning
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


## 5. Two-Stage Ranking Algorithm

```mermaid
graph TD
    Start([Start Ranking Process]) --> CheckOptimization{top_n >= total_cvs?}
    
    %% Vector Similarity Stage
    CheckOptimization -->|No| VectorStage[Vector Similarity Stage]
    VectorStage --> GetJDChunks[Get JD Chunks]
    GetJDChunks --> ChunkLoop[For Each JD Chunk]
    ChunkLoop --> GetEmbedding[Generate JD Chunk Embedding]
    GetEmbedding --> GetWeight["Get JD Chunk Weight<br/>(1, 2, or 3)"]
    GetWeight --> FindSimilar[Find Similar CV Chunks]
    FindSimilar --> CalcScore["Calculate Weighted Score<br/>(similarity² × weight)"]
    CalcScore --> AggregateByCV[Aggregate Scores by CV]
    AggregateByCV --> NormalizeScores[Normalize: total_score / match_count]
    NormalizeScores --> SelectTopN[Select Top N CVs]
    
    %% Skip Vector Stage
    CheckOptimization -->|Yes| SelectAll["Select All CVs<br/>(Skip Vector Stage)"]
    
    %% LLM Reasoning Stage
    SelectTopN --> LLMStage[LLM Reasoning Stage]
    SelectAll --> LLMStage
    LLMStage --> GetFullJD[Get Full JD Text]
    GetFullJD --> CVLoop[For Each Selected CV]
    CVLoop --> GetFullCV[Get Full CV Text]
    GetFullCV --> CompareDocs[Compare JD & CV with LLM]
    CompareDocs --> GenerateResults["Generate Structured Results<br/>(skills, experience, score)"]
    GenerateResults --> AllProcessed{All CVs Processed?}
    AllProcessed -->|No| CVLoop
    AllProcessed -->|Yes| SortResults[Sort by LLM Ranking Score]
    SortResults --> End([End Ranking Process])
   
```

### 5.1 Mathematical Foundation: Why We Square Similarity Scores

The core formula in our vector similarity stage is:
```
weighted_score_contribution = (similarity_score²) × jd_chunk_weight
```

**Why Squaring is Critical:**

1. **Non-Linear Penalty for Weak Matches**
   - Creates a steep penalty curve that dramatically reduces mediocre matches
   - Raw score 0.9 → 0.9² = 0.81 (only 10% reduction)
   - Raw score 0.6 → 0.6² = 0.36 (40% reduction)
   - Raw score 0.3 → 0.3² = 0.09 (70% reduction)

2. **Amplifies "Shiniest Moment" Effect**
   - Since we use `max_weighted_contribution` as the primary ranking metric
   - Rewards specialists with strong domain expertise over generalists with many weak matches
   - Ensures genuine expertise drives rankings, not just keyword frequency

3. **Quality Over Quantity Principle**
   - Prevents CVs from achieving high scores through many moderate matches
   - Only truly confident semantic alignments contribute meaningfully
   - Focuses on core competencies rather than surface-level similarities

4. **Statistical Noise Reduction**
   - Vector similarity scores contain noise from common words and semantic ambiguity
   - Squaring acts as a confidence threshold, filtering out weak correlations
   - Preserves only high-confidence matches for ranking decisions

**Example Impact:**
```
Job Requirement: "Senior Python Developer" (Weight = 3)

CV A (Generalist): Raw similarity = 0.6
- Without squaring: 0.6 × 3 = 1.8
- With squaring: 0.6² × 3 = 1.08

CV B (Python Expert): Raw similarity = 0.9  
- Without squaring: 0.9 × 3 = 2.7
- With squaring: 0.9² × 3 = 2.43

Gap widens from 1.5x to 2.25x, properly highlighting the specialist's advantage.
```

This mathematical approach ensures our ranking system identifies candidates with **strong, relevant expertise** rather than those who simply mention related terms without demonstrable depth.

## 6. Data Model

```mermaid
classDiagram
    class JDOutput {
        +Optional[str] type
        +Optional[str] location
        +List[str] skills
        +Optional[str] experience
    }
    
    class ExperienceDetail {
        +Optional[str] previous_company
        +Optional[str] role
        +Optional[str] duration
        +List[str] points_about_it
    }
    
    class ContactInfo {
        +Optional[str] mobile_number
        +Optional[EmailStr] email
        +List[str] other_links
    }
    
    class PersonalDetails {
        +Optional[str] date_of_birth
        +Optional[str] place
        +List[str] language
        +List[str] additional_points
    }
    
    class CVOutput {
        +Optional[str] candidate_name
        +List[str] skills
        +List[ExperienceDetail] experience
        +Optional[ContactInfo] contact_info
        +Optional[PersonalDetails] personal_details
    }
    
    class DetailedQuestion {
        +str question
        +str category
        +List[str] good_answer_pointers
        +List[str] unsure_answer_pointers
    }
    
    class CandidateQuestionsOutput {
        +List[DetailedQuestion] technical_questions
        +List[DetailedQuestion] general_behavioral_questions
    }
    
    class LLMJdCvComparisonOutput {
        +str cv_id
        +List[str] skills_evaluation
        +List[str] experience_evaluation
        +List[str] additional_points
        +Optional[str] overall_assessment
        +Optional[float] llm_ranking_score
    }
    
    CVOutput *-- ExperienceDetail : contains
    CVOutput *-- ContactInfo : contains
    CVOutput *-- PersonalDetails : contains
    CandidateQuestionsOutput *-- DetailedQuestion : contains
```

## 7. API Flow Diagram

```mermaid
graph LR
    %% Client
    Client[Client/UI]
    
    %% API Endpoints
    HealthCheck[/GET /\]
    UploadJD[/POST /upload-jd\]
    UploadCVs[/POST /upload-cvs\]
    RankCVs[/POST /rank-cvs\]
    GenQuestions[/POST /generate-questions\]
    
    %% Handlers
    ProcessJD[Process JD Handler]
    ProcessCVs[Process CVs Handler]
    RankHandler[Ranking Handler]
    QuestionsHandler[Questions Handler]
    
    %% Client to Endpoints
    Client --> HealthCheck
    Client --> UploadJD
    Client --> UploadCVs
    Client --> RankCVs
    Client --> GenQuestions
    
    %% Endpoints to Handlers
    UploadJD --> ProcessJD
    UploadCVs --> ProcessCVs
    RankCVs --> RankHandler
    GenQuestions --> QuestionsHandler
    
    %% Request/Response Models
    UploadJD -.-> JDUploadResponse[JDUploadResponse]
    UploadCVs -.-> CVUploadResponse[CVUploadResponse]
    RankCVs -.-> RankingRequest[RankingRequest]
    RankCVs -.-> RankingResponse[RankingResponse]
    GenQuestions -.-> QuestionRequest[QuestionGenerationRequest]
    GenQuestions -.-> QuestionResponse[QuestionGenerationResponse]
    
  
```

## 8. Document Chunking Process

```mermaid
graph TB
    Start([Start Chunking]) --> InputDoc["Input Document<br/>(Base64 or Raw Text)"]
    InputDoc --> LoadPrompt[Load Enrichment Prompt]
    LoadPrompt --> CallLLM[Call LLM with Document + Prompt]
    CallLLM --> ParseResponse[Parse LLM Response]
    ParseResponse --> ExtractChunks[Extract Chunks from JSON]
    
    ExtractChunks --> ChunkLoop[Process Each Chunk]
    ChunkLoop --> ValidateOG{Has og_content?}
    ValidateOG -->|Yes| ValidateEnriched{Has enriched_content?}
    ValidateOG -->|No| SkipChunk[Skip Invalid Chunk]
    
    ValidateEnriched -->|Yes| IsJD{Is JD Document?}
    ValidateEnriched -->|No| SkipChunk
    
    IsJD -->|Yes| CheckWeight{Has valid weight?}
    IsJD -->|No| AddToResult[Add to Result Array]
    
    CheckWeight -->|Yes| AddWithWeight[Add with Weight Value]
    CheckWeight -->|No| AddWithDefaultWeight[Add with Default Weight]
    
    AddWithWeight --> ResultComplete{All Chunks Processed?}
    AddWithDefaultWeight --> ResultComplete
    AddToResult --> ResultComplete
    SkipChunk --> ResultComplete
    
    ResultComplete -->|No| ChunkLoop
    ResultComplete -->|Yes| End([Return Chunks])
    
``` 