import pytest
from unittest.mock import patch, MagicMock
from src.models import (
    ScoringResult,
    DimensionScore,
    SkillMatchDetail,
)
from src.models.enums import ScoreDimension, MatchType
from src.scorer.engine import ScoringEngine


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


# ------------------------------------------------------------------
# Mock score builders
# ------------------------------------------------------------------

def make_dimension_score(
    dimension: ScoreDimension,
    score: float = 75.0,
    explanation: str = "Test explanation.",
    evidence: list[str] | None = None,
) -> DimensionScore:
    """Build a fake DimensionScore for mocking individual scorers."""
    return DimensionScore(
        dimension=dimension,
        score=score,
        explanation=explanation,
        evidence=evidence or [],
    )


def make_skill_detail(
    jd_skill: str = "Python",
    candidate_skill: str = "Python",
    match_type: MatchType = MatchType.EXACT,
) -> SkillMatchDetail:
    """Build a fake SkillMatchDetail."""
    return SkillMatchDetail(
        jd_skill=jd_skill,
        candidate_skill=candidate_skill,
        match_type=match_type,
        explanation="Test match.",
    )


def patch_all_scorers(
    exact_score: float = 80.0,
    semantic_score: float = 75.0,
    achievement_score: float = 70.0,
    ownership_score: float = 65.0,
    exact_details: list | None = None,
    semantic_details: list | None = None,
):
    """
    Context manager that patches all 4 scorers simultaneously.
    Returns a dict of patches for individual assertion if needed.
    """
    exact_dim = make_dimension_score(
        ScoreDimension.EXACT_MATCH, exact_score
    )
    semantic_dim = make_dimension_score(
        ScoreDimension.SEMANTIC_SIMILARITY, semantic_score
    )
    achievement_dim = make_dimension_score(
        ScoreDimension.ACHIEVEMENT, achievement_score
    )
    ownership_dim = make_dimension_score(
        ScoreDimension.OWNERSHIP, ownership_score
    )

    return {
        "exact": patch(
            "src.scorer.engine.exact_match_scorer.score",
            return_value=(
                exact_dim,
                exact_details or [make_skill_detail()],
            ),
        ),
        "semantic": patch(
            "src.scorer.engine.semantic_similarity_scorer.score",
            return_value=(
                semantic_dim,
                semantic_details or [],
            ),
        ),
        "achievement": patch(
            "src.scorer.engine.achievement_scorer.score",
            return_value=achievement_dim,
        ),
        "ownership": patch(
            "src.scorer.engine.ownership_scorer.score",
            return_value=ownership_dim,
        ),
    }


# ------------------------------------------------------------------
# Basic orchestration
# ------------------------------------------------------------------

class TestBasicOrchestration:

    def test_returns_scoring_result(
        self, engine, strong_candidate, backend_jd
    ):
        """run() should return a ScoringResult instance."""
        patches = patch_all_scorers()
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert isinstance(result, ScoringResult)

    def test_candidate_name_on_result(
        self, engine, strong_candidate, backend_jd
    ):
        """Candidate name should be preserved on ScoringResult."""
        patches = patch_all_scorers()
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.candidate_name == strong_candidate.full_name

    def test_jd_title_on_result(
        self, engine, strong_candidate, backend_jd
    ):
        """JD title should be preserved on ScoringResult."""
        patches = patch_all_scorers()
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.jd_title == backend_jd.title

    def test_all_four_dimensions_present(
        self, engine, strong_candidate, backend_jd
    ):
        """All 4 DimensionScores should be present on result."""
        patches = patch_all_scorers()
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.exact_match is not None
        assert result.semantic_similarity is not None
        assert result.achievement is not None
        assert result.ownership is not None


# ------------------------------------------------------------------
# Overall score computation
# ------------------------------------------------------------------

class TestOverallScoreComputation:

    def test_overall_score_is_weighted_average(
        self, engine, strong_candidate, backend_jd
    ):
        """
        Overall score should be the weighted average of the 4 dimensions.
        Using equal 25% weights for predictable math.
        """
        from src.config import config

        patches = patch_all_scorers(
            exact_score=80.0,
            semantic_score=60.0,
            achievement_score=40.0,
            ownership_score=20.0,
        )
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        expected = (
            80.0 * config.WEIGHT_EXACT_MATCH +
            60.0 * config.WEIGHT_SEMANTIC_SIMILARITY +
            40.0 * config.WEIGHT_ACHIEVEMENT +
            20.0 * config.WEIGHT_OWNERSHIP
        )
        assert abs(result.overall_score - expected) < 0.01

    def test_perfect_scores_give_100(
        self, engine, strong_candidate, backend_jd
    ):
        """All dimensions at 100 should give overall score of 100."""
        patches = patch_all_scorers(
            exact_score=100.0,
            semantic_score=100.0,
            achievement_score=100.0,
            ownership_score=100.0,
        )
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.overall_score == 100.0

    def test_zero_scores_give_zero(
        self, engine, strong_candidate, backend_jd
    ):
        """All dimensions at 0 should give overall score of 0."""
        patches = patch_all_scorers(
            exact_score=0.0,
            semantic_score=0.0,
            achievement_score=0.0,
            ownership_score=0.0,
        )
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.overall_score == 0.0

    def test_score_breakdown_stored(
        self, engine, strong_candidate, backend_jd
    ):
        """Score breakdown dict should be stored on the result."""
        patches = patch_all_scorers()
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert len(result.score_breakdown) == 4
        assert ScoreDimension.EXACT_MATCH in result.score_breakdown
        assert ScoreDimension.SEMANTIC_SIMILARITY in result.score_breakdown
        assert ScoreDimension.ACHIEVEMENT in result.score_breakdown
        assert ScoreDimension.OWNERSHIP in result.score_breakdown

    def test_overall_score_clamped_to_100(
        self, engine, strong_candidate, backend_jd
    ):
        """Overall score should never exceed 100."""
        patches = patch_all_scorers(
            exact_score=100.0,
            semantic_score=100.0,
            achievement_score=100.0,
            ownership_score=100.0,
        )
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.overall_score <= 100.0


# ------------------------------------------------------------------
# Scorer execution order
# ------------------------------------------------------------------

class TestScorerExecutionOrder:

    def test_exact_match_runs_before_semantic(
        self, engine, strong_candidate, backend_jd
    ):
        """
        ExactMatchScorer must run before SemanticSimilarityScorer.
        SemanticScorer should receive exact match details.
        """
        call_order = []

        def mock_exact(*args, **kwargs):
            call_order.append("exact")
            return (
                make_dimension_score(ScoreDimension.EXACT_MATCH, 80.0),
                [make_skill_detail()],
            )

        def mock_semantic(*args, **kwargs):
            call_order.append("semantic")
            return (
                make_dimension_score(ScoreDimension.SEMANTIC_SIMILARITY, 70.0),
                [],
            )

        def mock_achievement(*args, **kwargs):
            call_order.append("achievement")
            return make_dimension_score(ScoreDimension.ACHIEVEMENT, 60.0)

        def mock_ownership(*args, **kwargs):
            call_order.append("ownership")
            return make_dimension_score(ScoreDimension.OWNERSHIP, 50.0)

        with patch("src.scorer.engine.exact_match_scorer.score",
                   side_effect=mock_exact), \
             patch("src.scorer.engine.semantic_similarity_scorer.score",
                   side_effect=mock_semantic), \
             patch("src.scorer.engine.achievement_scorer.score",
                   side_effect=mock_achievement), \
             patch("src.scorer.engine.ownership_scorer.score",
                   side_effect=mock_ownership):
            engine.run(strong_candidate, backend_jd)

        assert call_order.index("exact") < call_order.index("semantic")

    def test_semantic_receives_exact_match_details(
        self, engine, strong_candidate, backend_jd
    ):
        """
        SemanticScorer should receive the exact match details
        from the ExactMatchScorer — not None.
        """
        exact_details = [
            make_skill_detail("Python", "Python", MatchType.EXACT),
            make_skill_detail("Kafka",  "Kafka",  MatchType.EXACT),
        ]
        semantic_mock = MagicMock(
            return_value=(
                make_dimension_score(ScoreDimension.SEMANTIC_SIMILARITY, 70.0),
                [],
            )
        )

        with patch(
            "src.scorer.engine.exact_match_scorer.score",
            return_value=(
                make_dimension_score(ScoreDimension.EXACT_MATCH, 80.0),
                exact_details,
            ),
        ), patch(
            "src.scorer.engine.semantic_similarity_scorer.score",
            new=semantic_mock,
        ), patch(
            "src.scorer.engine.achievement_scorer.score",
            return_value=make_dimension_score(ScoreDimension.ACHIEVEMENT, 60.0),
        ), patch(
            "src.scorer.engine.ownership_scorer.score",
            return_value=make_dimension_score(ScoreDimension.OWNERSHIP, 50.0),
        ):
            engine.run(strong_candidate, backend_jd)

        # Verify semantic was called with exact_match_details kwarg
        call_kwargs = semantic_mock.call_args.kwargs
        assert "exact_match_details" in call_kwargs
        assert call_kwargs["exact_match_details"] == exact_details


# ------------------------------------------------------------------
# Skill match merging
# ------------------------------------------------------------------

class TestSkillMatchMerging:

    def test_skill_matches_merged_from_both_scorers(
        self, engine, strong_candidate, backend_jd
    ):
        """
        Skill matches from both exact and semantic scorers
        should be combined on the result.
        """
        exact_details = [
            make_skill_detail("Python", "Python", MatchType.EXACT),
        ]
        semantic_details = [
            make_skill_detail("Kafka", "RabbitMQ", MatchType.SEMANTIC),
        ]

        with patch(
            "src.scorer.engine.exact_match_scorer.score",
            return_value=(
                make_dimension_score(ScoreDimension.EXACT_MATCH, 80.0),
                exact_details,
            ),
        ), patch(
            "src.scorer.engine.semantic_similarity_scorer.score",
            return_value=(
                make_dimension_score(ScoreDimension.SEMANTIC_SIMILARITY, 70.0),
                semantic_details,
            ),
        ), patch(
            "src.scorer.engine.achievement_scorer.score",
            return_value=make_dimension_score(ScoreDimension.ACHIEVEMENT, 60.0),
        ), patch(
            "src.scorer.engine.ownership_scorer.score",
            return_value=make_dimension_score(ScoreDimension.OWNERSHIP, 50.0),
        ):
            result = engine.run(strong_candidate, backend_jd)

        assert len(result.skill_matches) == 2
        jd_skills = [m.jd_skill for m in result.skill_matches]
        assert "Python" in jd_skills
        assert "Kafka" in jd_skills


# ------------------------------------------------------------------
# Strengths and gaps derivation
# ------------------------------------------------------------------

class TestStrengthsAndGaps:

    def test_high_scores_produce_strengths(
        self, engine, strong_candidate, backend_jd
    ):
        """Dimensions scoring >= 70 should produce strengths."""
        patches = patch_all_scorers(
            exact_score=90.0,
            semantic_score=85.0,
            achievement_score=80.0,
            ownership_score=75.0,
        )
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert len(result.strengths) > 0

    def test_low_scores_produce_gaps(
        self, engine, weak_candidate, backend_jd
    ):
        """Dimensions scoring < 50 should produce gaps."""
        patches = patch_all_scorers(
            exact_score=20.0,
            semantic_score=15.0,
            achievement_score=10.0,
            ownership_score=12.0,
        )
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(weak_candidate, backend_jd)

        assert len(result.gaps) > 0

    def test_mid_range_scores_produce_neither(
        self, engine, strong_candidate, backend_jd
    ):
        """
        Scores between 50–69 (the neutral band) should produce
        neither strengths nor gaps.
        """
        patches = patch_all_scorers(
            exact_score=60.0,
            semantic_score=65.0,
            achievement_score=55.0,
            ownership_score=58.0,
        )
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.strengths == []
        assert result.gaps == []

    def test_strengths_are_strings(
        self, engine, strong_candidate, backend_jd
    ):
        """All strength entries should be non-empty strings."""
        patches = patch_all_scorers(
            exact_score=90.0,
            semantic_score=85.0,
            achievement_score=80.0,
            ownership_score=75.0,
        )
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        for strength in result.strengths:
            assert isinstance(strength, str)
            assert len(strength) > 0


# ------------------------------------------------------------------
# Score bounds
# ------------------------------------------------------------------

class TestScoreBounds:

    def test_overall_score_never_below_zero(
        self, engine, strong_candidate, backend_jd
    ):
        patches = patch_all_scorers(0.0, 0.0, 0.0, 0.0)
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.overall_score >= 0.0

    def test_overall_score_never_above_100(
        self, engine, strong_candidate, backend_jd
    ):
        patches = patch_all_scorers(100.0, 100.0, 100.0, 100.0)
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert result.overall_score <= 100.0

    def test_overall_score_is_float(
        self, engine, strong_candidate, backend_jd
    ):
        patches = patch_all_scorers()
        with patches["exact"], patches["semantic"], \
             patches["achievement"], patches["ownership"]:
            result = engine.run(strong_candidate, backend_jd)

        assert isinstance(result.overall_score, float)