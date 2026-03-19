from src.models import CandidateProfile, DimensionScore
from src.models.enums import ScoreDimension
from src.llm.client import llm_client
from src.llm.prompts.score_achievement import (
    SCORE_ACHIEVEMENT_SYSTEM,
    build_score_achievement_prompt,
    format_experience_for_prompt,
)


class AchievementScorer:
    """
    Scores the candidate based on the quality and quantity of
    measurable, quantified achievements in their work history.

    Uses Claude to detect achievement signals and assess impact.
    Does not require the JD — achievements are evaluated purely
    on the strength of the candidate's own claims.
    """

    def score(
        self,
        candidate: CandidateProfile,
    ) -> DimensionScore:
        """
        Compute the achievement score for a candidate.

        Args:
            candidate: Parsed candidate profile.

        Returns:
            DimensionScore with score + explanation + evidence.
        """
        # Guard: no experience to evaluate
        if not candidate.experience:
            return self._zero_score(
                "No work experience found in the candidate profile."
            )

        experience_text = format_experience_for_prompt(candidate.experience)

        prompt = build_score_achievement_prompt(
            experience_text=experience_text,
            candidate_name=candidate.full_name,
        )

        raw_json = llm_client.complete_json(
            prompt=prompt,
            system=SCORE_ACHIEVEMENT_SYSTEM,
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
        Parse Claude's achievement scoring response into a DimensionScore.

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
                dimension=ScoreDimension.ACHIEVEMENT,
                score=round(score, 2),
                explanation=explanation,
                evidence=evidence,
            )

        except Exception as e:
            raise ValueError(
                f"[AchievementScorer] Failed to parse Claude response "
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
        Build the explanation string from Claude's response.
        Combines the main explanation with missing signals if present.

        Args:
            raw_json: Parsed dict from Claude.

        Returns:
            Human-readable explanation string.
        """
        explanation = raw_json.get("explanation", "").strip()
        missing = raw_json.get("missing", "").strip()

        if explanation and missing:
            return f"{explanation} Missing: {missing}"

        return explanation or missing or "No explanation provided."

    @staticmethod
    def _build_evidence(raw_json: dict) -> list[str]:
        """
        Build the evidence list from Claude's detected achievement signals.
        Only includes strong and moderate signals as positive evidence.

        Args:
            raw_json: Parsed dict from Claude.

        Returns:
            List of evidence strings from the resume.
        """
        signals = raw_json.get("achievement_signals", [])
        evidence = []

        for signal in signals:
            if not isinstance(signal, dict):
                continue

            text = signal.get("text", "").strip()
            signal_type = signal.get("signal_type", "").strip()
            strength = signal.get("strength", "").strip()

            if not text:
                continue

            # Only surface strong and moderate signals as evidence
            if strength in ("strong", "moderate"):
                label = signal_type.replace("_", " ").title()
                evidence.append(f"[{strength.upper()}] {label}: {text}")

        return evidence

    @staticmethod
    def _zero_score(reason: str) -> DimensionScore:
        """Return a zero score with a reason."""
        return DimensionScore(
            dimension=ScoreDimension.ACHIEVEMENT,
            score=0.0,
            explanation=reason,
            evidence=[],
        )


# Singleton
achievement_scorer = AchievementScorer()