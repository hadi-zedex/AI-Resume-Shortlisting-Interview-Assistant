from pathlib import Path
from src.config import config


class ResumeValidator:
    """
    Validates resume inputs before they hit the LLM or PDF parser.
    All validation is fast, local, and free.
    Raises ValueError or FileNotFoundError with clear messages.
    """

    @staticmethod
    def validate_pdf_path(pdf_path: str | Path) -> Path:
        """
        Validate a PDF file path before parsing.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Validated Path object.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError:        If the file is not a PDF or is empty.
        """
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Resume PDF not found: '{path}'. "
                f"Please check the file path."
            )

        if not path.is_file():
            raise ValueError(
                f"Path is not a file: '{path}'."
            )

        if path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Expected a .pdf file, got '{path.suffix}'. "
                f"Only PDF resumes are supported."
            )

        if path.stat().st_size == 0:
            raise ValueError(
                f"Resume PDF is empty (0 bytes): '{path.name}'."
            )

        if path.stat().st_size > 10 * 1024 * 1024:     # 10 MB
            raise ValueError(
                f"Resume PDF is too large "
                f"({path.stat().st_size / 1024 / 1024:.1f} MB). "
                f"Maximum allowed size is 10 MB."
            )

        return path

    @staticmethod
    def validate_pdf_bytes(pdf_bytes: bytes, filename: str = "resume") -> None:
        """
        Validate raw PDF bytes before parsing.

        Args:
            pdf_bytes: Raw bytes of the uploaded PDF.
            filename:  Original filename for error messages.

        Raises:
            ValueError: If the bytes are empty, too large,
                        or not a valid PDF.
        """
        if not pdf_bytes:
            raise ValueError(
                f"Uploaded file '{filename}' is empty. "
                f"Please upload a valid PDF resume."
            )

        if len(pdf_bytes) > 10 * 1024 * 1024:          # 10 MB
            raise ValueError(
                f"Uploaded file is too large "
                f"({len(pdf_bytes) / 1024 / 1024:.1f} MB). "
                f"Maximum allowed size is 10 MB."
            )

        # Check PDF magic bytes — all PDFs start with %PDF
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError(
                f"File '{filename}' does not appear to be a valid PDF. "
                f"Please upload a PDF resume."
            )

    @staticmethod
    def validate_raw_text(raw_text: str, source: str = "Resume") -> None:
        """
        Validate raw extracted text before sending to LLM.

        Args:
            raw_text: Extracted text from the PDF.
            source:   Label for error messages ("Resume" or "JD").

        Raises:
            ValueError: If the text is empty or too short.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError(
                f"{source} text is empty after extraction. "
                f"The PDF may be a scanned image. "
                f"OCR support is not included in this version."
            )

        MIN_CHARS = 100
        if len(raw_text.strip()) < MIN_CHARS:
            raise ValueError(
                f"{source} text is too short "
                f"({len(raw_text.strip())} characters). "
                f"Minimum required: {MIN_CHARS} characters. "
                f"Please check the uploaded file."
            )


class JDValidator:
    """
    Validates job description inputs before they hit the LLM.
    """

    @staticmethod
    def validate_jd_text(jd_text: str) -> str:
        """
        Validate and clean job description text.

        Args:
            jd_text: Raw job description text.

        Returns:
            Cleaned and stripped JD text.

        Raises:
            ValueError: If the text is empty, too short, or too generic.
        """
        if not jd_text or not jd_text.strip():
            raise ValueError(
                "Job description text is empty. "
                "Please paste the full job description."
            )

        cleaned = jd_text.strip()

        MIN_CHARS = 100
        if len(cleaned) < MIN_CHARS:
            raise ValueError(
                f"Job description is too short "
                f"({len(cleaned)} characters). "
                f"Please paste the complete job description including "
                f"requirements and responsibilities."
            )

        MAX_CHARS = config.MAX_JD_CHARS * 3        # Allow 3x before hard truncation
        if len(cleaned) > MAX_CHARS:
            print(
                f"[JDValidator] JD is very long "
                f"({len(cleaned)} characters). "
                f"It will be truncated before processing."
            )

        return cleaned


class PipelineInputValidator:
    """
    Top-level validator that runs all input checks
    before the pipeline starts.
    Combines ResumeValidator and JDValidator.
    """

    resume_validator = ResumeValidator()
    jd_validator = JDValidator()

    @classmethod
    def validate_bytes_input(
        cls,
        pdf_bytes: bytes,
        jd_text: str,
        filename: str = "resume.pdf",
    ) -> str:
        """
        Validate all pipeline inputs when receiving PDF as bytes.
        Called from the Streamlit UI.

        Args:
            pdf_bytes: Raw PDF bytes from file uploader.
            jd_text:   Raw job description text.
            filename:  Original filename for error messages.

        Returns:
            Cleaned JD text.

        Raises:
            ValueError: If any input is invalid.
        """
        cls.resume_validator.validate_pdf_bytes(pdf_bytes, filename)
        cleaned_jd = cls.jd_validator.validate_jd_text(jd_text)
        return cleaned_jd

    @classmethod
    def validate_path_input(
        cls,
        pdf_path: str | Path,
        jd_text: str,
    ) -> tuple[Path, str]:
        """
        Validate all pipeline inputs when receiving PDF as a path.
        Called from CLI or tests.

        Args:
            pdf_path: Path to the PDF file.
            jd_text:  Raw job description text.

        Returns:
            Tuple of (validated Path, cleaned JD text).

        Raises:
            FileNotFoundError: If the PDF path does not exist.
            ValueError:        If any input is invalid.
        """
        validated_path = cls.resume_validator.validate_pdf_path(pdf_path)
        cleaned_jd = cls.jd_validator.validate_jd_text(jd_text)
        return validated_path, cleaned_jd


# Singletons
resume_validator = ResumeValidator()
jd_validator = JDValidator()
pipeline_input_validator = PipelineInputValidator()