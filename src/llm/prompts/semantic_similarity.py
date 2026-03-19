# --- System Prompt ---
SEMANTIC_SIMILARITY_SYSTEM = """
You are an expert technical recruiter and software engineer.
Your job is to evaluate whether a candidate's skills are functionally
equivalent or similar to the skills required in a job description.

Rules:
- Return ONLY valid JSON. No explanation, no markdown fences, no preamble.
- For each JD skill, find the best matching candidate skill if one exists.
- Assign a match_type from: "exact", "semantic", "partial", "none"
    - exact    → identical or trivially same (e.g. "Python" == "python", "JS" == "JavaScript")
    - semantic → functionally equivalent or interchangeable in most contexts
                 (e.g. "Kafka" ~ "RabbitMQ", "AWS" ~ "GCP", "Postgres" ~ "MySQL")
    - partial  → related but not equivalent, candidate has adjacent knowledge
                 (e.g. "SQL" for "PostgreSQL", "REST APIs" for "GraphQL")
    - none     → no relevant match found in the candidate's skills
- For semantic and partial matches, always provide a clear explanation of
  why the match was made and what the differences are.
- For exact matches, explanation can be brief.
- For none matches, explanation should state what is missing.
- score_0_to_100 per skill:
    - exact   → 90–100
    - semantic → 60–85  (based on how interchangeable they truly are)
    - partial  → 30–55
    - none     → 0
- Consider the domain context when scoring semantic matches.
  "Kafka ↔ RabbitMQ" is stronger in a data pipeline role than a web backend role.
- Be strict. Do not inflate scores to be generous.
""".strip()


# --- Prompt Template ---
def build_semantic_similarity_prompt(
    jd_skills: list[str],
    candidate_skills: list[str],
    domain: str | None = None,
) -> str:
    """
    Build the semantic similarity prompt.

    Args:
        jd_skills:        List of skill names from the JD requirements.
        candidate_skills: List of skill names from the candidate profile.
        domain:           Optional domain context e.g. "FinTech", "Data Engineering".

    Returns:
        Fully formatted prompt string ready to send to Claude.
    """
    domain_context = (
        f"Domain context: {domain}\n"
        if domain
        else "Domain context: Not specified\n"
    )

    schema = _get_schema_hint()

    return f"""
Evaluate how well the candidate's skills match the job requirements.

{domain_context}
JD required skills:
{_format_list(jd_skills)}

Candidate skills:
{_format_list(candidate_skills)}

For each JD skill, find the best match from the candidate's skill list
and return a JSON object following this schema exactly:

{schema}

Return only the JSON object. Nothing else.
""".strip()


# --- Schema hint for Claude ---
def _get_schema_hint() -> str:
    return """
{
  "matches": [
    {
      "jd_skill": "string",
      "candidate_skill": "string or null",
      "match_type": "exact | semantic | partial | none",
      "score_0_to_100": "integer",
      "explanation": "string"
    }
  ],
  "overall_summary": "string"
}
""".strip()


def _format_list(items: list[str]) -> str:
    """Format a list of strings as a numbered list for the prompt."""
    if not items:
        return "  (none provided)"
    return "\n".join(f"  {i+1}. {item}" for i, item in enumerate(items))