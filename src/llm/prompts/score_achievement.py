# --- System Prompt ---
SCORE_ACHIEVEMENT_SYSTEM = """
You are an expert technical recruiter evaluating the impact and achievements
of a software engineering candidate based on their resume.

Your job is to assess how well the candidate demonstrates measurable,
quantified achievements and concrete impact in their work history.

Rules:
- Return ONLY valid JSON. No explanation, no markdown fences, no preamble.
- Look for achievement signals across ALL experience entries.
- Strong achievement signals (high score):
    - Quantified impact with numbers    ("reduced latency by 40%")
    - Revenue or cost impact            ("saved $200K annually")
    - Scale indicators                  ("served 10M users", "processed 1B events/day")
    - Team or project size              ("led team of 8", "delivered $2M project")
    - Comparative improvement           ("improved throughput by 3x")
    - Awards, recognitions, promotions  ("promoted within 12 months")
- Weak achievement signals (low score):
    - Vague responsibility statements   ("responsible for backend services")
    - Generic task descriptions         ("worked on microservices")
    - Skill mentions without outcomes   ("used Python and Django")
    - Soft outcomes without numbers     ("improved performance significantly")
- Scoring guide:
    - 85–100 → Multiple strong quantified achievements across roles
    - 65–84  → Some quantified achievements, mix of strong and weak signals
    - 40–64  → Mostly vague, one or two weak quantified signals
    - 0–39   → No quantified achievements, pure responsibility statements
- evidence must be direct quotes or close paraphrases from the resume text.
  Do not fabricate evidence.
- Be strict. A resume with only generic statements scores below 40.
""".strip()


# --- Prompt Template ---
def build_score_achievement_prompt(
    experience_text: str,
    candidate_name: str,
) -> str:
    """
    Build the achievement scoring prompt.

    Args:
        experience_text: Formatted string of all experience entries
                         including descriptions and achievements.
        candidate_name:  Name of the candidate for context.

    Returns:
        Fully formatted prompt string ready to send to Claude.
    """
    schema = _get_schema_hint()

    return f"""
Evaluate the achievement quality of {candidate_name}'s work history below.

Focus on:
1. Are achievements quantified with numbers, percentages, or scale?
2. Is there evidence of real business or technical impact?
3. Do the achievements go beyond listing responsibilities?

Work history:
---
{experience_text}
---

Return a JSON object following this schema exactly:

{schema}

Return only the JSON object. Nothing else.
""".strip()


# --- Schema hint for Claude ---
def _get_schema_hint() -> str:
    return """
{
  "score_0_to_100": "integer",
  "achievement_signals": [
    {
      "text": "direct quote or close paraphrase from resume",
      "signal_type": "quantified_impact | scale | cost_saving | team_size | improvement | recognition",
      "strength": "strong | moderate | weak"
    }
  ],
  "missing": "string describing what kind of achievements are absent",
  "explanation": "string summarising why this score was given"
}
""".strip()


# --- Helper ---
def format_experience_for_prompt(experience_list: list) -> str:
    """
    Format a list of Experience objects into a readable string
    for the achievement scoring prompt.

    Args:
        experience_list: List of Experience Pydantic model instances.

    Returns:
        Formatted multi-line string of all experience entries.
    """
    if not experience_list:
        return "No experience entries found."

    lines = []
    for i, exp in enumerate(experience_list, start=1):
        lines.append(f"Role {i}: {exp.role} at {exp.company}")

        if exp.duration_months:
            lines.append(f"Duration: {exp.duration_months} months")

        lines.append(f"Description: {exp.description}")

        if exp.achievements:
            lines.append("Achievements:")
            for ach in exp.achievements:
                lines.append(f"  - {ach}")
        else:
            lines.append("Achievements: None listed")

        lines.append("")                            # Blank line between roles

    return "\n".join(lines).strip()