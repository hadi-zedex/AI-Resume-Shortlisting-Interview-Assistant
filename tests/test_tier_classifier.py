import pytest
from src.models import TierClassification, TierThresholds
from src.models.enums import Tier
from src.classifier.classifier import TierClassifier


@pytest.fixture
def classifier() -> TierClassifier:
    return TierClassifier()


# ------------------------------------------------------------------
# Tier assignment — standard cases
# ------------------------------------------------------------------

class TestTierAssignment:

    def test_high_score_assigns_tier_a(
        self, classifier, perfect_scoring_result
    ):
        """Score of 89.9 should assign Tier A."""
        result = classifier.classify(perfect_scoring_result)

        assert result.tier == Tier.A

    def test_low_score_assigns_tier_c(
        self, classifier, weak_scoring_result
    ):
        """Score of 14.9 should assign Tier C."""
        result = classifier.classify(weak_scoring_result)

        assert result.tier == Tier.C

    def test_mid_score_assigns_tier_b(self, classifier, boundary_b_scoring_result):
        """Score of 55.0 should assign Tier B (at lower boundary)."""
        result = classifier.classify(boundary_b_scoring_result)

        assert result.tier == Tier.B


# ------------------------------------------------------------------
# Boundary conditions — the most important tests
# ------------------------------------------------------------------

class TestBoundaryConditions:

    def test_exactly_80_is_tier_a(
        self, classifier, boundary_a_scoring_result
    ):
        """Score of exactly 80.0 should be Tier A, not Tier B."""
        result = classifier.classify(boundary_a_scoring_result)

        assert result.tier == Tier.A

    def test_79_point_9_is_tier_b(self, classifier, boundary_a_scoring_result):
        """Score of 79.9 should be Tier B, not Tier A."""
        boundary_a_scoring_result.overall_score = 79.9
        result = classifier.classify(boundary_a_scoring_result)

        assert result.tier == Tier.B

    def test_exactly_55_is_tier_b(
        self, classifier, boundary_b_scoring_result
    ):
        """Score of exactly 55.0 should be Tier B, not Tier C."""
        result = classifier.classify(boundary_b_scoring_result)

        assert result.tier == Tier.B

    def test_54_point_9_is_tier_c(self, classifier, boundary_b_scoring_result):
        """Score of 54.9 should be Tier C, not Tier B."""
        boundary_b_scoring_result.overall_score = 54.9
        result = classifier.classify(boundary_b_scoring_result)

        assert result.tier == Tier.C

    def test_zero_score_is_tier_c(self, classifier, weak_scoring_result):
        """Score of 0.0 should be Tier C."""
        weak_scoring_result.overall_score = 0.0
        result = classifier.classify(weak_scoring_result)

        assert result.tier == Tier.C

    def test_perfect_score_is_tier_a(self, classifier, perfect_scoring_result):
        """Score of 100.0 should be Tier A."""
        perfect_scoring_result.overall_score = 100.0
        result = classifier.classify(perfect_scoring_result)

        assert result.tier == Tier.A


# ------------------------------------------------------------------
# Custom thresholds
# ------------------------------------------------------------------

class TestCustomThresholds:

    def test_custom_thresholds_applied(
        self, classifier, boundary_a_scoring_result
    ):
        """
        Custom threshold of 90 for Tier A means score of 80
        should now be Tier B.
        """
        strict_thresholds = TierThresholds(
            tier_a_min=90.0,
            tier_b_min=60.0,
        )
        result = classifier.classify(
            boundary_a_scoring_result,
            thresholds=strict_thresholds,
        )

        assert result.tier == Tier.B

    def test_lenient_thresholds(
        self, classifier, boundary_b_scoring_result
    ):
        """
        Lenient threshold of 40 for Tier B means score of 55
        should now be Tier A.
        """
        lenient_thresholds = TierThresholds(
            tier_a_min=50.0,
            tier_b_min=30.0,
        )
        result = classifier.classify(
            boundary_b_scoring_result,
            thresholds=lenient_thresholds,
        )

        assert result.tier == Tier.A

    def test_thresholds_stored_on_result(
        self, classifier, boundary_a_scoring_result
    ):
        """Thresholds used should be stored on the result for auditability."""
        custom = TierThresholds(tier_a_min=85.0, tier_b_min=60.0)
        result = classifier.classify(
            boundary_a_scoring_result,
            thresholds=custom,
        )

        assert result.thresholds_used.tier_a_min == 85.0
        assert result.thresholds_used.tier_b_min == 60.0

    def test_default_thresholds_from_config(
        self, classifier, boundary_a_scoring_result
    ):
        """Without custom thresholds, config defaults should be used."""
        from src.config import config

        result = classifier.classify(boundary_a_scoring_result)

        assert result.thresholds_used.tier_a_min == config.TIER_A_MIN_SCORE
        assert result.thresholds_used.tier_b_min == config.TIER_B_MIN_SCORE


# ------------------------------------------------------------------
# Output fields
# ------------------------------------------------------------------

class TestOutputFields:

    def test_returns_tier_classification(
        self, classifier, perfect_scoring_result
    ):
        """classify() should return a TierClassification instance."""
        result = classifier.classify(perfect_scoring_result)

        assert isinstance(result, TierClassification)

    def test_overall_score_preserved(
        self, classifier, perfect_scoring_result
    ):
        """Overall score on result should match input scoring result."""
        result = classifier.classify(perfect_scoring_result)

        assert result.overall_score == perfect_scoring_result.overall_score

    def test_scoring_result_embedded(
        self, classifier, perfect_scoring_result
    ):
        """Full ScoringResult should be embedded in TierClassification."""
        result = classifier.classify(perfect_scoring_result)

        assert result.scoring_result is not None
        assert result.scoring_result.candidate_name == "Alice Strong"

    def test_decision_label_not_empty(
        self, classifier, perfect_scoring_result
    ):
        """Decision label should never be empty."""
        result = classifier.classify(perfect_scoring_result)

        assert result.decision_label != ""
        assert len(result.decision_label) > 5

    def test_recommended_action_not_empty(
        self, classifier, perfect_scoring_result
    ):
        """Recommended action should never be empty."""
        result = classifier.classify(perfect_scoring_result)

        assert result.recommended_action != ""

    def test_reasoning_not_empty(
        self, classifier, perfect_scoring_result
    ):
        """Reasoning should never be empty."""
        result = classifier.classify(perfect_scoring_result)

        assert result.reasoning != ""
        assert len(result.reasoning) > 20

    def test_reasoning_contains_candidate_name(
        self, classifier, perfect_scoring_result
    ):
        """Reasoning should reference the candidate by name."""
        result = classifier.classify(perfect_scoring_result)

        assert "Alice Strong" in result.reasoning

    def test_reasoning_contains_score(
        self, classifier, perfect_scoring_result
    ):
        """Reasoning should mention the overall score."""
        result = classifier.classify(perfect_scoring_result)

        assert str(int(perfect_scoring_result.overall_score)) in result.reasoning


# ------------------------------------------------------------------
# Focus areas
# ------------------------------------------------------------------

class TestFocusAreas:

    def test_focus_areas_not_empty(
        self, classifier, perfect_scoring_result
    ):
        """Every classification should produce at least one focus area."""
        result = classifier.classify(perfect_scoring_result)

        assert len(result.focus_areas) > 0

    def test_weak_candidate_has_more_focus_areas(
        self, classifier, perfect_scoring_result, weak_scoring_result
    ):
        """
        Weak candidates should have more focus areas than strong ones
        since more dimensions need probing.
        """
        strong_result = classifier.classify(perfect_scoring_result)
        weak_result = classifier.classify(weak_scoring_result)

        assert len(weak_result.focus_areas) >= len(strong_result.focus_areas)

    def test_tier_c_has_evaluation_probe(
        self, classifier, weak_scoring_result
    ):
        """Tier C should always include an evaluation-specific probe."""
        result = classifier.classify(weak_scoring_result)

        combined = " ".join(result.focus_areas).lower()
        assert any(
            word in combined
            for word in ["assessment", "evaluate", "manual", "hold"]
        )

    def test_tier_a_has_system_design_probe(
        self, classifier, perfect_scoring_result
    ):
        """Tier A should always include a system design probe."""
        result = classifier.classify(perfect_scoring_result)

        combined = " ".join(result.focus_areas).lower()
        assert any(
            word in combined
            for word in ["system design", "architecture", "design", "fast-track"]
        )


# ------------------------------------------------------------------
# Tier labels
# ------------------------------------------------------------------

class TestTierLabels:

    def test_tier_a_label(self, classifier, perfect_scoring_result):
        """Tier A should have fast-track label."""
        result = classifier.classify(perfect_scoring_result)

        assert "fast" in result.decision_label.lower() or \
               "final" in result.decision_label.lower()

    def test_tier_b_label(self, classifier, boundary_b_scoring_result):
        """Tier B should have technical screen label."""
        result = classifier.classify(boundary_b_scoring_result)

        assert "screen" in result.decision_label.lower() or \
               "technical" in result.decision_label.lower()

    def test_tier_c_label(self, classifier, weak_scoring_result):
        """Tier C should have evaluation label."""
        result = classifier.classify(weak_scoring_result)

        assert "evaluation" in result.decision_label.lower() or \
               "needs" in result.decision_label.lower()