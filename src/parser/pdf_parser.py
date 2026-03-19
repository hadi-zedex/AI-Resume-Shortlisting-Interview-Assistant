import pdfplumber
import re
from pathlib import Path
from src.config import config


class PDFParser:
    """
    Extracts raw text from a PDF resume.
    Uses pdfplumber for reliable text extraction.
    Does NOT call any LLM — pure local processing.
    """

    def extract_text(self, pdf_path: str | Path) -> str:
        """
        Extract and clean raw text from a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Cleaned plain text string.

        Raises:
            FileNotFoundError: If the PDF path does not exist.
            ValueError:        If the PDF has no extractable text
                               (e.g. scanned image-only PDF).
        """
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

        raw_pages: list[str] = []

        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    raw_pages.append(text)
                else:
                    print(f"[PDFParser] Warning: Page {page_num} yielded no text.")

        if not raw_pages:
            raise ValueError(
                f"No extractable text found in '{path.name}'. "
                "The PDF may be a scanned image. "
                "OCR support is not included in this version."
            )

        full_text = "\n\n".join(raw_pages)
        cleaned = self._clean_text(full_text)
        truncated = self._truncate(cleaned)

        return truncated

    def extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        """
        Extract and clean raw text from PDF bytes (e.g. uploaded via UI).

        Args:
            pdf_bytes: Raw bytes of the PDF file.

        Returns:
            Cleaned plain text string.

        Raises:
            ValueError: If no extractable text is found.
        """
        import io

        raw_pages: list[str] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    raw_pages.append(text)
                else:
                    print(f"[PDFParser] Warning: Page {page_num} yielded no text.")

        if not raw_pages:
            raise ValueError(
                "No extractable text found in the uploaded PDF. "
                "The file may be a scanned image. "
                "OCR support is not included in this version."
            )

        full_text = "\n\n".join(raw_pages)
        cleaned = self._clean_text(full_text)
        truncated = self._truncate(cleaned)

        return truncated

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Normalize raw extracted text for LLM consumption.
        - Collapse multiple blank lines into one
        - Collapse multiple spaces into one
        - Strip leading/trailing whitespace per line
        - Remove non-printable characters
        """
        # Remove non-printable / non-ASCII control characters
        text = re.sub(r"[^\x20-\x7E\n]", " ", text)

        # Strip trailing whitespace on each line
        lines = [line.rstrip() for line in text.splitlines()]

        # Collapse 3+ consecutive blank lines into 2
        cleaned_lines = []
        blank_count = 0
        for line in lines:
            if line.strip() == "":
                blank_count += 1
                if blank_count <= 2:
                    cleaned_lines.append(line)
            else:
                blank_count = 0
                cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)

        # Collapse multiple spaces into one
        text = re.sub(r" {2,}", " ", text)

        return text.strip()

    @staticmethod
    def _truncate(text: str) -> str:
        """
        Truncate text to MAX_RESUME_CHARS to avoid hitting token limits.
        Truncates at a newline boundary to avoid cutting mid-sentence.
        """
        limit = config.MAX_RESUME_CHARS

        if len(text) <= limit:
            return text

        truncated = text[:limit]

        # Walk back to the nearest newline to avoid cutting mid-sentence
        last_newline = truncated.rfind("\n")
        if last_newline > limit * 0.8:          # Only snap if newline is reasonably close
            truncated = truncated[:last_newline]

        print(
            f"[PDFParser] Resume truncated from {len(text)} "
            f"to {len(truncated)} characters."
        )

        return truncated.strip()


# Singleton
pdf_parser = PDFParser()