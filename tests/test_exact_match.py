import pytest
from src.models import (
    CandidateProfile,
    JobDescription,
    RequiredSkill,
    CandidateSkill,
)
from src.models.enums import SkillLevel, MatchType
from src.scorer.exact_match import ExactMatchScorer


@pytest.fixture
def scorer() -> ExactMatchScorer:
    return ExactMatchScorer()


# ------------------------------------------------------------------
# Basic matching
# ------------------------------------------------------------------

class TestBasicMatching:

    def test_perfect_match(self, scorer, strong_candidate, backend_jd):
        """All mandatory skills present → high score."""
        dim_score, details = scorer.score(strong_candidate, backend_jd)

        assert dim_score.score > 80.0
        assert dim_score.explanation != ""

    def test_no_match(self, scorer, weak_candidate, backend_jd):
        """Candidate missing most required skills → low score."""
        dim_score, details = scorer.score(weak_candidate, backend_jd)

        assert dim_score.score < 40.0

    def test_empty_candidate_skills(self, scorer, minimal_candidate, backend_jd):
        """Candidate with no skills → zero score, no crash."""
        dim_score, details = scorer.score(minimal_candidate, backend_jd)

        assert dim_score.score == 0.0
        assert dim_score.explanation != ""

    def test_empty_jd_skills(self, scorer, strong_candidate, minimal_jd):
        """JD with no skills → zero score, no crash."""
        dim_score, details = scorer.score(strong_candidate, minimal_jd)

        assert dim_score.score == 0.0
        assert "No skills found" in dim_score.explanation


# ------------------------------------------------------------------
# Case insensitivity
# ------------------------------------------------------------------

class TestCaseInsensitivity:

    def test_case_insensitive_match(self, scorer):
        """'python' in candidate should match 'Python' in JD."""
        candidate = CandidateProfile(
            full_name="Test",
            skills=[CandidateSkill(name="python", level=SkillLevel.ADVANCED)],
            experience=[],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Test Role",
            required_skills=[
                RequiredSkill(name="Python", is_mandatory=True)
            ],
            preferred_skills=[],
            raw_text="",
        )
        dim_score, details = scorer.score(candidate, jd)

        assert dim_score.score == 100.0
        assert details[0].match_type == MatchType.EXACT

    def test_uppercase_candidate_skill(self, scorer):
        """'PYTHON' in candidate should match 'Python' in JD."""
        candidate = CandidateProfile(
            full_name="Test",
            skills=[CandidateSkill(name="PYTHON", level=SkillLevel.ADVANCED)],
            experience=[],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Test Role",
            required_skills=[
                RequiredSkill(name="Python", is_mandatory=True)
            ],
            preferred_skills=[],
            raw_text="",
        )
        dim_score, details = scorer.score(candidate, jd)

        assert dim_score.score == 100.0


# ------------------------------------------------------------------
# Mandatory vs preferred weighting
# ------------------------------------------------------------------

class TestMandatoryVsPreferredWeighting:

    def test_mandatory_skills_weighted_higher(self, scorer):
        """
        Missing a mandatory skill should hurt more than
        missing a preferred skill.
        """
        # Candidate has preferred skill but not mandatory
        candidate_missing_mandatory = CandidateProfile(
            full_name="Test",
            skills=[CandidateSkill(name="Terraform", level=SkillLevel.BEGINNER)],
            experience=[],
            education=[],
            raw_text="",
        )
        # Candidate has mandatory skill but not preferred
        candidate_missing_preferred = CandidateProfile(
            full_name="Test",
            skills=[CandidateSkill(name="Python", level=SkillLevel.ADVANCED)],
            experience=[],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Test Role",
            required_skills=[
                RequiredSkill(name="Python", is_mandatory=True)
            ],
            preferred_skills=[
                RequiredSkill(name="Terraform", is_mandatory=False)
            ],
            raw_text="",
        )

        score_missing_mandatory, _ = scorer.score(
            candidate_missing_mandatory, jd
        )
        score_missing_preferred, _ = scorer.score(
            candidate_missing_preferred, jd
        )

        # Missing mandatory should score lower than missing preferred
        assert score_missing_mandatory.score < score_missing_preferred.score

    def test_only_preferred_skills_in_jd(self, scorer):
        """If JD has only preferred skills, score is based entirely on those."""
        candidate = CandidateProfile(
            full_name="Test",
            skills=[CandidateSkill(name="Terraform", level=SkillLevel.BEGINNER)],
            experience=[],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Test Role",
            required_skills=[],
            preferred_skills=[
                RequiredSkill(name="Terraform", is_mandatory=False),
                RequiredSkill(name="Ansible",   is_mandatory=False),
            ],
            raw_text="",
        )
        dim_score, _ = scorer.score(candidate, jd)

        # 1/2 preferred matched → 50.0
        assert dim_score.score == 50.0


# ------------------------------------------------------------------
# Skill detail records
# ------------------------------------------------------------------

class TestSkillMatchDetails:

    def test_returns_detail_per_jd_skill(self, scorer, strong_candidate, backend_jd):
        """Should return one SkillMatchDetail per JD skill."""
        _, details = scorer.score(strong_candidate, backend_jd)

        total_jd_skills = (
            len(backend_jd.required_skills) +
            len(backend_jd.preferred_skills)
        )
        assert len(details) == total_jd_skills

    def test_matched_skill_has_exact_type(self, scorer, strong_candidate, backend_jd):
        """Matched skills should have MatchType.EXACT."""
        _, details = scorer.score(strong_candidate, backend_jd)

        matched = [d for d in details if d.match_type == MatchType.EXACT]
        assert len(matched) > 0
        for detail in matched:
            assert detail.candidate_skill is not None
            assert detail.explanation != ""

    def test_unmatched_skill_has_none_type(self, scorer, weak_candidate, backend_jd):
        """Unmatched skills should have MatchType.NONE."""
        _, details = scorer.score(weak_candidate, backend_jd)

        unmatched = [d for d in details if d.match_type == MatchType.NONE]
        assert len(unmatched) > 0
        for detail in unmatched:
            assert detail.candidate_skill is None


# ------------------------------------------------------------------
# Keyword extraction from experience
# ------------------------------------------------------------------

class TestKeywordExtraction:

    def test_skills_from_experience_keywords(self, scorer):
        """
        Skills listed only in experience keywords (not top-level skills)
        should still be matched.
        """
        candidate = CandidateProfile(
            full_name="Test",
            skills=[],                              # No top-level skills
            experience=[
                Experience_stub("Python", "Kafka"),  # Skills in keywords only
            ],
            education=[],
            raw_text="",
        )
        jd = JobDescription(
            title="Test Role",
            required_skills=[
                RequiredSkill(name="Python", is_mandatory=True),
                RequiredSkill(name="Kafka",  is_mandatory=True),
            ],
            preferred_skills=[],
            raw_text="",
        )
        dim_score, details = scorer.score(candidate, jd)

        assert dim_score.score == 100.0


# ------------------------------------------------------------------
# Explainability
# ------------------------------------------------------------------

class TestExplainability:

    def test_explanation_mentions_matched_count(
        self, scorer, strong_candidate, backend_jd
    ):
        """Explanation should mention how many skills were matched."""
        dim_score, _ = scorer.score(strong_candidate, backend_jd)

        # Should contain fraction like "4/4" or "3/4"
        assert "/" in dim_score.explanation

    def test_explanation_mentions_missing_skills(
        self, scorer, weak_candidate, backend_jd
    ):
        """Explanation should call out missing mandatory skills."""
        dim_score, _ = scorer.score(weak_candidate, backend_jd)

        assert "Missing" in dim_score.explanation or "missing" in dim_score.explanation

    def test_evidence_only_contains_matched_skills(
        self, scorer, strong_candidate, backend_jd
    ):
        """Evidence list should only contain skills that were matched."""
        dim_score, _ = scorer.score(strong_candidate, backend_jd)

        for item in dim_score.evidence:
            assert "exact match" in item.lower()


# ------------------------------------------------------------------
# Score bounds
# ------------------------------------------------------------------

class TestScoreBounds:

    def test_score_never_exceeds_100(self, scorer, strong_candidate, backend_jd):
        dim_score, _ = scorer.score(strong_candidate, backend_jd)
        assert dim_score.score <= 100.0

    def test_score_never_below_zero(self, scorer, weak_candidate, backend_jd):
        dim_score, _ = scorer.score(weak_candidate, backend_jd)
        assert dim_score.score >= 0.0

    def test_score_is_float(self, scorer, strong_candidate, backend_jd):
        dim_score, _ = scorer.score(strong_candidate, backend_jd)
        assert isinstance(dim_score.score, float)


# ------------------------------------------------------------------
# Helper stub (avoids importing Experience directly in test)
# ------------------------------------------------------------------

from src.models.candidate import Experience

def Experience_stub(*keywords) -> Experience:
    """Create a minimal Experience with given keywords."""
    return Experience(
        company="TestCo",
        role="Engineer",
        duration_months=12,
        description="Test role.",
        achievements=[],
        keywords=list(keywords),
    )
