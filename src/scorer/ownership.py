from src.models import CandidateProfile, JobDescription, DimensionScore
from src.models.enums import ScoreDimension
from src.llm.client import llm_client
from src.llm.prompts.score_ownership import (
    SCORE_OWNERSHIP_SYSTEM,
    build_score_ownership_prompt,
    format_experience_for_prompt,
)


class OwnershipScorer:
    """
    Scores the candidate based on ownership, initiative, and leadership
    signals detected in their work history language.

    Uses Claude to distinguish between candidates who led/owned things
    versus those who assisted/contributed to others' work.

    Unlike AchievementScorer, this scorer is JD-aware — ownership
    expectations are calibrated against the role's responsibilities.
    """

    def score(
        self,
        candidate: CandidateProfile,
        jd: JobDescription,
    ) -> DimensionScore:
        """
        Compute the ownership score for a candidate.

        Args:
            candidate: Parsed candidate profile.
            jd:        Parsed job description (for seniority context).

        Returns:
            DimensionScore with score + explanation + evidence.
        """
        # Guard: no experience to evaluate
        if not candidate.experience:
            return self._zero_score(
                "No work experience found in the candidate profile."
            )

        experience_text = format_experience_for_prompt(candidate.experience)

        prompt = build_score_ownership_prompt(
            experience_text=experience_text,
            candidate_name=candidate.full_name,
            jd_responsibilities=jd.responsibilities,
        )

        raw_json = llm_client.complete_json(
            prompt=prompt,
            system=SCORE_OWNERSHIP_SYSTEM,
        )

        return self._parse_response(raw_json, candidate.full_name)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        raw_json: dict,
        candidate_name: str,
    ) -> DimensionScore:
        """
        Parse Claude's ownership scoring response into a DimensionScore.

        Args:
            raw_json:       Parsed dict from Claude's JSON response.
            candidate_name: Used for fallback explanation context.

        Returns:
            Validated DimensionScore instance.
        """
        try:
            score = self._extract_score(raw_json)
            explanation = self._build_explanation(raw_json)
            evidence = self._build_evidence(raw_json)

            return DimensionScore(
                dimension=ScoreDimension.OWNERSHIP,
                score=round(score, 2),
                explanation=explanation,
                evidence=evidence,
            )

        except Exception as e:
            raise ValueError(
                f"[OwnershipScorer] Failed to parse Claude response "
                f"for '{candidate_name}'.\nError: {e}\n"
                f"Raw JSON keys: {list(raw_json.keys())}"
            ) from e

    @staticmethod
    def _extract_score(raw_json: dict) -> float:
        """
        Safely extract and clamp the score from Claude's response.

        Args:
            raw_json: Parsed dict from Claude.

        Returns:
            Float score clamped between 0.0 and 100.0.
        """
        raw_score = raw_json.get("score_0_to_100", 0)

        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0

        return min(100.0, max(0.0, score))

    @staticmethod
    def _build_explanation(raw_json: dict) -> str:
        """
        Build a complete explanation string from Claude's response.
        Combines explanation, seniority context, and missing signals.

        Args:
            raw_json: Parsed dict from Claude.

        Returns:
            Human-readable explanation string.
        """
        explanation = raw_json.get("explanation", "").strip()
        seniority_context = raw_json.get("seniority_context", "").strip()
        missing = raw_json.get("missing", "").strip()

        parts = []

        if explanation:
            parts.append(explanation)

        if seniority_context:
            parts.append(f"Seniority context: {seniority_context}")

        if missing:
            parts.append(f"Missing: {missing}")

        return " | ".join(parts) if parts else "No explanation provided."

    @staticmethod
    def _build_evidence(raw_json: dict) -> list[str]:
        """
        Build the evidence list from Claude's detected ownership signals.

        Includes:
        - Strong and moderate ownership signals as positive evidence
        - Weak signals from the resume flagged for attention

        Args:
            raw_json: Parsed dict from Claude.

        Returns:
            List of evidence strings.
        """
        evidence = []

        # Positive ownership signals
        ownership_signals = raw_json.get("ownership_signals", [])
        for signal in ownership_signals:
            if not isinstance(signal, dict):
                continue

            text = signal.get("text", "").strip()
            signal_type = signal.get("signal_type", "").strip()
            strength = signal.get("strength", "").strip()

            if not text:
                continue

            if strength in ("strong", "moderate"):
                label = signal_type.replace("_", " ").title()
                evidence.append(f"[{strength.upper()}] {label}: {text}")

        # Weak signals flagged for interviewer attention
        weak_signals = raw_json.get("weak_signals", [])
        for signal in weak_signals:
            if not isinstance(signal, dict):
                continue

            text = signal.get("text", "").strip()
            suggestion = signal.get("suggestion", "").strip()

            if not text:
                continue

            if suggestion:
                evidence.append(f"[WEAK] Passive language: '{text}' → {suggestion}")
            else:
                evidence.append(f"[WEAK] Passive language: '{text}'")

        return evidence

    @staticmethod
    def _zero_score(reason: str) -> DimensionScore:
        """Return a zero score with a reason."""
        return DimensionScore(
            dimension=ScoreDimension.OWNERSHIP,
            score=0.0,
            explanation=reason,
            evidence=[],
        )


# Singleton
ownership_scorer = OwnershipScorer()
