from src.models import CandidateProfile

# --- System Prompt ---
EXTRACT_RESUME_SYSTEM = """
You are an expert resume parser. Your job is to extract structured information
from raw resume text and return it as valid JSON.

Rules:
- Return ONLY valid JSON. No explanation, no markdown fences, no preamble.
- If a field is not present in the resume, use null for optional fields or an empty list for arrays.
- Do not hallucinate or infer information that is not explicitly in the resume.
- For duration_months: calculate from the date range if given (e.g. "Jan 2021 – Jun 2022" = 17 months).
  If only years are given (e.g. "2021 – 2022"), estimate as 12 months per year.
  If "Present" is mentioned, calculate up to today.
- For achievements: only include statements with measurable impact
  (numbers, percentages, team sizes, revenue, latency etc.).
- For keywords per experience: extract only technical skills, tools, and technologies
  mentioned in that specific role. Not soft skills.
- For skill level: infer from context.
  "5 years of Python" or "expert in" → advanced.
  "familiar with" or "exposure to" → beginner.
  Default to unknown if unclear.
- For total_experience_years: sum all non-overlapping experience durations.
- For summary: write 2 sentences maximum capturing the candidate's profile.
  Be factual, not promotional.
""".strip()


# --- Prompt Template ---
def build_extract_resume_prompt(raw_text: str) -> str:
    """
    Build the extraction prompt for a given resume's raw text.

    Args:
        raw_text: Plain text extracted from the resume PDF.

    Returns:
        A fully formatted prompt string ready to send to Claude.
    """
    schema = _get_schema_hint()

    return f"""
Extract all information from the resume text below and return a JSON object
that strictly follows this schema:

{schema}

Resume text:
---
{raw_text}
---

Return only the JSON object. Nothing else.
""".strip()


# --- Schema hint for Claude ---
def _get_schema_hint() -> str:
    """
    Returns a JSON schema hint derived from CandidateProfile.
    This shows Claude exactly what structure to return.
    """
    return """
{
  "full_name": "string",
  "email": "string or null",
  "linkedin_url": "string or null",
  "github_url": "string or null",
  "skills": [
    {
      "name": "string",
      "level": "beginner | intermediate | advanced | unknown",
      "years": "float or null"
    }
  ],
  "experience": [
    {
      "company": "string",
      "role": "string",
      "duration_months": "integer or null",
      "description": "string",
      "achievements": ["string"],
      "keywords": ["string"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string or null",
      "field": "string or null",
      "year": "integer or null"
    }
  ],
  "total_experience_years": "float or null",
  "summary": "string or null",
  "raw_text": ""
}
""".strip()