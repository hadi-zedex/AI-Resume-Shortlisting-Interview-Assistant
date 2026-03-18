from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional
from .enums import SkillLevel


class Experience(BaseModel):
    """A single work experience entry from the resume."""
    company: str
    role: str
    duration_months: Optional[int] = None        # None if dates are unclear
    description: str                              # Raw text about the role
    achievements: list[str] = Field(default_factory=list)  # Quantified wins e.g. "Reduced latency by 40%"
    keywords: list[str] = Field(default_factory=list)      # Skills mentioned in this role


class Education(BaseModel):
    """A single education entry from the resume."""
    institution: str
    degree: Optional[str] = None                 # e.g. "B.Tech"
    field: Optional[str] = None                  # e.g. "CS"
    year: Optional[int] = None                   # Graduation year


class CandidateSkill(BaseModel):
    """A skill extracted from the resume."""
    name: str                                     # e.g. "Kafka"
    level: SkillLevel = SkillLevel.UNKNOWN        # Inferred from context
    years: Optional[float] = None                 # e.g. 2.5 years if mentioned


class CandidateProfile(BaseModel):
    """
    The fully structured representation of a resume.
    Output of the Parser layer and input to the Scoring Layer.
    """
    # Identity
    full_name: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None

    # Core content
    skills: list[CandidateSkill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)

    # Derived / computed fields (extracted by Claude)
    total_experience_years: Optional[float] = None
    summary: Optional[str] = None                # Claude-generated 2-line summary

    # preserving original for debugging
    raw_text: str = ""
