from enum import Enum

class Tier(str, Enum):
    """Candidate classification after scoring."""
    A = "A"  # Fast-track: overall score >= 80
    B = "B"  # Technical screen: overall score 55–79
    C = "C"  # Needs evaluation: overall score < 55

class MatchType(str, Enum):
    """How a candidate skill was matched against a JD requirement."""
    EXACT = "exact"          # Literal keyword match e.g. "Python" == "Python"
    SEMANTIC = "semantic"    # Functionally equivalent e.g. "Kafka" ~ "RabbitMQ"
    PARTIAL = "partial"      # Related but not equivalent e.g. "SQL" for "PostgreSQL"
    NONE = "none"            # No match found

class SkillLevel(str, Enum):
    """Self-reported or inferred seniority for a given skill."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"

class ScoreDimension(str, Enum):
    """The four scoring axes used by the Scoring Engine."""
    EXACT_MATCH = "exact_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    ACHIEVEMENT = "achievement"
    OWNERSHIP = "ownership"