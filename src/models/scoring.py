from pydantic import BaseModel, Field
from typing import Optional
from .enums import ScoreDimension, MatchType


class SkillMatchDetail(BaseModel):
    """
    How a single JD skill requirement was matched
    against the candidate's skills.
    """
    jd_skill: str                                   # What the JD asked for e.g. "Kafka"
    candidate_skill: Optional[str] = None           # What the candidate had e.g. "RabbitMQ"
    match_type: MatchType = MatchType.NONE          # exact / semantic / partial / none
    explanation: Optional[str] = None               # e.g. "RabbitMQ is functionally similar to Kafka"


class DimensionScore(BaseModel):
    """
    Score for a single dimension of the evaluation.
    """
    dimension: ScoreDimension
    score: float = Field(ge=0.0, le=100.0)          # Constrained 0–100
    explanation: str                                 # Why this score was given
    evidence: list[str] = Field(default_factory=list)  # Specific quotes/examples from resume


class ScoringResult(BaseModel):
    """
    The complete output of the Scoring Engine.
    Contains all 4 dimension scores and the final weighted overall score.
    """
    candidate_name: str
    jd_title: str

    # The 4 dimensions
    exact_match: DimensionScore
    semantic_similarity: DimensionScore
    achievement: DimensionScore
    ownership: DimensionScore

    # Aggregated
    overall_score: float = Field(ge=0.0, le=100.0)  # Weighted average of the 4 dimensions
    score_breakdown: dict[ScoreDimension, float] = Field(default_factory=dict)  # weights used

    # Skill-level detail for explainability
    skill_matches: list[SkillMatchDetail] = Field(default_factory=list)

    # Top-level summary for the output / UI
    strengths: list[str] = Field(default_factory=list)     # e.g. "Strong systems design background"
    gaps: list[str] = Field(default_factory=list)          # e.g. "No Kubernetes experience"
