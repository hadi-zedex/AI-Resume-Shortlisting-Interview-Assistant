from src.models import JobDescription, RequiredSkill
from src.models.enums import SkillLevel
from src.llm.client import llm_client
from src.llm.prompts.extract_jd import (
    EXTRACT_JD_SYSTEM,
    build_extract_jd_prompt,
)
from src.config import config


class JDExtractor:
    """
    Converts raw job description text into a structured JobDescription.

    Pipeline:
        Raw JD text
            → LLMClient        (structured JSON)
            → JobDescription   (validated Pydantic model)

    Note: No PDF parsing needed here — JDs are typically
    provided as plain text or copy-pasted from a job portal.
    """

    def extract(self, raw_text: str) -> JobDescription:
        """
        Extract a JobDescription from raw text.

        Args:
            raw_text: Plain text of the job description.

        Returns:
            Validated JobDescription instance.

        Raises:
            ValueError: If extraction or validation fails.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError(
                "[JDExtractor] Job description text is empty."
            )

        truncated = self._truncate(raw_text)
        return self._extract(truncated)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract(self, raw_text: str) -> JobDescription:
        """
        Core extraction logic.
        Sends raw JD text to Claude and parses the response
        into a validated JobDescription.

        Args:
            raw_text: Cleaned plain text of the job description.

        Returns:
            Validated JobDescription instance.

        Raises:
            ValueError: If Claude returns invalid JSON or
                        the JSON doesn't match the schema.
        """
        prompt = build_extract_jd_prompt(raw_text)

        raw_json = llm_client.complete_json(
            prompt=prompt,
            system=EXTRACT_JD_SYSTEM,
        )

        return self._parse_response(raw_json, raw_text)

    def _parse_response(
        self,
        raw_json: dict,
        raw_text: str,
    ) -> JobDescription:
        """
        Validate and coerce the raw JSON dict from Claude
        into a JobDescription Pydantic model.

        Args:
            raw_json: Parsed dict from Claude's JSON response.
            raw_text: Original JD text to inject into the model.

        Returns:
            Validated JobDescription instance.
        """
        try:
            required_skills = self._parse_skills(
                raw_json.get("required_skills", []),
                is_mandatory=True,
            )
            preferred_skills = self._parse_skills(
                raw_json.get("preferred_skills", []),
                is_mandatory=False,
            )
            responsibilities = self._parse_responsibilities(
                raw_json.get("responsibilities", [])
            )

            return JobDescription(
                title=raw_json.get("title", "Unknown Role"),
                company=raw_json.get("company"),
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                min_experience_years=raw_json.get("min_experience_years"),
                responsibilities=responsibilities,
                domain=raw_json.get("domain"),
                raw_text=raw_text,                  # Always injected by us
            )

        except Exception as e:
            raise ValueError(
                f"[JDExtractor] Failed to construct JobDescription "
                f"from Claude response.\nError: {e}\n"
                f"Raw JSON keys: {list(raw_json.keys())}"
            ) from e

    @staticmethod
    def _parse_skills(
        skills_data: list,
        is_mandatory: bool,
    ) -> list[RequiredSkill]:
        """
        Parse a skills list from Claude's response.
        Enforces is_mandatory based on which list the skill came from,
        not what Claude returned — Claude can be inconsistent here.

        Args:
            skills_data:  Raw list of skill dicts from Claude.
            is_mandatory: True for required_skills, False for preferred_skills.

        Returns:
            List of validated RequiredSkill instances.
        """
        skills = []
        for item in skills_data:
            if not isinstance(item, dict):
                continue
            try:
                skills.append(RequiredSkill(
                    name=item.get("name", ""),
                    is_mandatory=is_mandatory,      # We enforce this, not Claude
                    minimum_level=SkillLevel(
                        item.get("minimum_level", "unknown")
                    ),
                    minimum_years=item.get("minimum_years"),
                ))
            except Exception:
                continue                             # Skip malformed skill silently
        return skills

    @staticmethod
    def _parse_responsibilities(responsibilities_data: list) -> list[str]:
        """
        Parse responsibilities list.
        Filters out empty strings and non-string entries.

        Args:
            responsibilities_data: Raw list from Claude.

        Returns:
            Clean list of responsibility strings.
        """
        return [
            item.strip()
            for item in responsibilities_data
            if isinstance(item, str) and item.strip()
        ]

    @staticmethod
    def _truncate(text: str) -> str:
        """
        Truncate JD text to MAX_JD_CHARS to avoid hitting token limits.
        Truncates at a newline boundary to avoid cutting mid-sentence.
        """
        limit = config.MAX_JD_CHARS

        if len(text) <= limit:
            return text

        truncated = text[:limit]

        last_newline = truncated.rfind("\n")
        if last_newline > limit * 0.8:
            truncated = truncated[:last_newline]

        print(
            f"[JDExtractor] JD truncated from {len(text)} "
            f"to {len(truncated)} characters."
        )

        return truncated.strip()


# Singleton
jd_extractor = JDExtractor()