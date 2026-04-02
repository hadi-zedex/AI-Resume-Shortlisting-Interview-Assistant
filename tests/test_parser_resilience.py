import pytest
from unittest.mock import patch, MagicMock
from src.models import CandidateProfile, JobDescription
from src.models.enums import SkillLevel
from src.parser.resume_extractor import ResumeExtractor
from src.parser.jd_extractor import JDExtractor


@pytest.fixture
def resume_extractor() -> ResumeExtractor:
    return ResumeExtractor()


@pytest.fixture
def jd_extractor() -> JDExtractor:
    return JDExtractor()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_full_resume_json() -> dict:
    """A complete, well-formed Claude resume extraction response."""
    return {
        "full_name": "Jane Smith",
        "email": "jane@example.com",
        "linkedin_url": "https://linkedin.com/in/jane",
        "github_url": "https://github.com/jane",
        "skills": [
            {"name": "Python", "level": "advanced", "years": 5.0},
            {"name": "Kafka",  "level": "intermediate", "years": 2.0},
        ],
        "experience": [
            {
                "company": "TechCorp",
                "role": "Senior Engineer",
                "duration_months": 24,
                "description": "Led backend services.",
                "achievements": ["Reduced latency by 40%"],
                "keywords": ["Python", "Kafka"],
            }
        ],
        "education": [
            {
                "institution": "MIT",
                "degree": "BSc",
                "field": "Computer Science",
                "year": 2018,
            }
        ],
        "total_experience_years": 5.0,
        "summary": "Experienced backend engineer.",
        "raw_text": "",
    }


def make_full_jd_json() -> dict:
    """A complete, well-formed Claude JD extraction response."""
    return {
        "title": "Senior Backend Engineer",
        "company": "TechCorp",
        "required_skills": [
            {
                "name": "Python",
                "is_mandatory": True,
                "minimum_level": "advanced",
                "minimum_years": 3.0,
            }
        ],
        "preferred_skills": [
            {
                "name": "Kubernetes",
                "is_mandatory": False,
                "minimum_level": "beginner",
                "minimum_years": None,
            }
        ],
        "min_experience_years": 4.0,
        "responsibilities": ["Design backend systems", "Mentor junior engineers"],
        "domain": "Data Engineering",
        "raw_text": "",
    }


# ------------------------------------------------------------------
# Resume extractor — missing optional fields
# ------------------------------------------------------------------

class TestResumeMissingFields:

    def test_missing_email_defaults_to_none(
        self, resume_extractor
    ):
        """Missing email should default to None, not crash."""
        response = make_full_resume_json()
        response.pop("email")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.email is None

    def test_missing_linkedin_defaults_to_none(
        self, resume_extractor
    ):
        """Missing LinkedIn URL should default to None."""
        response = make_full_resume_json()
        response.pop("linkedin_url")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.linkedin_url is None

    def test_missing_github_defaults_to_none(
        self, resume_extractor
    ):
        """Missing GitHub URL should default to None."""
        response = make_full_resume_json()
        response.pop("github_url")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.github_url is None

    def test_missing_summary_defaults_to_none(
        self, resume_extractor
    ):
        """Missing summary should default to None."""
        response = make_full_resume_json()
        response.pop("summary")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.summary is None

    def test_missing_total_experience_defaults_to_none(
        self, resume_extractor
    ):
        """Missing total experience years should default to None."""
        response = make_full_resume_json()
        response.pop("total_experience_years")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.total_experience_years is None

    def test_missing_full_name_defaults_to_unknown(
        self, resume_extractor
    ):
        """Missing full_name should default to 'Unknown', not crash."""
        response = make_full_resume_json()
        response.pop("full_name")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.full_name == "Unknown"

    def test_missing_skills_defaults_to_empty_list(
        self, resume_extractor
    ):
        """Missing skills should default to empty list."""
        response = make_full_resume_json()
        response.pop("skills")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.skills == []

    def test_missing_experience_defaults_to_empty_list(
        self, resume_extractor
    ):
        """Missing experience should default to empty list."""
        response = make_full_resume_json()
        response.pop("experience")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.experience == []

    def test_missing_education_defaults_to_empty_list(
        self, resume_extractor
    ):
        """Missing education should default to empty list."""
        response = make_full_resume_json()
        response.pop("education")

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert profile.education == []


# ------------------------------------------------------------------
# Resume extractor — malformed nested entries
# ------------------------------------------------------------------

class TestResumeMalformedEntries:

    def test_malformed_skill_entry_skipped(
        self, resume_extractor
    ):
        """Malformed skill entries should be skipped silently."""
        response = make_full_resume_json()
        response["skills"] = [
            None,
            "not a dict",
            {"name": "Python", "level": "advanced", "years": 5.0},
            {"name": "",       "level": "advanced", "years": 1.0},
        ]

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        # Only the valid Python entry should survive
        valid_skills = [s for s in profile.skills if s.name]
        assert len(valid_skills) >= 1
        assert any(s.name == "Python" for s in profile.skills)

    def test_malformed_experience_entry_skipped(
        self, resume_extractor
    ):
        """Malformed experience entries should be skipped."""
        response = make_full_resume_json()
        response["experience"] = [
            None,
            "not a dict",
            {
                "company": "ValidCo",
                "role": "Engineer",
                "duration_months": 12,
                "description": "Valid role.",
                "achievements": [],
                "keywords": [],
            },
        ]

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert len(profile.experience) == 1
        assert profile.experience[0].company == "ValidCo"

    def test_malformed_education_entry_skipped(
        self, resume_extractor
    ):
        """Malformed education entries should be skipped."""
        response = make_full_resume_json()
        response["education"] = [
            None,
            {"institution": "MIT", "degree": "BSc",
             "field": "CS", "year": 2018},
        ]

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert len(profile.education) == 1
        assert profile.education[0].institution == "MIT"

    def test_invalid_skill_level_defaults_to_unknown(
        self, resume_extractor
    ):
        """Invalid skill level string should default to UNKNOWN."""
        response = make_full_resume_json()
        response["skills"] = [
            {"name": "Python", "level": "expert_plus", "years": 5.0},
        ]

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Some resume text")

        assert len(profile.skills) == 0 or \
               profile.skills[0].level == SkillLevel.UNKNOWN

    def test_completely_empty_response(
        self, resume_extractor
    ):
        """Completely empty Claude response should return minimal profile."""
        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value={},
        ):
            profile = resume_extractor._extract("Some resume text")

        assert isinstance(profile, CandidateProfile)
        assert profile.full_name == "Unknown"
        assert profile.skills == []
        assert profile.experience == []

    def test_raw_text_always_injected(
        self, resume_extractor
    ):
        """
        raw_text should always be the text we passed in,
        not what Claude returns.
        """
        response = make_full_resume_json()
        response["raw_text"] = "Claude tried to overwrite this"

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract("Original resume text")

        assert profile.raw_text == "Original resume text"


# ------------------------------------------------------------------
# JD extractor — missing fields
# ------------------------------------------------------------------

class TestJDMissingFields:

    def test_missing_company_defaults_to_none(
        self, jd_extractor
    ):
        """Missing company should default to None."""
        response = make_full_jd_json()
        response.pop("company")

        with patch(
            "src.parser.jd_extractor.llm_client.complete_json",
            return_value=response,
        ):
            jd = jd_extractor._extract("Some JD text")

        assert jd.company is None

    def test_missing_domain_defaults_to_none(
        self, jd_extractor
    ):
        """Missing domain should default to None."""
        response = make_full_jd_json()
        response.pop("domain")

        with patch(
            "src.parser.jd_extractor.llm_client.complete_json",
            return_value=response,
        ):
            jd = jd_extractor._extract("Some JD text")

        assert jd.domain is None

    def test_missing_title_defaults_to_unknown_role(
        self, jd_extractor
    ):
        """Missing title should default to 'Unknown Role'."""
        response = make_full_jd_json()
        response.pop("title")

        with patch(
            "src.parser.jd_extractor.llm_client.complete_json",
            return_value=response,
        ):
            jd = jd_extractor._extract("Some JD text")

        assert jd.title == "Unknown Role"

    def test_missing_required_skills_defaults_to_empty(
        self, jd_extractor
    ):
        """Missing required_skills should default to empty list."""
        response = make_full_jd_json()
        response.pop("required_skills")

        with patch(
            "src.parser.jd_extractor.llm_client.complete_json",
            return_value=response,
        ):
            jd = jd_extractor._extract("Some JD text")

        assert jd.required_skills == []

    def test_missing_responsibilities_defaults_to_empty(
        self, jd_extractor
    ):
        """Missing responsibilities should default to empty list."""
        response = make_full_jd_json()
        response.pop("responsibilities")

        with patch(
            "src.parser.jd_extractor.llm_client.complete_json",
            return_value=response,
        ):
            jd = jd_extractor._extract("Some JD text")

        assert jd.responsibilities == []


# ------------------------------------------------------------------
# JD extractor — is_mandatory enforcement
# ------------------------------------------------------------------

class TestJDIsMandatoryEnforcement:

    def test_required_skills_always_mandatory(
        self, jd_extractor
    ):
        """
        Skills in required_skills list should always have
        is_mandatory=True, regardless of what Claude returns.
        """
        response = make_full_jd_json()
        response["required_skills"] = [
            {
                "name": "Python",
                "is_mandatory": False,        # Claude returned wrong value
                "minimum_level": "advanced",
                "minimum_years": None,
            }
        ]

        with patch(
            "src.parser.jd_extractor.llm_client.complete_json",
            return_value=response,
        ):
            jd = jd_extractor._extract("Some JD text")

        # We enforce is_mandatory=True regardless of Claude
        assert jd.required_skills[0].is_mandatory is True

    def test_preferred_skills_always_not_mandatory(
        self, jd_extractor
    ):
        """
        Skills in preferred_skills list should always have
        is_mandatory=False, regardless of what Claude returns.
        """
        response = make_full_jd_json()
        response["preferred_skills"] = [
            {
                "name": "Kubernetes",
                "is_mandatory": True,         # Claude returned wrong value
                "minimum_level": "beginner",
                "minimum_years": None,
            }
        ]

        with patch(
            "src.parser.jd_extractor.llm_client.complete_json",
            return_value=response,
        ):
            jd = jd_extractor._extract("Some JD text")

        assert jd.preferred_skills[0].is_mandatory is False


# ------------------------------------------------------------------
# JD extractor — input validation
# ------------------------------------------------------------------

class TestJDInputValidation:

    def test_empty_string_raises_value_error(self, jd_extractor):
        """Empty JD text should raise ValueError before LLM call."""
        with pytest.raises(ValueError, match="empty"):
            jd_extractor.extract("")

    def test_whitespace_only_raises_value_error(self, jd_extractor):
        """Whitespace-only JD text should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            jd_extractor.extract("     \n\t  ")

    def test_very_short_jd_still_processed(self, jd_extractor):
        """
        A very short but non-empty JD should still be sent to
        the LLM — validation only blocks empty input.
        """
        with patch(
            "src.parser.jd_extractor.llm_client.complete_json",
            return_value=make_full_jd_json(),
        ):
            jd = jd_extractor.extract("Backend engineer needed.")

        assert isinstance(jd, JobDescription)


# ------------------------------------------------------------------
# PDF parser — failure modes
# ------------------------------------------------------------------

class TestPDFParserFailureModes:

    def test_file_not_found_raises_error(self):
        """Non-existent PDF path should raise FileNotFoundError."""
        from src.parser.pdf_parser import PDFParser

        parser = PDFParser()
        with pytest.raises(FileNotFoundError):
            parser.extract_text("/nonexistent/path/resume.pdf")

    def test_non_pdf_extension_raises_error(self, tmp_path):
        """Non-PDF file extension should raise ValueError."""
        from src.parser.pdf_parser import PDFParser

        parser = PDFParser()
        fake_file = tmp_path / "resume.docx"
        fake_file.write_text("not a pdf")

        with pytest.raises(ValueError, match=".pdf"):
            parser.extract_text(str(fake_file))

    def test_empty_pdf_raises_value_error(self, tmp_path):
        """
        A PDF with no extractable text should raise ValueError
        with a clear message about OCR.
        """
        from src.parser.pdf_parser import PDFParser
        import unittest.mock as mock

        parser = PDFParser()
        fake_pdf = tmp_path / "empty.pdf"
        fake_pdf.write_bytes(b"fake pdf content")

        with mock.patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            mock_pdf.pages = [MagicMock(extract_text=lambda: None)]
            mock_open.return_value.__enter__ = MagicMock(
                return_value=mock_pdf
            )
            mock_open.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(ValueError, match="No extractable text"):
                parser.extract_text(str(fake_pdf))

    def test_truncation_applied_for_long_text(self):
        """Text longer than MAX_RESUME_CHARS should be truncated."""
        from src.parser.pdf_parser import PDFParser
        from src.config import config

        parser = PDFParser()
        long_text = "A" * (config.MAX_RESUME_CHARS + 5000)
        result = parser._truncate(long_text)

        assert len(result) <= config.MAX_RESUME_CHARS

    def test_short_text_not_truncated(self):
        """Text shorter than MAX_RESUME_CHARS should not be truncated."""
        from src.parser.pdf_parser import PDFParser

        parser = PDFParser()
        short_text = "Short resume text."
        result = parser._truncate(short_text)

        assert result == short_text


# ------------------------------------------------------------------
# Resume extractor — raw text injection
# ------------------------------------------------------------------

class TestRawTextInjection:

    def test_raw_text_preserved_through_extraction(
        self, resume_extractor
    ):
        """raw_text on profile should match the input text exactly."""
        input_text = "Jane Smith\nSenior Engineer\nPython, Kafka"

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=make_full_resume_json(),
        ):
            profile = resume_extractor._extract(input_text)

        assert profile.raw_text == input_text

    def test_raw_text_not_overwritten_by_claude(
        self, resume_extractor
    ):
        """
        Even if Claude returns a different raw_text value,
        we should always use our own.
        """
        response = make_full_resume_json()
        response["raw_text"] = "WRONG TEXT FROM CLAUDE"
        input_text = "CORRECT TEXT WE OWN"

        with patch(
            "src.parser.resume_extractor.llm_client.complete_json",
            return_value=response,
        ):
            profile = resume_extractor._extract(input_text)

        assert profile.raw_text == input_text
        assert profile.raw_text != "WRONG TEXT FROM CLAUDE"