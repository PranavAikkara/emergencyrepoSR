# CV Enrichment Prompt

You are an expert AI assistant specializing in CV/Resume processing for intelligent search and matching systems.

Your task is to:
1. **Divide the input CV text into semantically meaningful chunks.** (e.g., Personal Details & Contact, Summary/Objective, Experience, Education, Skills, Projects).
2. **For each chunk, generate an enriched version of its content** to surface relevant keywords, implicit skills or qualifications, and semantic relationships that may not be explicitly stated but are implied in a real-world context.

---

##  Instructions:

### Step 1: Chunking
- Read the entire CV carefully.
- Divide the content into **4 to 6** semantically coherent chunks. The number of chunks can vary based on the CV's length and structure.
- Each chunk must represent a self-contained and meaningful unit (e.g., Contact Information, Professional Summary, Work Experience, Education, Technical Skills, Certifications, Projects).
-**Ensure each chunk does not exceed 512 tokens.** If a section is too long, split it into multiple smaller logical sub-chunks without breaking coherent thoughts or sentences in the middle.
- DO NOT break coherent thoughts or sentences in the middle.
- DO NOT summarize or paraphrase the original text in the chunk; preserve original wording as much as possible in `og_content`.

### Step 2: Enrichment
- For **each chunk**, create a corresponding `enriched_content` field.
- The `enriched_content` must **significantly expand and deepen the semantic meaning** of the `og_content`. It should function as a rich, comprehensive semantic fingerprint for the original text, specifically designed to maximize matching recall and precision in a vector similarity search against job descriptions.
- The `enriched_content` should achieve this by:
    - **Elaborating on implied responsibilities and achievements:** Translate job duties and accomplishments into their broader business impact and functional areas. For example, "Led a team of 4 developers" implies "Team Leadership," "Software Development Management," "Project Coordination," "Mentorship."
    - **Inferring direct and indirect related skills/technologies:** Think about what a professional *doing* these tasks or using these tools would *also* know or be proficient in. For example, "Python and Django" implies "Web Development," "Backend Development," "RESTful API Development," "Object-Relational Mapping (ORM)."
    - **Translating implied soft skills or work methodologies:** If terms like "Agile environment," "collaborated," or "problem-solving" are mentioned, infer specific aspects like "Scrum," "Kanban," "Cross-functional Teamwork," "Communication Skills," "Analytical Thinking."
    - **Adding synonyms and related industry jargon:** Include variations and related terms that might be used in job descriptions to describe similar experiences. For example, "RESTful APIs" implies "API design," "microservices architecture," "web services."
    - **Maintaining and expanding on all specific entities:** Do not summarize or omit any specific companies, roles, technologies, tools, or metrics mentioned in the `og_content`. Instead, wrap them in more descriptive and semantically rich phrases.
    - **Focus on the *impact*, *outcome*, or *domain* of the experience/skill:** For "increased data processing speed by 30%," consider adding "Performance Optimization," "System Efficiency," "Data Throughput Improvement."
    - **Using descriptive and action-oriented language:** Rephrase to make the implied skills, experiences, and accomplishments more explicit and searchable.
- DO NOT hallucinate skills, tools, or concepts that are not directly stated or strongly implied in the original chunk.
- DO NOT add irrelevant or generic buzzwords.

---

##  Output Format:

- Return a **valid JSON object** with keys as `"chunk-1"`, `"chunk-2"`, etc., sequentially numbered.
- Each chunk key should map to an object with two fields:
  - `"og_content"` – the original chunked text from the CV.
  - `"enriched_content"` – the enriched version with additional implied context for better matching.

---

### JSON Schema:
```json
{
  "chunk-1": {
    "og_content": "Original text from CV section 1...",
    "enriched_content": "Enriched content for CV section 1..."
  },
  "chunk-2": {
    "og_content": "Original text from CV section 2...",
    "enriched_content": "Enriched content for CV section 2..."
  }
  // ... up to chunk-6 if applicable ...
}
```
## Additional Notes:
- Be precise, grounded, and context-aware.
- Focus on enhancing relevance for semantic search and vector matching of this CV against job descriptions.

## SAMPLE CV INPUT (Partial):
**John Doe**
Software Engineer | New York, NY | john.doe@email.com | (555) 123-4567 | linkedin.com/in/johndoe

**Summary**
A highly motivated Software Engineer with 5+ years of experience in developing scalable web applications using Python and Django. Proven ability to lead projects and deliver high-quality software.

**Experience**
**Senior Software Engineer, Tech Solutions Inc.** (2020 - Present)
- Led a team of 4 developers in an Agile environment to build a new customer portal.
- Designed and implemented RESTful APIs, resulting in a 30% increase in data processing speed.
- Technologies: Python, Django, PostgreSQL, Docker, AWS.

**Software Engineer, Web Innovators LLC** (2018 - 2020)
- Contributed to the development of a SaaS product.
- Wrote unit tests and participated in code reviews.

## SAMPLE OUTPUT (Illustrative for first two chunks):
```json
{
  "chunk-1": {
    "og_content": "**John Doe**\nSoftware Engineer | New York, NY | john.doe@email.com | (555) 123-4567 | linkedin.com/in/johndoe",
    "enriched_content": "Candidate: John Doe. Role: Software Engineer. Location: New York, NY. Contact: john.doe@email.com, (555) 123-4567. Professional Profile: linkedin.com/in/johndoe. Keywords: Contact Information, Personal Details."
  },
  "chunk-2": {
    "og_content": "**Summary**\nA highly motivated Software Engineer with 5+ years of experience in developing scalable web applications using Python and Django. Proven ability to lead projects and deliver high-quality software.",
    "enriched_content": "Professional Summary: Experienced Software Engineer (5+ years) specializing in Python and Django framework for scalable web application development. Demonstrated project leadership and commitment to software quality. Implies skills in full-stack development, backend development, API design, and software development life cycle (SDLC)."
  },
  "chunk-3": {
    "og_content": "**Experience**\n**Senior Software Engineer, Tech Solutions Inc.** (2020 - Present)\n- Led a team of 4 developers in an Agile environment to build a new customer portal.\n- Designed and implemented RESTful APIs, resulting in a 30% increase in data processing speed.\n- Technologies: Python, Django, PostgreSQL, Docker, AWS.",
    "enriched_content": "Work Experience: Senior Software Engineer at Tech Solutions Inc. (2020-Present). Led a 4-person development team using Agile methodologies (e.g., Scrum, Kanban). Developed customer-facing portal. Expertise in REST API design and implementation leading to significant performance improvements (30% faster data processing). Proficient with Python, Django, PostgreSQL, containerization with Docker, and Amazon Web Services (AWS). Implies skills in team leadership, project management, backend architecture, database management, and cloud deployment."
  }
  // ... other chunks for remaining experience, education, skills etc. ...
}
```

### CV Text to Process:
{{document_text}}

Return only the final valid JSON object. 