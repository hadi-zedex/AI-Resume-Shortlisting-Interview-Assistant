import pytest
from unittest.mock import patch
from src.models import (
    CandidateProfile,
    JobDescription,
    DimensionScore,
    SkillMatchDetail,
    CandidateSkill,
    RequiredSkill,
)
from src.models.enums import ScoreDimension, MatchType, SkillLevel
from src.scorer.semantic_similarity import SemanticSimilarityScorer


@pytest.fixture
def scorer() -> SemanticSimilarityScorer:
    return SemanticSimilarityScorer()


# ------------------------------------------------------------------
# Mock response builders
# ------------------------------------------------------------------

def make_semantic_response(
    matches: list[dict] | None = None,
    overall_summary: str = "Good semantic alignment across the tech stack.",
) -> dict:
    """
    Build a fake Claude semantic similarity response dict.
    Used to mock llm_client.complete_json.
    """
    return {
        "matches": matches or [
            {
                "jd_skill": "Kafka",
                "candidate_skill": "RabbitMQ",
                "match_type": "semantic",
                "score_0_to_100": 75,
                "explanation": "RabbitMQ is functionally similar to Kafka "
                               "for most messaging use cases.",
            }
        ],
        "overall_summary": overall_summary,
    }


# ------------------------------------------------------------------
# Core semantic matching
# ------------------------------------------------------------------

class TestCoreSemanticMatching:

    def test_returns_dimension_score_and_details(
        self, scorer, strong_candidate, backend_jd
    ):
        """score() should return a tuple of DimensionScore and list."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(),
        ):
            dim_score, details = scorer.score(strong_candidate, backend_jd)

        assert isinstance(dim_score, DimensionScore)
        assert isinstance(details, list)
        assert dim_score.dimension == ScoreDimension.SEMANTIC_SIMILARITY

    def test_kafka_matches_rabbitmq_semantically(self, scorer):
        """
        The key use case: 'Kafka' in JD should semantically
        match 'RabbitMQ' in candidate skills.
        """
        candidate = CandidateProfile(
            full_name="Test",
            skills=[
                CandidateSkill(name="RabbitMQ", level=SkillLevel.ADVANCED),
            ],
            experience=[],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Backend Engineer",
            required_skills=[
                RequiredSkill(name="Kafka", is_mandatory=True),
            ],
            preferred_skills=[],
            raw_text="",
        )

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "Kafka",
                        "candidate_skill": "RabbitMQ",
                        "match_type": "semantic",
                        "score_0_to_100": 75,
                        "explanation": "RabbitMQ is functionally equivalent "
                                       "to Kafka for most messaging use cases.",
                    }
                ],
                overall_summary="Strong semantic match via RabbitMQ.",
            ),
        ):
            dim_score, details = scorer.score(candidate, jd)

        assert dim_score.score > 0
        assert len(details) == 1
        assert details[0].match_type == MatchType.SEMANTIC
        assert details[0].candidate_skill == "RabbitMQ"

    def test_aws_kinesis_matches_kafka_semantically(self, scorer):
        """
        'AWS Kinesis' in candidate should semantically match
        'Kafka' in JD — a common real-world equivalence.
        """
        candidate = CandidateProfile(
            full_name="Test",
            skills=[
                CandidateSkill(name="AWS Kinesis", level=SkillLevel.INTERMEDIATE),
            ],
            experience=[],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Data Engineer",
            required_skills=[
                RequiredSkill(name="Kafka", is_mandatory=True),
            ],
            preferred_skills=[],
            domain="Data Engineering",
            raw_text="",
        )

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "Kafka",
                        "candidate_skill": "AWS Kinesis",
                        "match_type": "semantic",
                        "score_0_to_100": 70,
                        "explanation": "AWS Kinesis is a managed streaming "
                                       "service similar to Kafka.",
                    }
                ],
            ),
        ):
            dim_score, details = scorer.score(candidate, jd)

        assert details[0].match_type == MatchType.SEMANTIC
        assert details[0].candidate_skill == "AWS Kinesis"
        assert dim_score.score > 0

    def test_unrelated_skill_gets_none_match(self, scorer):
        """Completely unrelated skill should get MatchType.NONE."""
        candidate = CandidateProfile(
            full_name="Test",
            skills=[
                CandidateSkill(name="Photoshop", level=SkillLevel.ADVANCED),
            ],
            experience=[],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Backend Engineer",
            required_skills=[
                RequiredSkill(name="Kafka", is_mandatory=True),
            ],
            preferred_skills=[],
            raw_text="",
        )

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "Kafka",
                        "candidate_skill": None,
                        "match_type": "none",
                        "score_0_to_100": 0,
                        "explanation": "No relevant match found.",
                    }
                ],
            ),
        ):
            dim_score, details = scorer.score(candidate, jd)

        assert details[0].match_type == MatchType.NONE
        assert details[0].candidate_skill is None
        assert dim_score.score == 0.0

    def test_partial_match_detected(self, scorer):
        """'SQL' should partially match 'PostgreSQL'."""
        candidate = CandidateProfile(
            full_name="Test",
            skills=[
                CandidateSkill(name="SQL", level=SkillLevel.INTERMEDIATE),
            ],
            experience=[],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Backend Engineer",
            required_skills=[
                RequiredSkill(name="PostgreSQL", is_mandatory=True),
            ],
            preferred_skills=[],
            raw_text="",
        )

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "PostgreSQL",
                        "candidate_skill": "SQL",
                        "match_type": "partial",
                        "score_0_to_100": 45,
                        "explanation": "SQL is related but not specific "
                                       "to PostgreSQL.",
                    }
                ],
            ),
        ):
            dim_score, details = scorer.score(candidate, jd)

        assert details[0].match_type == MatchType.PARTIAL
        assert 0 < dim_score.score < 60


# ------------------------------------------------------------------
# Already-matched skill filtering
# ------------------------------------------------------------------

class TestAlreadyMatchedFiltering:

    def test_exact_matched_skills_not_re_evaluated(
        self, scorer, strong_candidate, backend_jd
    ):
        """
        Skills already exactly matched should not be sent
        to Claude for semantic evaluation.
        LLM should not be called if all skills are already matched.
        """
        # All JD skills already exactly matched
        already_matched = [
            SkillMatchDetail(
                jd_skill=skill.name,
                candidate_skill=skill.name,
                match_type=MatchType.EXACT,
                explanation="Already matched.",
            )
            for skill in (
                backend_jd.required_skills + backend_jd.preferred_skills
            )
        ]

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json"
        ) as mock_llm:
            dim_score, details = scorer.score(
                strong_candidate,
                backend_jd,
                exact_match_details=already_matched,
            )

            # LLM should NOT be called — everything already matched
            mock_llm.assert_not_called()

        assert dim_score.score == 100.0

    def test_partially_matched_skills_still_evaluated(
        self, scorer, strong_candidate, backend_jd
    ):
        """
        Skills not in exact match details should still be
        sent to Claude for semantic evaluation.
        """
        # Only Python is exactly matched
        partial_exact = [
            SkillMatchDetail(
                jd_skill="Python",
                candidate_skill="Python",
                match_type=MatchType.EXACT,
                explanation="Direct match.",
            )
        ]

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(),
        ) as mock_llm:
            scorer.score(
                strong_candidate,
                backend_jd,
                exact_match_details=partial_exact,
            )

            # LLM should be called for the remaining skills
            mock_llm.assert_called_once()

    def test_none_exact_details_evaluates_all_skills(
        self, scorer, strong_candidate, backend_jd
    ):
        """
        When exact_match_details is None, all JD skills
        should be evaluated semantically.
        """
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(),
        ) as mock_llm:
            scorer.score(
                strong_candidate,
                backend_jd,
                exact_match_details=None,
            )

            mock_llm.assert_called_once()

    def test_perfect_score_when_all_exact_matched(
        self, scorer, strong_candidate, backend_jd
    ):
        """
        If all skills were exactly matched, semantic score
        should be 100.0 with a clear explanation.
        """
        all_matched = [
            SkillMatchDetail(
                jd_skill=s.name,
                candidate_skill=s.name,
                match_type=MatchType.EXACT,
                explanation="Exact.",
            )
            for s in backend_jd.required_skills + backend_jd.preferred_skills
        ]

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json"
        ):
            dim_score, _ = scorer.score(
                strong_candidate,
                backend_jd,
                exact_match_details=all_matched,
            )

        assert dim_score.score == 100.0
        assert "exactly" in dim_score.explanation.lower() or \
               "already" in dim_score.explanation.lower()


# ------------------------------------------------------------------
# Empty candidate skills
# ------------------------------------------------------------------

class TestEmptyCandidateSkills:

    def test_no_candidate_skills_returns_zero(
        self, scorer, minimal_candidate, backend_jd
    ):
        """
        Candidate with no skills should return zero score
        without calling the LLM.
        """
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json"
        ) as mock_llm:
            dim_score, details = scorer.score(
                minimal_candidate, backend_jd
            )

            mock_llm.assert_not_called()

        assert dim_score.score == 0.0

    def test_empty_jd_skills_returns_perfect_score(
        self, scorer, strong_candidate, minimal_jd
    ):
        """
        JD with no skills means nothing to evaluate —
        all skills are trivially matched → perfect score.
        """
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json"
        ) as mock_llm:
            dim_score, details = scorer.score(
                strong_candidate, minimal_jd
            )

            mock_llm.assert_not_called()

        assert dim_score.score == 100.0


# ------------------------------------------------------------------
# Mandatory skill weighting
# ------------------------------------------------------------------

class TestMandatorySkillWeighting:

    def test_mandatory_skills_weighted_higher(self, scorer):
        """
        A semantic match on a mandatory skill should contribute
        more to the score than one on a preferred skill.
        """
        # JD with one mandatory and one preferred skill
        jd = JobDescription(
            title="Test Role",
            required_skills=[
                RequiredSkill(name="Kafka", is_mandatory=True),
            ],
            preferred_skills=[
                RequiredSkill(name="Terraform", is_mandatory=False),
            ],
            raw_text="",
        )

        # Candidate only has RabbitMQ (semantic for Kafka)
        candidate_mandatory_match = CandidateProfile(
            full_name="Test",
            skills=[CandidateSkill(name="RabbitMQ", level=SkillLevel.ADVANCED)],
            experience=[],
            education=[],
            raw_text="",
        )

        # Candidate only has Ansible (semantic for Terraform)
        candidate_preferred_match = CandidateProfile(
            full_name="Test",
            skills=[CandidateSkill(name="Ansible", level=SkillLevel.ADVANCED)],
            experience=[],
            education=[],
            raw_text="",
        )

        mandatory_response = make_semantic_response(
            matches=[
                {
                    "jd_skill": "Kafka",
                    "candidate_skill": "RabbitMQ",
                    "match_type": "semantic",
                    "score_0_to_100": 70,
                    "explanation": "Semantic match.",
                },
                {
                    "jd_skill": "Terraform",
                    "candidate_skill": None,
                    "match_type": "none",
                    "score_0_to_100": 0,
                    "explanation": "No match.",
                },
            ]
        )

        preferred_response = make_semantic_response(
            matches=[
                {
                    "jd_skill": "Kafka",
                    "candidate_skill": None,
                    "match_type": "none",
                    "score_0_to_100": 0,
                    "explanation": "No match.",
                },
                {
                    "jd_skill": "Terraform",
                    "candidate_skill": "Ansible",
                    "match_type": "semantic",
                    "score_0_to_100": 70,
                    "explanation": "Semantic match.",
                },
            ]
        )

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=mandatory_response,
        ):
            mandatory_score, _ = scorer.score(candidate_mandatory_match, jd)

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=preferred_response,
        ):
            preferred_score, _ = scorer.score(candidate_preferred_match, jd)

        # Matching a mandatory skill should score higher
        assert mandatory_score.score > preferred_score.score


# ------------------------------------------------------------------
# Explainability
# ------------------------------------------------------------------

class TestExplainability:

    def test_explanation_from_overall_summary(self, scorer, strong_candidate, backend_jd):
        """overall_summary from Claude should become the explanation."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                overall_summary="Strong semantic alignment via RabbitMQ and Kinesis."
            ),
        ):
            dim_score, _ = scorer.score(strong_candidate, backend_jd)

        assert "RabbitMQ" in dim_score.explanation or \
               "semantic" in dim_score.explanation.lower()

    def test_fallback_explanation_when_summary_empty(
        self, scorer, strong_candidate, backend_jd
    ):
        """
        When overall_summary is empty, fallback explanation
        should be generated from match counts.
        """
        response = make_semantic_response(overall_summary="")
        response["matches"] = [
            {
                "jd_skill": "Kafka",
                "candidate_skill": "RabbitMQ",
                "match_type": "semantic",
                "score_0_to_100": 70,
                "explanation": "Semantic.",
            },
            {
                "jd_skill": "Terraform",
                "candidate_skill": None,
                "match_type": "none",
                "score_0_to_100": 0,
                "explanation": "No match.",
            },
        ]

        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=response,
        ):
            dim_score, _ = scorer.score(strong_candidate, backend_jd)

        assert dim_score.explanation != ""
        assert "match" in dim_score.explanation.lower()

    def test_evidence_contains_semantic_matches(
        self, scorer, strong_candidate, backend_jd
    ):
        """Evidence should contain entries for non-zero matches."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "Kafka",
                        "candidate_skill": "RabbitMQ",
                        "match_type": "semantic",
                        "score_0_to_100": 75,
                        "explanation": "RabbitMQ is similar to Kafka.",
                    }
                ]
            ),
        ):
            dim_score, _ = scorer.score(strong_candidate, backend_jd)

        assert len(dim_score.evidence) > 0
        assert any("RabbitMQ" in e for e in dim_score.evidence)

    def test_zero_score_matches_excluded_from_evidence(
        self, scorer, strong_candidate, backend_jd
    ):
        """Skills with score 0 should not appear in evidence."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "Terraform",
                        "candidate_skill": None,
                        "match_type": "none",
                        "score_0_to_100": 0,
                        "explanation": "No match found.",
                    }
                ]
            ),
        ):
            dim_score, _ = scorer.score(strong_candidate, backend_jd)

        assert dim_score.evidence == []


# ------------------------------------------------------------------
# Score bounds and type safety
# ------------------------------------------------------------------

class TestScoreBoundsAndSafety:

    def test_score_never_exceeds_100(
        self, scorer, strong_candidate, backend_jd
    ):
        """Score should always be clamped to 100."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "Kafka",
                        "candidate_skill": "Kafka",
                        "match_type": "exact",
                        "score_0_to_100": 150,
                        "explanation": "Over-scored.",
                    }
                ]
            ),
        ):
            dim_score, _ = scorer.score(strong_candidate, backend_jd)

        assert dim_score.score <= 100.0

    def test_score_never_below_zero(
        self, scorer, strong_candidate, backend_jd
    ):
        """Score should always be clamped to 0."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "Kafka",
                        "candidate_skill": None,
                        "match_type": "none",
                        "score_0_to_100": -10,
                        "explanation": "Negative score.",
                    }
                ]
            ),
        ):
            dim_score, _ = scorer.score(strong_candidate, backend_jd)

        assert dim_score.score >= 0.0

    def test_unknown_match_type_defaults_to_none(
        self, scorer, strong_candidate, backend_jd
    ):
        """Unknown match_type string should default to MatchType.NONE."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value=make_semantic_response(
                matches=[
                    {
                        "jd_skill": "Kafka",
                        "candidate_skill": "Something",
                        "match_type": "fuzzy_match",  # Unknown type
                        "score_0_to_100": 50,
                        "explanation": "Unknown match type.",
                    }
                ]
            ),
        ):
            _, details = scorer.score(strong_candidate, backend_jd)

        assert details[0].match_type == MatchType.NONE

    def test_malformed_match_entries_skipped(
        self, scorer, strong_candidate, backend_jd
    ):
        """Malformed match entries should be skipped without crashing."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value={
                "matches": [
                    None,
                    "not a dict",
                    {
                        "jd_skill": "Kafka",
                        "candidate_skill": "RabbitMQ",
                        "match_type": "semantic",
                        "score_0_to_100": 70,
                        "explanation": "Valid entry.",
                    },
                ],
                "overall_summary": "Mixed entries.",
            },
        ):
            dim_score, details = scorer.score(strong_candidate, backend_jd)

        assert len(details) == 1
        assert details[0].jd_skill == "Kafka"

    def test_empty_matches_list_gives_zero_score(
        self, scorer, strong_candidate, backend_jd
    ):
        """Empty matches list should give zero score."""
        with patch(
            "src.scorer.semantic_similarity.llm_client.complete_json",
            return_value={"matches": [], "overall_summary": ""},
        ):
            dim_score, details = scorer.score(strong_candidate, backend_jd)

        assert dim_score.score == 0.0
        assert details == []