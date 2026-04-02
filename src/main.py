import sys
from dataclasses import dataclass
from pathlib import Path

# Ensure src/ is importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import (
    CandidateProfile,
    JobDescription,
    ScoringResult,
    TierClassification,
    InterviewPlan,
)
from src.parser.resume_extractor import resume_extractor
from src.parser.jd_extractor import jd_extractor
from src.parser.validators import pipeline_input_validator
from src.scorer.engine import scoring_engine
from src.classifier.classifier import tier_classifier
from src.questions.generator import question_generator
from src.config import config


# ------------------------------------------------------------------
# Pipeline result container
# ------------------------------------------------------------------

@dataclass
class PipelineResult:
    """
    The complete output of the resume screening pipeline.
    Carries every intermediate result so the UI can
    display each stage independently.
    """
    candidate:      CandidateProfile
    jd:             JobDescription
    scoring:        ScoringResult
    classification: TierClassification
    interview_plan: InterviewPlan


# ------------------------------------------------------------------
# Main pipeline function
# ------------------------------------------------------------------

def run_pipeline(
    pdf_bytes: bytes,
    jd_text: str,
) -> PipelineResult:
    """
    Run the full resume screening pipeline.

    Stages:
        0. Validate all inputs
        1. Parse resume PDF → CandidateProfile
        2. Parse job description → JobDescription
        3. Score candidate across 4 dimensions → ScoringResult
        4. Classify into tier → TierClassification
        5. Generate interview plan → InterviewPlan

    Args:
        pdf_bytes: Raw bytes of the uploaded resume PDF.
        jd_text:   Plain text of the job description.

    Returns:
        PipelineResult containing all intermediate and final outputs.

    Raises:
        ValueError:          If PDF has no extractable text,
                             JD is empty, or inputs are invalid.
        RuntimeError:        If LLM calls fail after all retries.
        EnvironmentError:    If ANTHROPIC_API_KEY is not set.
        FileNotFoundError:   If PDF path does not exist (path mode).
    """
    # --- Stage 0: Validate config and inputs ---
    print("\n[Pipeline] Stage 0/5 — Validating inputs...")
    config.validate()

    cleaned_jd = pipeline_input_validator.validate_bytes_input(
        pdf_bytes=pdf_bytes,
        jd_text=jd_text,
    )
    print("[Pipeline] Inputs valid.")

    # --- Stage 1: Parse resume ---
    print("[Pipeline] Stage 1/5 — Parsing resume...")
    candidate = resume_extractor.extract_from_bytes(pdf_bytes)
    print(f"[Pipeline] Parsed candidate: {candidate.full_name}")

    # --- Stage 2: Parse job description ---
    print("[Pipeline] Stage 2/5 — Parsing job description...")
    jd = jd_extractor.extract(cleaned_jd)
    print(f"[Pipeline] Parsed JD: {jd.title}")

    # --- Stage 3: Score ---
    print("[Pipeline] Stage 3/5 — Scoring candidate...")
    scoring = scoring_engine.run(candidate, jd)
    print(f"[Pipeline] Overall score: {scoring.overall_score:.1f}/100")

    # --- Stage 4: Classify ---
    print("[Pipeline] Stage 4/5 — Classifying tier...")
    classification = tier_classifier.classify(scoring)
    print(f"[Pipeline] Tier: {classification.tier.value}")

    # --- Stage 5: Generate interview plan ---
    print("[Pipeline] Stage 5/5 — Generating interview plan...")
    interview_plan = question_generator.generate(classification, candidate)
    print(f"[Pipeline] Generated {len(interview_plan.questions)} questions.")

    print("\n[Pipeline] Complete.\n")

    return PipelineResult(
        candidate=candidate,
        jd=jd,
        scoring=scoring,
        classification=classification,
        interview_plan=interview_plan,
    )


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def run_pipeline_from_path(
    pdf_path: str | Path,
    jd_text: str,
) -> PipelineResult:
    """
    Run the full pipeline from a PDF file path.
    Used for CLI usage and testing.

    Args:
        pdf_path: Path to the resume PDF file.
        jd_text:  Plain text of the job description.

    Returns:
        PipelineResult containing all outputs.
    """
    # Validate inputs
    config.validate()

    validated_path, cleaned_jd = pipeline_input_validator.validate_path_input(
        pdf_path=pdf_path,
        jd_text=jd_text,
    )

    # Read bytes from path then run standard pipeline
    with open(validated_path, "rb") as f:
        pdf_bytes = f.read()

    return run_pipeline(
        pdf_bytes=pdf_bytes,
        jd_text=cleaned_jd,
    )


def _print_result(result: PipelineResult) -> None:
    """
    Print a formatted summary of the pipeline result to stdout.
    Used by the CLI entry point.
    """
    c = result.classification
    s = result.scoring
    p = result.interview_plan

    print("\n" + "━" * 50)
    print(f"  CANDIDATE:   {result.candidate.full_name}")
    print(f"  ROLE:        {result.jd.title}")
    print(f"  TIER:        {c.tier.value} — {c.decision_label}")
    print(f"  SCORE:       {c.overall_score:.1f} / 100")
    print("━" * 50)

    print("\n📊  DIMENSION SCORES")
    print(f"  Exact Match:         {s.exact_match.score:.1f}")
    print(f"  Semantic Similarity: {s.semantic_similarity.score:.1f}")
    print(f"  Achievement:         {s.achievement.score:.1f}")
    print(f"  Ownership:           {s.ownership.score:.1f}")

    print("\n💬  REASONING")
    print(f"  {c.reasoning}")

    if result.scoring.strengths:
        print("\n✦  STRENGTHS")
        for strength in result.scoring.strengths:
            print(f"  • {strength}")

    if result.scoring.gaps:
        print("\n⚠  GAPS")
        for gap in result.scoring.gaps:
            print(f"  • {gap}")

    print("\n🎯  FOCUS AREAS")
    for i, area in enumerate(c.focus_areas, start=1):
        print(f"  {i:02d}. {area}")

    print(f"\n📋  INTERVIEW PLAN  ({len(p.questions)} questions)")
    print(f"  Duration: {p.recommended_duration_minutes} minutes")
    print(f"\n  Briefing: {p.interviewer_briefing}\n")

    for i, q in enumerate(p.questions, start=1):
        print(f"  Q{i:02d} [{q.difficulty.upper()}] [{q.dimension}]")
        print(f"      {q.question}")
        print(f"      Why: {q.rationale}")
        if q.follow_up:
            print(f"      Follow-up: {q.follow_up}")
        print()

    if p.red_flags:
        print("🚩  RED FLAGS")
        for flag in p.red_flags:
            print(f"  • {flag}")

    if p.green_flags:
        print("✅  GREEN FLAGS")
        for flag in p.green_flags:
            print(f"  • {flag}")

    print("\n" + "━" * 50 + "\n")


# ------------------------------------------------------------------
# CLI runner
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Resume Shortlister — AI-powered candidate screening"
    )
    parser.add_argument(
        "--resume",
        required=True,
        help="Path to the resume PDF file",
    )
    parser.add_argument(
        "--jd",
        required=True,
        help="Path to the job description text file",
    )
    args = parser.parse_args()

    # Read JD from file
    jd_path = Path(args.jd)
    if not jd_path.exists():
        print(f"Error: JD file not found: {jd_path}")
        sys.exit(1)

    jd_text = jd_path.read_text(encoding="utf-8")

    try:
        result = run_pipeline_from_path(
            pdf_path=args.resume,
            jd_text=jd_text,
        )
        _print_result(result)

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    except ValueError as e:
        print(f"\nValidation error: {e}")
        sys.exit(1)

    except EnvironmentError as e:
        print(f"\nConfiguration error: {e}")
        sys.exit(1)

    except RuntimeError as e:
        print(f"\nPipeline error: {e}")
        sys.exit(1)