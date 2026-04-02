import pytest
from unittest.mock import patch
from src.models import DimensionScore
from src.models.enums import ScoreDimension
from src.scorer.achievement import AchievementScorer


@pytest.fixture
def scorer() -> AchievementScorer:
    return AchievementScorer()


# ------------------------------------------------------------------
# Mock response builders
# ------------------------------------------------------------------

def make_achievement_response(
    score: int = 75,
    signals: list[dict] | None = None,
    missing: str = "",
    explanation: str = "Test explanation.",
) -> dict:
    """
    Build a fake Claude achievement response dict.
    Used to mock llm_client.complete_json.
    """
    return {
        "score_0_to_100": score,
        "achievement_signals": signals or [
            {
                "text": "Reduced latency by 40%",
                "signal_type": "quantified_impact",
                "strength": "strong",
            },
            {
                "text": "Led team of 6 engineers",
                "signal_type": "team_size",
                "strength": "strong",
            },
        ],
        "missing": missing,
        "explanation": explanation,
    }


# ------------------------------------------------------------------
# Basic scoring
# ------------------------------------------------------------------

class TestBasicScoring:

    def test_returns_dimension_score(self, scorer, strong_candidate):
        """score() should return a DimensionScore instance."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(score=85),
        ):
            result = scorer.score(strong_candidate)

        assert isinstance(result, DimensionScore)
        assert result.dimension == ScoreDimension.ACHIEVEMENT

    def test_score_value_matches_llm_response(self, scorer, strong_candidate):
        """Score value should match what Claude returned."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(score=82),
        ):
            result = scorer.score(strong_candidate)

        assert result.score == 82.0

    def test_strong_candidate_gets_high_score(self, scorer, strong_candidate):
        """Strong candidate with quantified achievements → high score."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(score=88),
        ):
            result = scorer.score(strong_candidate)

        assert result.score >= 80.0

    def test_weak_candidate_gets_low_score(self, scorer, weak_candidate):
        """Weak candidate with no achievements → low score."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(
                score=15,
                signals=[],
                missing="No quantified achievements found.",
                explanation="Resume contains only vague responsibility statements.",
            ),
        ):
            result = scorer.score(weak_candidate)

        assert result.score < 40.0


# ------------------------------------------------------------------
# Empty experience guard
# ------------------------------------------------------------------

class TestEmptyExperience:

    def test_no_experience_returns_zero(self, scorer, minimal_candidate):
        """
        Candidate with no experience should return zero score
        without calling the LLM.
        """
        with patch(
            "src.scorer.achievement.llm_client.complete_json"
        ) as mock_llm:
            result = scorer.score(minimal_candidate)

            # LLM should NOT be called
            mock_llm.assert_not_called()

        assert result.score == 0.0
        assert result.explanation != ""

    def test_no_experience_explanation_is_clear(self, scorer, minimal_candidate):
        """Zero score explanation should be human-readable."""
        with patch("src.scorer.achievement.llm_client.complete_json"):
            result = scorer.score(minimal_candidate)

        assert "experience" in result.explanation.lower() or \
               "no" in result.explanation.lower()


# ------------------------------------------------------------------
# Explainability
# ------------------------------------------------------------------

class TestExplainability:

    def test_explanation_not_empty(self, scorer, strong_candidate):
        """Explanation must always be present."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(
                explanation="Strong quantified achievements across all roles."
            ),
        ):
            result = scorer.score(strong_candidate)

        assert result.explanation != ""
        assert len(result.explanation) > 10

    def test_explanation_includes_missing_when_present(
        self, scorer, weak_candidate
    ):
        """
        If Claude returns a 'missing' field, it should appear
        in the explanation.
        """
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(
                score=20,
                signals=[],
                missing="No revenue or cost impact mentioned.",
                explanation="Weak achievement signals throughout.",
            ),
        ):
            result = scorer.score(weak_candidate)

        assert "Missing" in result.explanation or \
               "missing" in result.explanation

    def test_explanation_without_missing_field(self, scorer, strong_candidate):
        """
        If Claude returns no 'missing' field, explanation
        should still be non-empty.
        """
        response = make_achievement_response(explanation="Good achievements.")
        response.pop("missing", None)

        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=response,
        ):
            result = scorer.score(strong_candidate)

        assert result.explanation == "Good achievements."

    def test_fallback_when_explanation_missing(self, scorer, strong_candidate):
        """
        If Claude omits explanation entirely, should not crash
        and should return a non-empty fallback.
        """
        response = {
            "score_0_to_100": 70,
            "achievement_signals": [],
            "missing": "",
        }
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=response,
        ):
            result = scorer.score(strong_candidate)

        assert result.explanation != ""


# ------------------------------------------------------------------
# Evidence building
# ------------------------------------------------------------------

class TestEvidenceBuilding:

    def test_strong_signals_appear_in_evidence(self, scorer, strong_candidate):
        """Strong achievement signals should appear in evidence list."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(
                signals=[
                    {
                        "text": "Reduced latency by 40%",
                        "signal_type": "quantified_impact",
                        "strength": "strong",
                    }
                ]
            ),
        ):
            result = scorer.score(strong_candidate)

        assert len(result.evidence) > 0
        assert any("Reduced latency by 40%" in e for e in result.evidence)

    def test_weak_signals_excluded_from_evidence(self, scorer, strong_candidate):
        """Weak signals should NOT appear in evidence."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(
                signals=[
                    {
                        "text": "Worked on backend services",
                        "signal_type": "quantified_impact",
                        "strength": "weak",
                    }
                ]
            ),
        ):
            result = scorer.score(strong_candidate)

        assert len(result.evidence) == 0

    def test_moderate_signals_appear_in_evidence(self, scorer, strong_candidate):
        """Moderate signals should appear in evidence."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(
                signals=[
                    {
                        "text": "Improved system performance",
                        "signal_type": "improvement",
                        "strength": "moderate",
                    }
                ]
            ),
        ):
            result = scorer.score(strong_candidate)

        assert len(result.evidence) > 0

    def test_empty_signals_gives_empty_evidence(self, scorer, strong_candidate):
        """No signals → empty evidence list."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(signals=[]),
        ):
            result = scorer.score(strong_candidate)

        assert result.evidence == []


# ------------------------------------------------------------------
# Score bounds and type safety
# ------------------------------------------------------------------

class TestScoreBoundsAndSafety:

    def test_score_clamped_above_100(self, scorer, strong_candidate):
        """Score above 100 from Claude should be clamped to 100."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(score=150),
        ):
            result = scorer.score(strong_candidate)

        assert result.score == 100.0

    def test_score_clamped_below_zero(self, scorer, strong_candidate):
        """Negative score from Claude should be clamped to 0."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(score=-20),
        ):
            result = scorer.score(strong_candidate)

        assert result.score == 0.0

    def test_non_numeric_score_defaults_to_zero(self, scorer, strong_candidate):
        """Non-numeric score from Claude should default to 0."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(score="high"),
        ):
            result = scorer.score(strong_candidate)

        assert result.score == 0.0

    def test_missing_score_field_defaults_to_zero(self, scorer, strong_candidate):
        """Missing score field in Claude response should default to 0."""
        response = {
            "achievement_signals": [],
            "missing": "",
            "explanation": "No score field.",
        }
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=response,
        ):
            result = scorer.score(strong_candidate)

        assert result.score == 0.0

    def test_score_is_float(self, scorer, strong_candidate):
        """Score should always be a float."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value=make_achievement_response(score=75),
        ):
            result = scorer.score(strong_candidate)

        assert isinstance(result.score, float)

    def test_malformed_signal_entries_skipped(self, scorer, strong_candidate):
        """Malformed signal entries should be skipped without crashing."""
        with patch(
            "src.scorer.achievement.llm_client.complete_json",
            return_value={
                "score_0_to_100": 60,
                "achievement_signals": [
                    None,
                    "not a dict",
                    {"text": "", "signal_type": "quantified_impact",
                     "strength": "strong"},
                    {"text": "Valid signal", "signal_type": "scale",
                     "strength": "strong"},
                ],
                "missing": "",
                "explanation": "Mixed signals.",
            },
        ):
            result = scorer.score(strong_candidate)

        assert result.score == 60.0
        assert isinstance(result.evidence, list)