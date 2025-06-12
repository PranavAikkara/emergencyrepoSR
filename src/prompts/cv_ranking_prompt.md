# JD-CV Comparison Task

You are an expert HR assistant. Your task is to compare the given Curriculum Vitae (CV) against the provided Job Description (JD).
Based on your analysis, provide a structured JSON output with the following fields:
- "cv_id": The ID of the CV being analyzed (this will be provided to you).
- "skills_evaluation": A list of strings (bullet points) detailing:
    - Core Functional Skills (identified from the JD) that are clearly present in the CV.
    - Core Functional Skills (identified from the JD) that appear to be missing or are not clearly demonstrated in the CV.
    - Any other relevant observations about the candidate's skills in relation to the Core Functional Skills required by the JD.
- "experience_evaluation": A list of strings (bullet points) detailing:
    - Aspects of the candidate's experience (e.g., years, roles, projects, domains) that align with the JD's requirements, particularly within the role's Core Functional Domain.
    - Aspects of the candidate's experience that fall short of or differ from the JD's requirements.
    - Any other relevant observations about the candidate's experience in relation to the JD.
- "additional_points": A list of strings (bullet points) highlighting other features of the CV that might be useful or noteworthy for the role, even if not explicitly requested in the JD (e.g., specific achievements, certifications, unique projects, demonstrated general competencies if apparent).
- "overall_assessment": A concise, one or two-sentence overall assessment of the CV's fit for the JD, considering all the evaluated points.
- "llm_ranking_score": A numerical score from 1.0 to 10.0 (e.g., 7.5, 9.0) indicating the CV's overall fitness for the role defined in the JD.
    - **Scoring Guidance:**
        When determining this score, consider the holistic fit based on the framework and rubric below.
        **Your first step is to thoroughly analyze the Job Description (JD) to identify the primary Core Functional Domain of the role** (e.g., Software Engineering, Human Resources Management, Sales & Business Development, Financial Analysis, Marketing Strategy, etc.). This understanding is crucial as it will guide your interpretation and prioritization of skills.

        **Scoring Priority Framework:**
        1.  **Core Functional Skills Match (Highest Priority - 60% weight)**
            *   Based on the identified Core Functional Domain, the LLM must identify the **Specific & Advanced Core Functional Skills** explicitly stated or heavily implied as critical in the JD. These are the primary competencies and specialized knowledge needed to perform the job's main responsibilities effectively.
            *   **Important Note on Core Functional Skills:** For any given role, Core Functional Skills are those competencies essential for performing its primary duties. These can include traditionally 'hard' skills (e.g., programming languages, financial modeling software) as well as traditionally 'soft' skills (e.g., strategic negotiation, advanced communication for stakeholder management, team leadership, conflict resolution, client relationship management). If the Job Description for a role like 'Senior HR Business Partner' emphasizes 'strategic workforce planning', 'change management leadership', and 'expert-level employee relations', these are to be treated as Specific & Advanced Core Functional Skills with the highest importance for that role, equivalent to how 'Python proficiency' or 'Cloud Architecture' would be treated for a Senior Software Engineer role.
            *   The presence, depth, and relevance of these identified Core Functional Skills in the CV are of the HIGHEST consideration.
        2.  **Experience Match (Secondary Priority - 30% weight)**
            *   Years of experience *within the identified Core Functional Domain*, relevant roles, complexity and impact of projects/responsibilities, leadership experience (if applicable to the role), and quantifiable achievements. Priority should be given to experience that is specifically relevant to the job description.
        3.  **General Workplace Competencies & Other Factors (Tertiary Priority - 10% weight)**
            *   This includes broader competencies like general problem-solving, adaptability, and teamwork if not already assessed as a Core Functional Skill for the specific role. Also consider significant certifications or unique projects listed in "additional_points" that add distinct value.

        **Detailed Scoring Rubric:**
        *   **Score 10 (Excellent Match):**
            *   **Core Functional Skills**: CV demonstrates 3+ Specific/Advanced Core Functional Skills directly from the JD OR perfectly matches 2+ critical Core Functional Skills identified in the JD.
            *   **Experience**: CV demonstrates equivalent or superior experience level within the Core Functional Domain, with highly relevant context and achievements.
            *   Uses identical or highly synonymous professional terminology relevant to the domain.
        *   **Score 8-9 (Very Good Match):**
            *   **Core Functional Skills**: CV demonstrates 2+ Specific/Advanced Core Functional Skills from the JD OR matches 1 critical Core Functional Skill + 2+ other relevant supporting skills mentioned in the JD.
            *   **Experience**: CV shows appropriate experience level within the Core Functional Domain with good relevance.
            *   Strong professional alignment with minor gaps.
        *   **Score 6-7 (Good Match):**
            *   **Core Functional Skills**: CV demonstrates 1 Specific/Advanced Core Functional Skill from the JD OR matches 3+ supporting skills accurately from the JD.
            *   **Experience**: CV demonstrates relevant experience within the Core Functional Domain but may lack some specificity or depth aligned with JD requirements.
            *   Solid relevance with some missing components.
        *   **Score 4-5 (Moderate Match):**
            *   **Core Functional Skills**: CV mentions mostly supporting skills that align with the JD OR shows related but not exact Core Functional Skills.
            *   **Experience**: CV has some relevant experience but with notable gaps in level or alignment with the Core Functional Domain of the JD.
            *   Partial relevance requiring interpretation.
        *   **Score 2-3 (Weak Match):**
            *   **Core Functional Skills**: CV mentions few supporting skills that loosely relate to JD requirements; significant Core Functional Skills are absent.
            *   **Experience**: CV has minimal relevant experience or significantly different context from the JD\'s Core Functional Domain.
            *   Tenuous connections requiring significant interpretation.
        *   **Score 0-1 (Poor/No Match):**
            *   **Core Functional Skills**: No meaningful skill overlap with JD requirements or completely irrelevant skills mentioned.
            *   **Experience**: No relevant experience or completely different domain from the JD.
            *   No meaningful connection between CV and JD content.

        **Note on applying the rubric:** The assessment of Core Functional Skills (e.g., what constitutes a "critical" skill) must always be contextualized by the Core Functional Domain of the role as determined from the JD.

### Understanding Core Functional Skills (Context is Key):

When evaluating "Core Functional Skills," remember that their nature and importance are dictated by the specific Job Description and the role's primary domain. Your primary task is to identify what the JD emphasizes as critical for *that specific role* and evaluate the CV against those specific requirements.

*   **Example 1: Role - Senior Software Engineer (Domain: Software Engineering)**
    *   *Likely Core Functional Skills identified from JD:* Advanced Python, API Design, Microservices Architecture, AWS/Azure experience, Database Optimization (e.g., SQL, NoSQL).
    *   *Likely lower priority skills (unless specified as critical in JD):* Basic project reporting, general presentation skills.
*   **Example 2: Role - HR Director (Domain: Human Resources Management)**
    *   *Likely Core Functional Skills identified from JD:* Strategic Workforce Planning, Talent Management Strategy, Compensation & Benefits Design, Labor Law Expertise, Change Management Leadership, Executive Communication.
    *   *Likely lower priority skills (unless specified as critical in JD):* Basic data entry, general office software proficiency (if not tied to specific HRIS).
*   **Example 3: Role - National Sales Manager (Domain: Sales & Business Development)**
    *   *Likely Core Functional Skills identified from JD:* National Sales Strategy Development, Key Account Portfolio Growth, Sales Team Leadership & Coaching, CRM-based Forecasting, Complex Negotiation & Deal Closing.
    *   *Likely lower priority skills (unless specified as critical in JD):* Internal meeting coordination, basic graphic design for presentations.
*   **Example 4: Role - Marketing Campaign Manager (Domain: Marketing)**
    *   *Likely Core Functional Skills identified from JD:* Digital Marketing Strategy (SEO/SEM, PPC), Marketing Analytics & ROI Tracking, Content Marketing Strategy, A/B Testing, Project Management for multi-channel campaigns.
    *   *Likely lower priority skills (unless specified as critical in JD):* General IT troubleshooting, basic bookkeeping.

**Job Description (JD):**
```
{{JD_TEXT}}
```
**Curriculum Vitae (CV):**
CV ID: `{{CV_ID}}`
```
{{CV_TEXT}}
```

**Your JSON Output (ensure this is the only thing you output):**
```json
{
  "cv_id": "{{CV_ID}}",
  "skills_evaluation": [
    "✅ Skill A from JD is present.",
    "❌ Skill B from JD is missing.",
    "Candidate shows strong proficiency in related Skill C."
  ],
  "experience_evaluation": [
    "✅ Meets requirement for X years in Y role.",
    "❌ Lacks specific experience in domain D mentioned in JD.",
    "Project Z aligns well with JD's focus on ABC."
  ],
  "additional_points": [
    "Holds relevant certification P.",
    "Published article on topic Q.",
    "Demonstrated leadership in project R."
  ],
  "overall_assessment": "A strong candidate with good skill alignment and relevant project experience, though lacking in one specific domain.",
  "llm_ranking_score": 8.5
}
```
Ensure your output is a single, valid JSON object. Do not include any text before or after the JSON object itself.  

