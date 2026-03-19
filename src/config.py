import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Anthropic ---
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL_NAME: str = "claude-sonnet-4-20250514"
    MAX_TOKENS: int = 4096

    # --- LLM Retry Settings ---
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 2.0        # Base delay, doubles on each retry

    # --- Scoring Weights ---
    # Must sum to 1.0
    WEIGHT_EXACT_MATCH: float = 0.30
    WEIGHT_SEMANTIC_SIMILARITY: float = 0.30
    WEIGHT_ACHIEVEMENT: float = 0.20
    WEIGHT_OWNERSHIP: float = 0.20

    # --- Tier Thresholds ---
    TIER_A_MIN_SCORE: float = 80.0
    TIER_B_MIN_SCORE: float = 55.0

    # --- Parser Settings ---
    MAX_RESUME_CHARS: int = 15000           # Truncate resume text if too long
    MAX_JD_CHARS: int = 5000               # Truncate JD text if too long

    @classmethod
    def validate(cls) -> None:
        """Call this at startup to catch missing config early."""
        if not cls.ANTHROPIC_API_KEY:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file."
            )

        weights_sum = (
            cls.WEIGHT_EXACT_MATCH +
            cls.WEIGHT_SEMANTIC_SIMILARITY +
            cls.WEIGHT_ACHIEVEMENT +
            cls.WEIGHT_OWNERSHIP
        )
        if not abs(weights_sum - 1.0) < 1e-6:
            raise ValueError(
                f"Scoring weights must sum to 1.0, got {weights_sum:.2f}"
            )


# Singleton — import this everywhere
config = Config()
