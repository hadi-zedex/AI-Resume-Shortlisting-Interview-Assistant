from src.models.enums import Tier

# --- System Prompt ---
GENERATE_QUESTIONS_SYSTEM = """
You are an expert technical interviewer and hiring consultant.
Your job is to generate a tailored, actionable interview plan for a specific
candidate based on their resume profile, scoring results, and assigned tier.

Rules:
- Return ONLY valid JSON. No explanation, no markdown fences, no preamble.
- Generate between 5 and 8 questions. No more, no less.
- Questions must be specific to THIS candidate — not generic interview questions.
  Reference their actual experience, companies, technologies, and claims.
- Every question must have a clear rationale explaining why it was chosen
  for this specific candidate.
- Calibrate difficulty to the tier:
    - Tier A → mostly hard questions, some medium. System design, architecture trade-offs.
    - Tier B → mix of medium and hard. Technical depth + ownership verification.
    - Tier C → mix of easy and medium. Foundational concepts + gap probing.
- Dimension coverage — spread questions across these dimensions:
    - technical_depth  → probe actual skill depth beyond keyword listing
    - skill_gap        → probe missing or semantically matched skills
    - ownership        → verify decision-making and leadership claims
    - achievement      → verify quantified claims with specifics
- For skill_gap questions: be specific about what was missing or only
  semantically matched. Do not ask about skills the candidate clearly has.
- For ownership questions: reference specific roles or projects from the resume
  and ask them to walk through their decision-making process.
- For achievement questions: ask them to go deeper on a specific metric they claimed.
  "You mentioned X% improvement — walk me through how you measured that."
- follow_up should be a probing question for when the candidate gives a
  surface-level answer. It should push for depth, not repeat the original question.
- interviewer_briefing must be 2–3 sentences maximum. It should tell the
  interviewer what kind of candidate this is and what to watch for.
- red_flags: things the interviewer should watch out for in answers.
- green_flags: things that would strongly confirm the candidate is a fit.
- Be honest and direct. Do not inflate the assessment to be kind.
""".strip()


# --- Prompt Template ---
def build_generate_questions_prompt(
    candidate_name: str,
    jd_title: str,
    tier: Tier,
    overall_score: float,
    strengths: list[str],
    gaps: list[str],
    focus_areas: list[str],
    experience_summary: str,
    skill_match_summary: str,
    dimension_scores: dict[str, float],
) -> str:
    """
    Build the interview question generation prompt.

    Args:
        candidate_name:     Full name of the candidate.
        jd_title:           Job title they applied for.
        tier:               Assigned tier (A, B, or C).
        overall_score:      Overall weighted score (0–100).
        strengths:          List of identified strengths from ScoringResult.
        gaps:               List of identified gaps from ScoringResult.
        focus_areas:        List of focus areas from TierClassification.
        experience_summary: Formatted string of candidate's experience.
        skill_match_summary: Summary of how skills matched the JD.
        dimension_scores:   Dict of dimension name → score.

    Returns:
        Fully formatted prompt string ready to send to Claude.
    """
    schema = _get_schema_hint()
    tier_guidance = _get_tier_guidance(tier)
    dimension_summary = _format_dimension_scores(dimension_scores)

    return f"""
Generate a tailored interview plan for the following candidate.

CANDIDATE: {candidate_name}
ROLE APPLIED: {jd_title}
TIER: {tier.value} — {tier_guidance}
OVERALL SCORE: {overall_score:.1f}/100

DIMENSION SCORES:
{dimension_summary}

STRENGTHS:
{_format_list(strengths) if strengths else "  None identified."}

GAPS:
{_format_list(gaps) if gaps else "  None identified."}

INTERVIEWER FOCUS AREAS:
{_format_list(focus_areas) if focus_areas else "  None identified."}

CANDIDATE EXPERIENCE SUMMARY:
---
{experience_summary}
---

SKILL MATCH SUMMARY:
---
{skill_match_summary}
---

Generate a complete interview plan following this schema exactly:

{schema}

Return only the JSON object. Nothing else.
""".strip()


# --- Schema hint ---
def _get_schema_hint() -> str:
    return """
{
  "interviewer_briefing": "string (2-3 sentences max)",
  "questions": [
    {
      "question": "string — specific to this candidate",
      "rationale": "string — why this question for this candidate",
      "dimension": "technical_depth | skill_gap | ownership | achievement",
      "difficulty": "easy | medium | hard",
      "follow_up": "string or null"
    }
  ],
  "red_flags": ["string"],
  "green_flags": ["string"],
  "recommended_duration_minutes": "integer (30, 45, or 60)"
}
""".strip()


# --- Helpers ---
def _get_tier_guidance(tier: Tier) -> str:
    """Return a one-line guidance string for the tier."""
    guidance = {
        Tier.A: "Fast-track candidate. Focus on system design and culture fit.",
        Tier.B: "Proceed to technical screen. Verify depth and ownership claims.",
        Tier.C: "Needs evaluation. Probe foundational gaps before investing further.",
    }
    return guidance[tier]


def _format_dimension_scores(dimension_scores: dict[str, float]) -> str:
    """Format dimension scores as a readable list."""
    if not dimension_scores:
        return "  No dimension scores available."

    lines = []
    for dimension, score in dimension_scores.items():
        label = dimension.replace("_", " ").title()
        bar = _score_bar(score)
        lines.append(f"  {label:<25} {score:>5.1f}/100  {bar}")

    return "\n".join(lines)


def _score_bar(score: float) -> str:
    """
    Render a simple ASCII progress bar for a score.
    Makes it visually easy for Claude to see relative strengths.

    e.g. score=75 → "███████░░░"
    """
    filled = int(score / 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty


def _format_list(items: list[str]) -> str:
    """Format a list as a numbered string."""
    if not items:
        return "  (none)"
    return "\n".join(f"  {i+1}. {item}" for i, item in enumerate(items))


# --- Experience formatter ---
def format_experience_for_questions(experience_list: list) -> str:
    """
    Format candidate experience for the question generation prompt.
    More concise than the scorer version — we only need enough context
    for the question generator to reference specific roles and claims.

    Args:
        experience_list: List of Experience Pydantic model instances.

    Returns:
        Formatted multi-line string.
    """
    if not experience_list:
        return "No experience entries found."

    lines = []
    for i, exp in enumerate(experience_list, start=1):
        duration = (
            f"{exp.duration_months} months"
            if exp.duration_months
            else "duration unknown"
        )
        lines.append(f"{i}. {exp.role} at {exp.company} ({duration})")

        if exp.achievements:
            for ach in exp.achievements:
                lines.append(f"   • {ach}")
        else:
            lines.append(f"   • {exp.description[:150]}...")

        lines.append("")

    return "\n".join(lines).strip()


# --- Skill match summary formatter ---
def format_skill_match_summary(skill_matches: list) -> str:
    """
    Format skill match details into a concise summary for the prompt.
    Groups by match type so Claude can see gaps and semantic matches clearly.

    Args:
        skill_matches: List of SkillMatchDetail instances.

    Returns:
        Formatted summary string.
    """
    if not skill_matches:
        return "No skill match details available."

    exact = [m for m in skill_matches if m.match_type.value == "exact"]
    semantic = [m for m in skill_matches if m.match_type.value == "semantic"]
    partial = [m for m in skill_matches if m.match_type.value == "partial"]
    none = [m for m in skill_matches if m.match_type.value == "none"]

    lines = []

    if exact:
        lines.append(f"Exact matches ({len(exact)}):")
        for m in exact:
            lines.append(f"  ✓ {m.jd_skill}")

    if semantic:
        lines.append(f"Semantic matches ({len(semantic)}):")
        for m in semantic:
            lines.append(
                f"  ~ {m.jd_skill} ← {m.candidate_skill}: {m.explanation}"
            )

    if partial:
        lines.append(f"Partial matches ({len(partial)}):")
        for m in partial:
            lines.append(
                f"  ≈ {m.jd_skill} ← {m.candidate_skill}: {m.explanation}"
            )

    if none:
        lines.append(f"Missing skills ({len(none)}):")
        for m in none:
            lines.append(f"  ✗ {m.jd_skill}")

    return "\n".join(lines)