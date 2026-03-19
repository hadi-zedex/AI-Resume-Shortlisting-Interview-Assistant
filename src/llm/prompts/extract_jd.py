from src.models import JobDescription

# --- System Prompt ---
EXTRACT_JD_SYSTEM = """
You are an expert job description parser. Your job is to extract structured
information from raw job description text and return it as valid JSON.

Rules:
- Return ONLY valid JSON. No explanation, no markdown fences, no preamble.
- If a field is not present, use null for optional fields or empty list for arrays.
- Do not hallucinate or infer requirements not explicitly stated in the JD.
- For required_skills vs preferred_skills:
    - required_skills: skills listed under "Required", "Must have", "You must",
      or stated as non-negotiable in the text.
    - preferred_skills: skills listed under "Preferred", "Nice to have",
      "Bonus", "Advantageous", or "Plus".
    - If no clear separation exists, treat all technical skills as required.
- For is_mandatory:
    - true  → required skills
    - false → preferred skills
- For minimum_level: infer from context.
    "Senior", "5+ years", "expert" → advanced.
    "Mid-level", "3+ years"        → intermediate.
    "Junior", "1+ years", "basic"  → beginner.
    Default to unknown if unclear.
- For minimum_years: extract only if explicitly stated (e.g. "3+ years of Python").
  Do not infer from seniority level alone.
- For responsibilities: extract the actual job duties as a clean list.
  Keep each item concise — one action per item.
- For domain: infer the industry/domain from context.
  Examples: "FinTech", "HealthTech", "E-commerce", "Data Engineering", "DevOps".
  Use null if unclear.
- For min_experience_years: extract only if explicitly stated overall
  (e.g. "5+ years of experience"). Do not sum up skill-level years.
""".strip()


# --- Prompt Template ---
def build_extract_jd_prompt(raw_text: str) -> str:
    """
    Build the extraction prompt for a given job description's raw text.

    Args:
        raw_text: Plain text of the job description.

    Returns:
        A fully formatted prompt string ready to send to Claude.
    """
    schema = _get_schema_hint()

    return f"""
Extract all information from the job description below and return a JSON object
that strictly follows this schema:

{schema}

Job description text:
---
{raw_text}
---

Return only the JSON object. Nothing else.
""".strip()


# --- Schema hint for Claude ---
def _get_schema_hint() -> str:
    """
    Returns a JSON schema hint derived from JobDescription.
    This shows Claude exactly what structure to return.
    """
    return """
{
  "title": "string",
  "company": "string or null",
  "required_skills": [
    {
      "name": "string",
      "is_mandatory": true,
      "minimum_level": "beginner | intermediate | advanced | unknown",
      "minimum_years": "float or null"
    }
  ],
  "preferred_skills": [
    {
      "name": "string",
      "is_mandatory": false,
      "minimum_level": "beginner | intermediate | advanced | unknown",
      "minimum_years": "float or null"
    }
  ],
  "min_experience_years": "float or null",
  "responsibilities": ["string"],
  "domain": "string or null",
  "raw_text": ""
}
""".strip()