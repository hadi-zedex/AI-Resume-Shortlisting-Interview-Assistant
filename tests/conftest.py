import pytest
from src.models import (
    CandidateProfile,
    CandidateSkill,
    Experience,
    Education,
    JobDescription,
    RequiredSkill,
    ScoringResult,
    DimensionScore,
    SkillMatchDetail,
    TierClassification,
    TierThresholds,
    InterviewPlan,
    InterviewQuestion,
)
from src.models.enums import (
    Tier,
    SkillLevel,
    MatchType,
    ScoreDimension,
)


# ------------------------------------------------------------------
# Candidate fixtures
# ------------------------------------------------------------------

@pytest.fixture
def strong_candidate() -> CandidateProfile:
    """
    A strong candidate with quantified achievements,
    ownership signals, and full skill match.
    Expected to score Tier A.
    """
    return CandidateProfile(
        full_name="Alice Strong",
        email="alice@example.com",
        linkedin_url="https://linkedin.com/in/alice",
        github_url="https://github.com/alice",
        skills=[
            CandidateSkill(name="Python",     level=SkillLevel.ADVANCED, years=5.0),
            CandidateSkill(name="Kafka",       level=SkillLevel.ADVANCED, years=3.0),
            CandidateSkill(name="Docker",      level=SkillLevel.ADVANCED, years=4.0),
            CandidateSkill(name="Kubernetes",  level=SkillLevel.INTERMEDIATE, years=2.0),
            CandidateSkill(name="PostgreSQL",  level=SkillLevel.ADVANCED, years=4.0),
        ],
        experience=[
            Experience(
                company="TechCorp",
                role="Senior Backend Engineer",
                duration_months=24,
                description="Led backend architecture for a high-throughput "
                            "data pipeline processing 1B events/day.",
                achievements=[
                    "Reduced pipeline latency by 40% through Kafka optimisation",
                    "Led a team of 6 engineers to deliver $2M infrastructure project",
                    "Improved system throughput by 3x after architectural redesign",
                ],
                keywords=["Python", "Kafka", "Docker", "Kubernetes"],
            ),
            Experience(
                company="DataFlow Inc",
                role="Backend Engineer",
                duration_months=18,
                description="Designed and owned the migration from monolith "
                            "to microservices architecture.",
                achievements=[
                    "Owned end-to-end migration serving 5M users",
                    "Reduced deployment time from 2 hours to 10 minutes",
                ],
                keywords=["Python", "PostgreSQL", "Docker"],
            ),
        ],
        education=[
            Education(
                institution="MIT",
                degree="Bachelor of Science",
                field="Computer Science",
                year=2018,
            )
        ],
        total_experience_years=3.5,
        summary="Senior backend engineer with strong data pipeline experience.",
        raw_text="Alice Strong... Senior Backend Engineer...",
    )


@pytest.fixture
def weak_candidate() -> CandidateProfile:
    """
    A weak candidate with vague descriptions,
    no achievements, and partial skill match.
    Expected to score Tier C.
    """
    return CandidateProfile(
        full_name="Bob Weak",
        email="bob@example.com",
        linkedin_url=None,
        github_url=None,
        skills=[
            CandidateSkill(name="Python",  level=SkillLevel.BEGINNER, years=1.0),
            CandidateSkill(name="SQL",     level=SkillLevel.BEGINNER, years=1.0),
        ],
        experience=[
            Experience(
                company="SmallCo",
                role="Junior Developer",
                duration_months=12,
                description="Assisted the team with backend tasks. "
                            "Helped with database queries and API work.",
                achievements=[],
                keywords=["Python", "SQL"],
            ),
        ],
        education=[
            Education(
                institution="State University",
                degree="Bachelor of Science",
                field="Information Technology",
                year=2023,
            )
        ],
        total_experience_years=1.0,
        summary="Junior developer with basic Python and SQL experience.",
        raw_text="Bob Weak... Junior Developer...",
    )


@pytest.fixture
def minimal_candidate() -> CandidateProfile:
    """
    A candidate with missing optional fields.
    Used to test parser resilience and graceful handling of None values.
    """
    return CandidateProfile(
        full_name="Unknown",
        email=None,
        linkedin_url=None,
        github_url=None,
        skills=[],
        experience=[],
        education=[],
        total_experience_years=None,
        summary=None,
        raw_text="Very short resume text.",
    )


# ------------------------------------------------------------------
# JD fixtures
# ------------------------------------------------------------------

@pytest.fixture
def backend_jd() -> JobDescription:
    """
    A standard backend engineering JD with clear
    required and preferred skills.
    """
    return JobDescription(
        title="Senior Backend Engineer",
        company="TechCorp",
        required_skills=[
            RequiredSkill(name="Python",    is_mandatory=True,
                          minimum_level=SkillLevel.ADVANCED),
            RequiredSkill(name="Kafka",     is_mandatory=True,
                          minimum_level=SkillLevel.INTERMEDIATE),
            RequiredSkill(name="Docker",    is_mandatory=True,
                          minimum_level=SkillLevel.INTERMEDIATE),
            RequiredSkill(name="PostgreSQL",is_mandatory=True,
                          minimum_level=SkillLevel.INTERMEDIATE),
        ],
        preferred_skills=[
            RequiredSkill(name="Kubernetes",is_mandatory=False,
                          minimum_level=SkillLevel.BEGINNER),
            RequiredSkill(name="Terraform", is_mandatory=False,
                          minimum_level=SkillLevel.BEGINNER),
        ],
        min_experience_years=4.0,
        responsibilities=[
            "Design and own backend microservices",
            "Lead technical decisions for data pipeline",
            "Mentor junior engineers",
        ],
        domain="Data Engineering",
        raw_text="Senior Backend Engineer at TechCorp...",
    )


@pytest.fixture
def minimal_jd() -> JobDescription:
    """
    A JD with no skills listed.
    Used to test edge cases in scorers.
    """
    return JobDescription(
        title="Software Engineer",
        company=None,
        required_skills=[],
        preferred_skills=[],
        min_experience_years=None,
        responsibilities=[],
        domain=None,
        raw_text="Generic software engineer role.",
    )


# ------------------------------------------------------------------
# Scoring fixtures
# ------------------------------------------------------------------

@pytest.fixture
def perfect_scoring_result(strong_candidate, backend_jd) -> ScoringResult:
    """A ScoringResult representing a near-perfect candidate."""
    return ScoringResult(
        candidate_name="Alice Strong",
        jd_title="Senior Backend Engineer",
        exact_match=DimensionScore(
            dimension=ScoreDimension.EXACT_MATCH,
            score=95.0,
            explanation="Matched 4/4 mandatory skills and 1/2 preferred skills.",
            evidence=["[Mandatory] Python — exact match found."],
        ),
        semantic_similarity=DimensionScore(
            dimension=ScoreDimension.SEMANTIC_SIMILARITY,
            score=85.0,
            explanation="Strong semantic alignment across tech stack.",
            evidence=["Kafka → Kafka (exact): Direct match."],
        ),
        achievement=DimensionScore(
            dimension=ScoreDimension.ACHIEVEMENT,
            score=90.0,
            explanation="Multiple strong quantified achievements.",
            evidence=["[STRONG] Quantified Impact: Reduced latency by 40%"],
        ),
        ownership=DimensionScore(
            dimension=ScoreDimension.OWNERSHIP,
            score=88.0,
            explanation="Clear ownership signals throughout.",
            evidence=["[STRONG] Led People: Led a team of 6 engineers"],
        ),
        overall_score=89.9,
        score_breakdown={
            ScoreDimension.EXACT_MATCH:         0.30,
            ScoreDimension.SEMANTIC_SIMILARITY:  0.30,
            ScoreDimension.ACHIEVEMENT:          0.20,
            ScoreDimension.OWNERSHIP:            0.20,
        },
        skill_matches=[
            SkillMatchDetail(
                jd_skill="Python",
                candidate_skill="Python",
                match_type=MatchType.EXACT,
                explanation="Direct match.",
            ),
            SkillMatchDetail(
                jd_skill="Kafka",
                candidate_skill="Kafka",
                match_type=MatchType.EXACT,
                explanation="Direct match.",
            ),
        ],
        strengths=[
            "Strong keyword alignment with JD requirements",
            "Well-demonstrated quantified impact and achievements",
        ],
        gaps=[],
    )


@pytest.fixture
def weak_scoring_result(weak_candidate, backend_jd) -> ScoringResult:
    """A ScoringResult representing a weak candidate."""
    return ScoringResult(
        candidate_name="Bob Weak",
        jd_title="Senior Backend Engineer",
        exact_match=DimensionScore(
            dimension=ScoreDimension.EXACT_MATCH,
            score=20.0,
            explanation="Matched 1/4 mandatory skills.",
            evidence=[],
        ),
        semantic_similarity=DimensionScore(
            dimension=ScoreDimension.SEMANTIC_SIMILARITY,
            score=15.0,
            explanation="Very limited semantic overlap.",
            evidence=[],
        ),
        achievement=DimensionScore(
            dimension=ScoreDimension.ACHIEVEMENT,
            score=10.0,
            explanation="No quantified achievements found.",
            evidence=[],
        ),
        ownership=DimensionScore(
            dimension=ScoreDimension.OWNERSHIP,
            score=12.0,
            explanation="Mostly passive contributor language.",
            evidence=[],
        ),
        overall_score=14.9,
        score_breakdown={
            ScoreDimension.EXACT_MATCH:         0.30,
            ScoreDimension.SEMANTIC_SIMILARITY:  0.30,
            ScoreDimension.ACHIEVEMENT:          0.20,
            ScoreDimension.OWNERSHIP:            0.20,
        },
        skill_matches=[
            SkillMatchDetail(
                jd_skill="Kafka",
                candidate_skill=None,
                match_type=MatchType.NONE,
                explanation="Not found in candidate skill set.",
            ),
        ],
        strengths=[],
        gaps=[
            "Missing key required skills from the JD",
            "Lacks quantified achievements and measurable impact",
        ],
    )


@pytest.fixture
def boundary_a_scoring_result() -> ScoringResult:
    """ScoringResult with overall_score exactly at Tier A boundary (80.0)."""
    dim = DimensionScore(
        dimension=ScoreDimension.EXACT_MATCH,
        score=80.0,
        explanation="Boundary test score.",
        evidence=[],
    )
    return ScoringResult(
        candidate_name="Boundary Candidate",
        jd_title="Test Role",
        exact_match=dim,
        semantic_similarity=DimensionScore(
            dimension=ScoreDimension.SEMANTIC_SIMILARITY,
            score=80.0,
            explanation="Boundary test.",
            evidence=[],
        ),
        achievement=DimensionScore(
            dimension=ScoreDimension.ACHIEVEMENT,
            score=80.0,
            explanation="Boundary test.",
            evidence=[],
        ),
        ownership=DimensionScore(
            dimension=ScoreDimension.OWNERSHIP,
            score=80.0,
            explanation="Boundary test.",
            evidence=[],
        ),
        overall_score=80.0,
        score_breakdown={},
        skill_matches=[],
        strengths=[],
        gaps=[],
    )


@pytest.fixture
def boundary_b_scoring_result() -> ScoringResult:
    """ScoringResult with overall_score exactly at Tier B boundary (55.0)."""
    return ScoringResult(
        candidate_name="Boundary Candidate B",
        jd_title="Test Role",
        exact_match=DimensionScore(
            dimension=ScoreDimension.EXACT_MATCH,
            score=55.0,
            explanation="Boundary test.",
            evidence=[],
        ),
        semantic_similarity=DimensionScore(
            dimension=ScoreDimension.SEMANTIC_SIMILARITY,
            score=55.0,
            explanation="Boundary test.",
            evidence=[],
        ),
        achievement=DimensionScore(
            dimension=ScoreDimension.ACHIEVEMENT,
            score=55.0,
            explanation="Boundary test.",
            evidence=[],
        ),
        ownership=DimensionScore(
            dimension=ScoreDimension.OWNERSHIP,
            score=55.0,
            explanation="Boundary test.",
            evidence=[],
        ),
        overall_score=55.0,
        score_breakdown={},
        skill_matches=[],
        strengths=[],
        gaps=[],
    )