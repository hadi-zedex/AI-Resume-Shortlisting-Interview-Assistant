# --- System Prompt ---
SCORE_OWNERSHIP_SYSTEM = """
You are an expert technical recruiter evaluating the ownership and leadership
signals in a software engineering candidate's resume.

Your job is to assess whether the candidate demonstrates ownership, initiative,
and leadership versus being a passive contributor or executor of others' tasks.

Rules:
- Return ONLY valid JSON. No explanation, no markdown fences, no preamble.
- Evaluate language signals across ALL experience entries.
- Strong ownership signals (high score):
    - Designed or architected systems        ("designed the microservices architecture")
    - Led or managed people or teams         ("led a team of 6 engineers")
    - Drove or owned initiatives end-to-end  ("owned the migration from monolith to microservices")
    - Made technical decisions               ("chose Kafka over RabbitMQ for throughput requirements")
    - Mentored others                        ("mentored 3 junior engineers")
    - Founded or initiated projects          ("initiated the observability platform from scratch")
    - Accountable for outcomes               ("responsible for 99.9% SLA of payment service")
- Weak ownership signals (low score):
    - Passive contributor language           ("assisted", "helped", "supported", "participated in")
    - Pure executor language                 ("implemented", "developed", "coded", "tested")
    - No indication of decision-making       (only describes tasks, not choices)
    - Always part of a team, never leading   ("worked with the team to...")
- Important nuance:
    - "implemented" alone is weak, but "implemented after evaluating 3 alternatives" is strong.
    - Junior roles are expected to have weaker ownership — account for seniority context.
    - A Senior or Lead title with weak language should score lower than expected.
    - A Junior title with strong ownership language should score higher than expected.
- Scoring guide:
    - 85–100 → Consistent ownership across multiple roles, clear decision-making authority
    - 65–84  → Mix of ownership and contribution, led at least one significant initiative
    - 40–64  → Mostly contributor, occasional ownership signals
    - 0–39   → Pure executor language throughout, no evidence of initiative or leadership
- evidence must be direct quotes or close paraphrases from resume text.
  Do not fabricate evidence.
- Be strict. Titles alone (e.g. "Tech Lead") do not guarantee a high score —
  the language must reflect actual ownership behaviour.
""".strip()


# --- Prompt Template ---
def build_score_ownership_prompt(
    experience_text: str,
    candidate_name: str,
    jd_responsibilities: list[str] | None = None,
) -> str:
    """
    Build the ownership scoring prompt.

    Args:
        experience_text:      Formatted string of all experience entries.
        candidate_name:       Name of the candidate for context.
        jd_responsibilities:  Optional list of JD responsibilities to
                              contextualise the expected ownership level.

    Returns:
        Fully formatted prompt string ready to send to Claude.
    """
    schema = _get_schema_hint()
    responsibilities_section = _format_responsibilities(jd_responsibilities)

    return f"""
Evaluate the ownership and leadership signals in {candidate_name}'s work history.

Focus on:
1. Does the candidate use language that signals ownership, initiative, and decision-making?
2. Did they lead people, systems, or projects — or were they always a contributor?
3. Is there evidence of going beyond assigned tasks?

{responsibilities_section}
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
  "ownership_signals": [
    {
      "text": "direct quote or close paraphrase from resume",
      "signal_type": "led_people | architected | drove_initiative | decision_making | mentored | founded | accountable",
      "strength": "strong | moderate | weak"
    }
  ],
  "weak_signals": [
    {
      "text": "direct quote showing passive or executor language",
      "suggestion": "string — how this could have been worded to show more ownership"
    }
  ],
  "seniority_context": "string — how seniority level affected the score",
  "missing": "string describing what ownership behaviours are absent",
  "explanation": "string summarising why this score was given"
}
""".strip()


# --- Helpers ---
def _format_responsibilities(responsibilities: list[str] | None) -> str:
    """
    Format JD responsibilities section for the prompt.
    Gives Claude context about what level of ownership this role expects.
    """
    if not responsibilities:
        return ""

    lines = ["JD expected responsibilities (for context):"]
    for i, resp in enumerate(responsibilities, start=1):
        lines.append(f"  {i}. {resp}")
    lines.append("")                                # Blank line before work history

    return "\n".join(lines)


def format_experience_for_prompt(experience_list: list) -> str:
    """
    Format a list of Experience objects into a readable string
    for the ownership scoring prompt.

    Reuses the same formatting logic as the achievement prompt
    but is kept here to keep each prompt module self-contained.

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
