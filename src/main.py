from dataclasses import dataclass
from src.models import (
    CandidateProfile,
    JobDescription,
    ScoringResult,
    TierClassification,
    InterviewPlan,
)
from src.parser.resume_extractor import resume_extractor
from src.parser.jd_extractor import jd_extractor
from src.scorer.engine import scoring_engine
from src.classifier.classifier import tier_classifier
from src.questions.generator import question_generator
from src.config import config


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


def run_pipeline(
    pdf_bytes: bytes,
    jd_text: str,
) -> PipelineResult:
    """
    Run the full resume screening pipeline.

    Stages:
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
        ValueError:       If PDF has no extractable text or JD is empty.
        RuntimeError:     If LLM calls fail after all retries.
        EnvironmentError: If ANTHROPIC_API_KEY is not set.
    """
    # Validate config at entry point
    config.validate()

    # --- Stage 1: Parse resume ---
    print("\n[Pipeline] Stage 1/5 — Parsing resume...")
    candidate = resume_extractor.extract_from_bytes(pdf_bytes)
    print(f"[Pipeline] Parsed candidate: {candidate.full_name}")

    # --- Stage 2: Parse job description ---
    print("[Pipeline] Stage 2/5 — Parsing job description...")
    jd = jd_extractor.extract(jd_text)
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