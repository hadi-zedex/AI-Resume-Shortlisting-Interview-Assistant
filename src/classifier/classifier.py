from src.models import ScoringResult, TierClassification, TierThresholds
from src.models.tier import TIER_LABELS
from src.models.enums import Tier, ScoreDimension
from src.config import config


class TierClassifier:
    """
    Classifies a candidate into Tier A, B, or C based on their
    overall score from the ScoringEngine.

    Responsibilities:
    - Apply threshold logic to assign a tier
    - Generate human-readable reasoning for the decision
    - Identify focus areas for the interviewer
    - Produce a recommended action for the recruiter

    Contains NO scoring logic — only classification and interpretation.
    """

    def classify(
        self,
        scoring_result: ScoringResult,
        thresholds: TierThresholds | None = None,
    ) -> TierClassification:
        """
        Classify a candidate into a tier based on their ScoringResult.

        Args:
            scoring_result: The fully populated ScoringResult from ScoringEngine.
            thresholds:     Optional custom thresholds. Defaults to config values.

        Returns:
            TierClassification with tier, reasoning, and recommended action.
        """
        thresholds = thresholds or TierThresholds(
            tier_a_min=config.TIER_A_MIN_SCORE,
            tier_b_min=config.TIER_B_MIN_SCORE,
        )

        tier = self._assign_tier(scoring_result.overall_score, thresholds)
        labels = TIER_LABELS[tier]
        reasoning = self._build_reasoning(scoring_result, tier)
        focus_areas = self._derive_focus_areas(scoring_result, tier)

        print(
            f"[TierClassifier] '{scoring_result.candidate_name}' → "
            f"Tier {tier.value} "
            f"(score: {scoring_result.overall_score:.1f})"
        )

        return TierClassification(
            tier=tier,
            overall_score=scoring_result.overall_score,
            decision_label=labels["decision_label"],
            reasoning=reasoning,
            recommended_action=labels["recommended_action"],
            focus_areas=focus_areas,
            thresholds_used=thresholds,
            scoring_result=scoring_result,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _assign_tier(
        overall_score: float,
        thresholds: TierThresholds,
    ) -> Tier:
        """
        Apply threshold logic to assign a Tier enum value.

        Args:
            overall_score: Weighted overall score from ScoringEngine.
            thresholds:    Tier boundary thresholds.

        Returns:
            Tier enum value (A, B, or C).
        """
        if overall_score >= thresholds.tier_a_min:
            return Tier.A
        elif overall_score >= thresholds.tier_b_min:
            return Tier.B
        else:
            return Tier.C

    @staticmethod
    def _build_reasoning(
        scoring_result: ScoringResult,
        tier: Tier,
    ) -> str:
        """
        Build a human-readable reasoning string explaining the tier decision.
        Combines overall score context with per-dimension highlights.

        Args:
            scoring_result: Full scoring result with all 4 dimension scores.
            tier:           The assigned tier.

        Returns:
            Multi-sentence reasoning string.
        """
        score = scoring_result.overall_score
        name = scoring_result.candidate_name

        # Opening sentence based on tier
        tier_openers = {
            Tier.A: f"{name} is a strong match with an overall score of {score:.1f}.",
            Tier.B: f"{name} is a moderate match with an overall score of {score:.1f}.",
            Tier.C: f"{name} is a weak match with an overall score of {score:.1f}.",
        }
        parts = [tier_openers[tier]]

        # Highlight strongest dimension
        dimension_scores = {
            ScoreDimension.EXACT_MATCH:         scoring_result.exact_match.score,
            ScoreDimension.SEMANTIC_SIMILARITY:  scoring_result.semantic_similarity.score,
            ScoreDimension.ACHIEVEMENT:          scoring_result.achievement.score,
            ScoreDimension.OWNERSHIP:            scoring_result.ownership.score,
        }

        dimension_labels = {
            ScoreDimension.EXACT_MATCH:         "exact skill match",
            ScoreDimension.SEMANTIC_SIMILARITY:  "semantic skill equivalence",
            ScoreDimension.ACHIEVEMENT:          "quantified achievements",
            ScoreDimension.OWNERSHIP:            "ownership and leadership signals",
        }

        strongest = max(dimension_scores, key=dimension_scores.get)
        weakest = min(dimension_scores, key=dimension_scores.get)

        strongest_score = dimension_scores[strongest]
        weakest_score = dimension_scores[weakest]

        if strongest_score >= 70:
            parts.append(
                f"Strongest area: {dimension_labels[strongest]} "
                f"({strongest_score:.1f}/100)."
            )

        if weakest_score < 50:
            parts.append(
                f"Weakest area: {dimension_labels[weakest]} "
                f"({weakest_score:.1f}/100)."
            )

        # Surface top-level strengths and gaps
        if scoring_result.strengths:
            parts.append(
                f"Key strengths: {'; '.join(scoring_result.strengths[:2])}."
            )

        if scoring_result.gaps:
            parts.append(
                f"Notable gaps: {'; '.join(scoring_result.gaps[:2])}."
            )

        return " ".join(parts)

    @staticmethod
    def _derive_focus_areas(
        scoring_result: ScoringResult,
        tier: Tier,
    ) -> list[str]:
        """
        Derive focus areas for the interviewer based on weak dimensions
        and tier-specific concerns.

        Focus areas are derived from:
        1. Dimensions that scored below 60 — probe these
        2. Skill gaps identified by the scorers
        3. Tier-specific standard probes

        Args:
            scoring_result: Full scoring result.
            tier:           Assigned tier.

        Returns:
            List of focus area strings for the interviewer.
        """
        focus_areas = []

        # Probe weak dimensions
        dimension_checks = [
            (
                scoring_result.exact_match,
                "Verify claimed skills directly — exact keyword match was low.",
            ),
            (
                scoring_result.semantic_similarity,
                "Probe depth of adjacent technologies — "
                "candidate relies on semantic equivalences.",
            ),
            (
                scoring_result.achievement,
                "Ask for specific metrics and impact — "
                "resume lacks quantified achievements.",
            ),
            (
                scoring_result.ownership,
                "Probe decision-making and leadership — "
                "resume shows mostly contributor-level language.",
            ),
        ]

        for dim_score, focus_message in dimension_checks:
            if dim_score.score < 60:
                focus_areas.append(focus_message)

        # Add top skill gaps
        if scoring_result.gaps:
            for gap in scoring_result.gaps[:2]:
                focus_areas.append(gap)

        # Tier-specific standard probes
        tier_probes = {
            Tier.A: [
                "Assess system design depth — candidate is fast-track calibre.",
                "Evaluate culture and team fit given strong technical signals.",
            ],
            Tier.B: [
                "Run a focused technical screen before moving forward.",
                "Verify the semantic skill matches with hands-on questions.",
            ],
            Tier.C: [
                "Consider a take-home skills assessment before investing in an interview.",
                "Re-evaluate if the JD requirements are correctly calibrated.",
            ],
        }

        focus_areas.extend(tier_probes[tier])

        return focus_areas


# Singleton
tier_classifier = TierClassifier()