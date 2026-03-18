from pydantic import BaseModel, Field
from typing import Optional
from .enums import SkillLevel


class RequiredSkill(BaseModel):
    """
    A single skill requirement extracted from the Job Description.
    """
    name: str                                       # e.g. "Kafka"
    is_mandatory: bool = True                       # False = nice-to-have / preferred
    minimum_level: SkillLevel = SkillLevel.UNKNOWN  # Expected proficiency
    minimum_years: Optional[float] = None           # e.g. 2.0 years if specified


class JobDescription(BaseModel):
    """
    The fully structured representation of a Job Description.
    Input to the Scoring Layer.
    """
    # Identity
    title: str                                      # e.g. "Senior Backend Engineer"
    company: Optional[str] = None

    # Requirements
    required_skills: list[RequiredSkill] = Field(default_factory=list)
    preferred_skills: list[RequiredSkill] = Field(default_factory=list)
    min_experience_years: Optional[float] = None

    # Context
    responsibilities: list[str] = Field(default_factory=list)  # Key role duties
    domain: Optional[str] = None                   # e.g. "FinTech", "Healthcare"

    # preserving original for debugging
    raw_text: str = ""
