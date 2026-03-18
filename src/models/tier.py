from pydantic import BaseModel, Field
from .enums import Tier
from .scoring import ScoringResult


class TierThresholds(BaseModel):
    """
    Configurable score thresholds for tier classification.
    Kept as a model so thresholds can be adjusted per role/company
    without touching business logic.
    """
    tier_a_min: float = 80.0    # >= 80 → Tier A (Fast-track)
    tier_b_min: float = 55.0    # >= 55 → Tier B (Technical Screen)
                                # <  55 → Tier C (Needs Evaluation)


class TierClassification(BaseModel):
    """
    The final output of the Tier classifier layer.
    Wraps the ScoringResult with a tier decision and human-readable reasoning.
    """
    # The tier decision
    tier: Tier
    overall_score: float = Field(ge=0.0, le=100.0)

    # Human-readable output
    decision_label: str         # e.g. "Fast-track to final round"
    reasoning: str              # e.g. "Strong exact match on all core skills,
                                #        demonstrated ownership in 2 roles"

    # What to do next
    recommended_action: str     # e.g. "Schedule system design interview within 48hrs"
    focus_areas: list[str] = Field(default_factory=list)  # What to probe in the interview
                                # e.g. ["Verify Kafka depth", "Clarify team size led"]

    # Thresholds used — stored for auditability
    thresholds_used: TierThresholds = Field(default_factory=TierThresholds)

    # Link back to the full scoring result
    scoring_result: ScoringResult


# --- Classification labels per tier ---

TIER_LABELS: dict[Tier, dict[str, str]] = {
    Tier.A: {
        "decision_label": "Fast-track to final round",
        "recommended_action": "Schedule system design interview within 48 hours",
    },
    Tier.B: {
        "decision_label": "Proceed to technical screen",
        "recommended_action": "Schedule a 45-minute technical phone screen",
    },
    Tier.C: {
        "decision_label": "Needs further evaluation",
        "recommended_action": "Hold — review manually or send a skills assessment",
    },
}