from pathlib import Path
from src.models import CandidateProfile, CandidateSkill, Experience, Education
from src.models.enums import SkillLevel
from src.llm.client import llm_client
from src.llm.prompts.extract_resume import (
    EXTRACT_RESUME_SYSTEM,
    build_extract_resume_prompt,
)
from src.parser.pdf_parser import pdf_parser


class ResumeExtractor:
    """
    Converts a raw PDF resume into a structured CandidateProfile.

    Pipeline:
        PDF file / bytes
            → PDFParser      (raw text)
            → LLMClient      (structured JSON)
            → CandidateProfile (validated Pydantic model)
    """

    def extract_from_path(self, pdf_path: str | Path) -> CandidateProfile:
        """
        Extract a CandidateProfile from a PDF file path.

        Args:
            pdf_path: Path to the resume PDF.

        Returns:
            Validated CandidateProfile instance.

        Raises:
            FileNotFoundError: If the PDF does not exist.
            ValueError:        If parsing or extraction fails.
        """
        raw_text = pdf_parser.extract_text(pdf_path)
        return self._extract(raw_text)

    def extract_from_bytes(self, pdf_bytes: bytes) -> CandidateProfile:
        """
        Extract a CandidateProfile from raw PDF bytes.

        Args:
            pdf_bytes: Raw bytes of the PDF file.

        Returns:
            Validated CandidateProfile instance.

        Raises:
            ValueError: If parsing or extraction fails.
        """
        raw_text = pdf_parser.extract_text_from_bytes(pdf_bytes)
        return self._extract(raw_text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract(self, raw_text: str) -> CandidateProfile:
        """
        Core extraction logic.
        Sends raw text to Claude and parses the response
        into a validated CandidateProfile.

        Args:
            raw_text: Cleaned plain text from the PDF.

        Returns:
            Validated CandidateProfile.

        Raises:
            ValueError: If Claude returns invalid JSON or
                        the JSON doesn't match the schema.
        """
        prompt = build_extract_resume_prompt(raw_text)

        raw_json = llm_client.complete_json(
            prompt=prompt,
            system=EXTRACT_RESUME_SYSTEM,
        )

        return self._parse_response(raw_json, raw_text)

    def _parse_response(
        self,
        raw_json: dict,
        raw_text: str,
    ) -> CandidateProfile:
        """
        Validate and coerce the raw JSON dict from Claude
        into a CandidateProfile Pydantic model.

        We do manual field-by-field construction instead of
        CandidateProfile(**raw_json) directly to:
        - Handle missing or malformed nested objects gracefully
        - Inject raw_text ourselves (never trust Claude to return it)
        - Provide clear error messages for each field

        Args:
            raw_json: Parsed dict from Claude's JSON response.
            raw_text: Original resume text to inject into the model.

        Returns:
            Validated CandidateProfile instance.
        """
        try:
            skills = self._parse_skills(raw_json.get("skills", []))
            experience = self._parse_experience(raw_json.get("experience", []))
            education = self._parse_education(raw_json.get("education", []))

            return CandidateProfile(
                full_name=raw_json.get("full_name", "Unknown"),
                email=raw_json.get("email"),
                linkedin_url=raw_json.get("linkedin_url"),
                github_url=raw_json.get("github_url"),
                skills=skills,
                experience=experience,
                education=education,
                total_experience_years=raw_json.get("total_experience_years"),
                summary=raw_json.get("summary"),
                raw_text=raw_text,                  # Always injected by us
            )

        except Exception as e:
            raise ValueError(
                f"[ResumeExtractor] Failed to construct CandidateProfile "
                f"from Claude response.\nError: {e}\n"
                f"Raw JSON keys: {list(raw_json.keys())}"
            ) from e

    @staticmethod
    def _parse_skills(skills_data: list) -> list[CandidateSkill]:
        """Parse skills list, skipping malformed entries."""
        skills = []
        for item in skills_data:
            if not isinstance(item, dict):
                continue
            try:
                skills.append(CandidateSkill(
                    name=item.get("name", ""),
                    level=SkillLevel(item.get("level", "unknown")),
                    years=item.get("years"),
                ))
            except Exception:
                continue                             # Skip malformed skill silently
        return skills

    @staticmethod
    def _parse_experience(experience_data: list) -> list[Experience]:
        """Parse experience list, skipping malformed entries."""
        experiences = []
        for item in experience_data:
            if not isinstance(item, dict):
                continue
            try:
                experiences.append(Experience(
                    company=item.get("company", ""),
                    role=item.get("role", ""),
                    duration_months=item.get("duration_months"),
                    description=item.get("description", ""),
                    achievements=item.get("achievements", []),
                    keywords=item.get("keywords", []),
                ))
            except Exception:
                continue                             # Skip malformed entry silently
        return experiences

    @staticmethod
    def _parse_education(education_data: list) -> list[Education]:
        """Parse education list, skipping malformed entries."""
        educations = []
        for item in education_data:
            if not isinstance(item, dict):
                continue
            try:
                educations.append(Education(
                    institution=item.get("institution", ""),
                    degree=item.get("degree"),
                    field=item.get("field"),
                    year=item.get("year"),
                ))
            except Exception:
                continue                             # Skip malformed entry silently
        return educations


# Singleton
resume_extractor = ResumeExtractor()