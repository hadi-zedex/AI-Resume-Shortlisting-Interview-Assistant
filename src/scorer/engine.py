from src.models import (
    CandidateProfile,
    JobDescription,
    ScoringResult,
    DimensionScore,
    SkillMatchDetail,
)
from src.models.enums import ScoreDimension
from src.config import config
from src.scorer.exact_match import exact_match_scorer
from src.scorer.semantic_similarity import semantic_similarity_scorer
from src.scorer.achievement import achievement_scorer
from src.scorer.ownership import ownership_scorer


class ScoringEngine:
    """
    Orchestrates all 4 scorers and assembles the final ScoringResult.

    Responsibilities:
    - Run all 4 scorers in the correct order
    - Combine per-dimension scores into a weighted overall score
    - Merge SkillMatchDetails from exact + semantic scorers
    - Derive top-level strengths and gaps from dimension results
    - Return a fully populated ScoringResult

    This class contains NO scoring logic itself.
    It only orchestrates, aggregates, and assembles.
    """

    def run(
        self,
        candidate: CandidateProfile,
        jd: JobDescription,
    ) -> ScoringResult:
        """
        Run the full scoring pipeline for a candidate against a JD.

        Order matters:
            1. ExactMatch runs first — its results are passed to SemanticSimilarity
               so already-matched skills are not re-evaluated.
            2. SemanticSimilarity runs second — evaluates only unmatched skills.
            3. Achievement and Ownership run independently — no dependencies.

        Args:
            candidate: Parsed CandidateProfile.
            jd:        Parsed JobDescription.

        Returns:
            Fully populated ScoringResult.
        """
        print(f"[ScoringEngine] Scoring '{candidate.full_name}' for '{jd.title}'...")

        # --- Step 1: Exact Match ---
        print("[ScoringEngine] Running ExactMatchScorer...")
        exact_score, exact_details = exact_match_scorer.score(candidate, jd)

        # --- Step 2: Semantic Similarity (receives exact match details) ---
        print("[ScoringEngine] Running SemanticSimilarityScorer...")
        semantic_score, semantic_details = semantic_similarity_scorer.score(
            candidate=candidate,
            jd=jd,
            exact_match_details=exact_details,
        )

        # --- Step 3: Achievement ---
        print("[ScoringEngine] Running AchievementScorer...")
        achievement_score = achievement_scorer.score(candidate)

        # --- Step 4: Ownership ---
        print("[ScoringEngine] Running OwnershipScorer...")
        ownership_score = ownership_scorer.score(candidate, jd)

        # --- Step 5: Compute overall weighted score ---
        overall_score, score_breakdown = self._compute_overall_score(
            exact_score=exact_score,
            semantic_score=semantic_score,
            achievement_score=achievement_score,
            ownership_score=ownership_score,
        )

        # --- Step 6: Merge all skill match details ---
        all_skill_matches = exact_details + semantic_details

        # --- Step 7: Derive strengths and gaps ---
        strengths, gaps = self._derive_strengths_and_gaps(
            exact_score=exact_score,
            semantic_score=semantic_score,
            achievement_score=achievement_score,
            ownership_score=ownership_score,
        )

        print(
            f"[ScoringEngine] Done. "
            f"Overall score: {overall_score:.1f} | "
            f"Exact: {exact_score.score:.1f} | "
            f"Semantic: {semantic_score.score:.1f} | "
            f"Achievement: {achievement_score.score:.1f} | "
            f"Ownership: {ownership_score.score:.1f}"
        )

        return ScoringResult(
            candidate_name=candidate.full_name,
            jd_title=jd.title,
            exact_match=exact_score,
            semantic_similarity=semantic_score,
            achievement=achievement_score,
            ownership=ownership_score,
            overall_score=round(overall_score, 2),
            score_breakdown=score_breakdown,
            skill_matches=all_skill_matches,
            strengths=strengths,
            gaps=gaps,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_overall_score(
        exact_score: DimensionScore,
        semantic_score: DimensionScore,
        achievement_score: DimensionScore,
        ownership_score: DimensionScore,
    ) -> tuple[float, dict[ScoreDimension, float]]:
        """
        Compute the weighted overall score from the 4 dimension scores.
        Weights are pulled from config so they can be adjusted without
        touching this logic.

        Args:
            exact_score:       DimensionScore from ExactMatchScorer.
            semantic_score:    DimensionScore from SemanticSimilarityScorer.
            achievement_score: DimensionScore from AchievementScorer.
            ownership_score:   DimensionScore from OwnershipScorer.

        Returns:
            Tuple of:
                - overall_score: float clamped 0–100
                - score_breakdown: dict mapping each dimension to its weight
        """
        weights = {
            ScoreDimension.EXACT_MATCH:          config.WEIGHT_EXACT_MATCH,
            ScoreDimension.SEMANTIC_SIMILARITY:   config.WEIGHT_SEMANTIC_SIMILARITY,
            ScoreDimension.ACHIEVEMENT:           config.WEIGHT_ACHIEVEMENT,
            ScoreDimension.OWNERSHIP:             config.WEIGHT_OWNERSHIP,
        }

        weighted_sum = (
            exact_score.score       * config.WEIGHT_EXACT_MATCH +
            semantic_score.score    * config.WEIGHT_SEMANTIC_SIMILARITY +
            achievement_score.score * config.WEIGHT_ACHIEVEMENT +
            ownership_score.score   * config.WEIGHT_OWNERSHIP
        )

        overall = min(100.0, max(0.0, weighted_sum))

        return overall, weights

    @staticmethod
    def _derive_strengths_and_gaps(
        exact_score: DimensionScore,
        semantic_score: DimensionScore,
        achievement_score: DimensionScore,
        ownership_score: DimensionScore,
    ) -> tuple[list[str], list[str]]:
        """
        Derive human-readable strengths and gaps from the 4 dimension scores.

        Thresholds:
            strength → dimension score >= 70
            gap      → dimension score <  50

        Args:
            exact_score:       DimensionScore from ExactMatchScorer.
            semantic_score:    DimensionScore from SemanticSimilarityScorer.
            achievement_score: DimensionScore from AchievementScorer.
            ownership_score:   DimensionScore from OwnershipScorer.

        Returns:
            Tuple of:
                - strengths: list of strength description strings
                - gaps:      list of gap description strings
        """
        STRENGTH_THRESHOLD = 70.0
        GAP_THRESHOLD = 50.0

        dimension_labels = {
            ScoreDimension.EXACT_MATCH: (
                "Strong keyword alignment with JD requirements",
                "Missing key required skills from the JD",
            ),
            ScoreDimension.SEMANTIC_SIMILARITY: (
                "Good functional equivalence across tech stack",
                "Tech stack has limited overlap with JD requirements",
            ),
            ScoreDimension.ACHIEVEMENT: (
                "Well-demonstrated quantified impact and achievements",
                "Lacks quantified achievements and measurable impact",
            ),
            ScoreDimension.OWNERSHIP: (
                "Clear ownership and leadership signals throughout",
                "Mostly contributor-level language, limited ownership signals",
            ),
        }

        scores = {
            ScoreDimension.EXACT_MATCH:        exact_score,
            ScoreDimension.SEMANTIC_SIMILARITY: semantic_score,
            ScoreDimension.ACHIEVEMENT:         achievement_score,
            ScoreDimension.OWNERSHIP:           ownership_score,
        }

        strengths = []
        gaps = []

        for dimension, dim_score in scores.items():
            strength_label, gap_label = dimension_labels[dimension]

            if dim_score.score >= STRENGTH_THRESHOLD:
                strengths.append(strength_label)
            elif dim_score.score < GAP_THRESHOLD:
                gaps.append(gap_label)

        return strengths, gaps


# Singleton
scoring_engine = ScoringEngine()