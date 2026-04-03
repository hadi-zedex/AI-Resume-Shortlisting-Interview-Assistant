import pytest
from unittest.mock import patch
from src.models import DimensionScore
from src.models.enums import ScoreDimension
from src.scorer.ownership import OwnershipScorer


@pytest.fixture
def scorer() -> OwnershipScorer:
    return OwnershipScorer()


# ------------------------------------------------------------------
# Mock response builders
# ------------------------------------------------------------------

def make_ownership_response(
    score: int = 75,
    ownership_signals: list[dict] | None = None,
    weak_signals: list[dict] | None = None,
    seniority_context: str = "Mid-level role, moderate ownership expected.",
    missing: str = "",
    explanation: str = "Test explanation.",
) -> dict:
    """
    Build a fake Claude ownership response dict.
    Used to mock llm_client.complete_json.
    """
    return {
        "score_0_to_100": score,
        "ownership_signals": ownership_signals if ownership_signals is not None else [
            {
                "text": "Led a team of 6 engineers",
                "signal_type": "led_people",
                "strength": "strong",
            },
            {
                "text": "Designed the microservices architecture",
                "signal_type": "architected",
                "strength": "strong",
            },
        ],
        "weak_signals": weak_signals if weak_signals is not None else [],
        "seniority_context": seniority_context,
        "missing": missing,
        "explanation": explanation,
    }


# ------------------------------------------------------------------
# Basic scoring
# ------------------------------------------------------------------

class TestBasicScoring:

    def test_returns_dimension_score(
        self, scorer, strong_candidate, backend_jd
    ):
        """score() should return a DimensionScore instance."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(score=80),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert isinstance(result, DimensionScore)
        assert result.dimension == ScoreDimension.OWNERSHIP

    def test_score_value_matches_llm_response(
        self, scorer, strong_candidate, backend_jd
    ):
        """Score value should match what Claude returned."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(score=78),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.score == 78.0

    def test_strong_candidate_gets_high_score(
        self, scorer, strong_candidate, backend_jd
    ):
        """Strong candidate with ownership signals → high score."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(score=85),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.score >= 80.0

    def test_weak_candidate_gets_low_score(
        self, scorer, weak_candidate, backend_jd
    ):
        """Weak candidate with passive language → low score."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                score=18,
                ownership_signals=[],
                weak_signals=[
                    {
                        "text": "Assisted the team with backend tasks",
                        "suggestion": "Could have been: Led the team in...",
                    }
                ],
                missing="No evidence of decision-making or leadership.",
                explanation="Purely contributor language throughout.",
            ),
        ):
            result = scorer.score(weak_candidate, backend_jd)

        assert result.score < 40.0


# ------------------------------------------------------------------
# Empty experience guard
# ------------------------------------------------------------------

class TestEmptyExperience:

    def test_no_experience_returns_zero(
        self, scorer, minimal_candidate, backend_jd
    ):
        """
        Candidate with no experience should return zero score
        without calling the LLM.
        """
        with patch(
            "src.scorer.ownership.llm_client.complete_json"
        ) as mock_llm:
            result = scorer.score(minimal_candidate, backend_jd)

            mock_llm.assert_not_called()

        assert result.score == 0.0

    def test_no_experience_explanation_is_clear(
        self, scorer, minimal_candidate, backend_jd
    ):
        """Zero score explanation should be human-readable."""
        with patch("src.scorer.ownership.llm_client.complete_json"):
            result = scorer.score(minimal_candidate, backend_jd)

        assert "experience" in result.explanation.lower() or \
               "no" in result.explanation.lower()


# ------------------------------------------------------------------
# Explainability — three-field explanation
# ------------------------------------------------------------------

class TestExplainability:

    def test_explanation_not_empty(
        self, scorer, strong_candidate, backend_jd
    ):
        """Explanation must always be present."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                explanation="Clear ownership and leadership signals."
            ),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.explanation != ""
        assert len(result.explanation) > 10

    def test_explanation_includes_seniority_context(
        self, scorer, strong_candidate, backend_jd
    ):
        """
        Seniority context from Claude should appear
        in the final explanation string.
        """
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                seniority_context="Senior role — high ownership expected.",
                explanation="Strong ownership signals.",
            ),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert "Senior role" in result.explanation or \
               "seniority" in result.explanation.lower()

    def test_explanation_includes_missing_when_present(
        self, scorer, weak_candidate, backend_jd
    ):
        """Missing field should appear in explanation."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                score=20,
                missing="No evidence of architectural decisions.",
                explanation="Mostly executor language.",
            ),
        ):
            result = scorer.score(weak_candidate, backend_jd)

        assert "Missing" in result.explanation or \
               "architectural" in result.explanation

    def test_explanation_pipe_separated(
        self, scorer, strong_candidate, backend_jd
    ):
        """
        When all three fields (explanation, seniority, missing)
        are present, they should be joined with ' | '.
        """
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                explanation="Good ownership.",
                seniority_context="Senior role.",
                missing="No mentoring found.",
            ),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert "|" in result.explanation

    def test_explanation_when_all_fields_empty(
        self, scorer, strong_candidate, backend_jd
    ):
        """If all explanation fields are empty, should return fallback."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value={
                "score_0_to_100": 50,
                "ownership_signals": [],
                "weak_signals": [],
                "seniority_context": "",
                "missing": "",
                "explanation": "",
            },
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.explanation != ""


# ------------------------------------------------------------------
# Evidence — ownership signals
# ------------------------------------------------------------------

class TestOwnershipSignals:

    def test_strong_signals_in_evidence(
        self, scorer, strong_candidate, backend_jd
    ):
        """Strong ownership signals should appear in evidence."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                ownership_signals=[
                    {
                        "text": "Owned the migration end-to-end",
                        "signal_type": "drove_initiative",
                        "strength": "strong",
                    }
                ]
            ),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert any(
            "Owned the migration end-to-end" in e
            for e in result.evidence
        )

    def test_weak_signals_in_evidence_with_suggestion(
        self, scorer, weak_candidate, backend_jd
    ):
        """
        Weak signals should appear in evidence tagged as [WEAK]
        with the suggestion included.
        """
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                score=20,
                ownership_signals=[],
                weak_signals=[
                    {
                        "text": "Assisted the team",
                        "suggestion": "Could have been: Led the team in...",
                    }
                ],
            ),
        ):
            result = scorer.score(weak_candidate, backend_jd)

        weak_evidence = [e for e in result.evidence if "[WEAK]" in e]
        assert len(weak_evidence) > 0
        assert any("Assisted the team" in e for e in weak_evidence)
        assert any("Could have been" in e for e in weak_evidence)

    def test_weak_signal_without_suggestion(
        self, scorer, weak_candidate, backend_jd
    ):
        """Weak signal without suggestion should still appear in evidence."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                score=20,
                ownership_signals=[],
                weak_signals=[
                    {
                        "text": "Helped with API development",
                        "suggestion": "",
                    }
                ],
            ),
        ):
            result = scorer.score(weak_candidate, backend_jd)

        weak_evidence = [e for e in result.evidence if "[WEAK]" in e]
        assert len(weak_evidence) > 0

    def test_moderate_signals_in_evidence(
        self, scorer, strong_candidate, backend_jd
    ):
        """Moderate ownership signals should appear in evidence."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                ownership_signals=[
                    {
                        "text": "Contributed to architectural decisions",
                        "signal_type": "decision_making",
                        "strength": "moderate",
                    }
                ]
            ),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert len(result.evidence) > 0

    def test_empty_signals_gives_empty_positive_evidence(
        self, scorer, strong_candidate, backend_jd
    ):
        """No ownership signals → no positive evidence items."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(
                ownership_signals=[],
                weak_signals=[],
            ),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.evidence == []


# ------------------------------------------------------------------
# JD responsibilities passed to prompt
# ------------------------------------------------------------------

class TestJDResponsibilitiesContext:

    def test_jd_responsibilities_used_in_prompt(
        self, scorer, strong_candidate, backend_jd
    ):
        """
        The prompt builder should receive JD responsibilities.
        We verify the LLM is called (not short-circuited)
        when responsibilities are present.
        """
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(),
        ) as mock_llm:
            scorer.score(strong_candidate, backend_jd)

            mock_llm.assert_called_once()

    def test_minimal_jd_no_responsibilities(
        self, scorer, strong_candidate, minimal_jd
    ):
        """
        Scorer should work fine with a JD that has no responsibilities.
        No crash expected.
        """
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(score=60),
        ):
            result = scorer.score(strong_candidate, minimal_jd)

        assert isinstance(result, DimensionScore)
        assert result.score == 60.0


# ------------------------------------------------------------------
# Score bounds and type safety
# ------------------------------------------------------------------

class TestScoreBoundsAndSafety:

    def test_score_clamped_above_100(
        self, scorer, strong_candidate, backend_jd
    ):
        """Score above 100 should be clamped to 100."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(score=120),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.score == 100.0

    def test_score_clamped_below_zero(
        self, scorer, strong_candidate, backend_jd
    ):
        """Negative score should be clamped to 0."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(score=-10),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.score == 0.0

    def test_non_numeric_score_defaults_to_zero(
        self, scorer, strong_candidate, backend_jd
    ):
        """Non-numeric score should default to 0."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(score="excellent"),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.score == 0.0

    def test_malformed_ownership_signals_skipped(
        self, scorer, strong_candidate, backend_jd
    ):
        """Malformed signal entries should be skipped without crashing."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value={
                "score_0_to_100": 65,
                "ownership_signals": [
                    None,
                    "not a dict",
                    {"text": "", "signal_type": "led_people",
                     "strength": "strong"},
                    {"text": "Valid signal", "signal_type": "architected",
                     "strength": "strong"},
                ],
                "weak_signals": [None, "bad entry"],
                "seniority_context": "",
                "missing": "",
                "explanation": "Mixed signals.",
            },
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.score == 65.0
        assert isinstance(result.evidence, list)

    def test_missing_fields_in_response_no_crash(
        self, scorer, strong_candidate, backend_jd
    ):
        """Completely minimal response should not crash."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value={"score_0_to_100": 50},
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert result.score == 50.0
        assert isinstance(result, DimensionScore)

    def test_score_is_float(self, scorer, strong_candidate, backend_jd):
        """Score should always be a float."""
        with patch(
            "src.scorer.ownership.llm_client.complete_json",
            return_value=make_ownership_response(score=70),
        ):
            result = scorer.score(strong_candidate, backend_jd)

        assert isinstance(result.score, float)