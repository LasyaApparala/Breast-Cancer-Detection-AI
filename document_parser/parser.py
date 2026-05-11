"""
Document Parser: converts raw file bytes into structured text + page data.

Supports:
  - PDF via pdfplumber
  - Images (JPEG, PNG, TIFF) via pytesseract OCR
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


class ParsedDocument:
    """Holds the result of parsing a single document."""

    def __init__(
        self,
        text: str,
        pages: list[dict],
        document_id: str,
        mime_type: str,
    ) -> None:
        self.text = text
        self.pages = pages  # [{"page_num": 1, "text": "..."}]
        self.document_id = document_id
        self.mime_type = mime_type

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ParsedDocument(document_id={self.document_id!r}, "
            f"mime_type={self.mime_type!r}, pages={len(self.pages)})"
        )


class DocumentParser:
    """Parse a document from raw bytes into a ParsedDocument."""

    def parse(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_id: str,
    ) -> ParsedDocument:
        """
        Parse *file_bytes* according to *mime_type*.

        Supported MIME types:
          - application/pdf  → pdfplumber text extraction
          - image/jpeg, image/png, image/tiff → pytesseract OCR

        Raises ValueError for unsupported MIME types.
        """
        if mime_type == "application/pdf":
            return self._parse_pdf(file_bytes, document_id)
        elif mime_type in ("image/jpeg", "image/png", "image/tiff"):
            return self._parse_image(file_bytes, mime_type, document_id)
        else:
            raise ValueError(f"Unsupported mime type: {mime_type}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_pdf(self, file_bytes: bytes, document_id: str) -> ParsedDocument:
        """Extract text from a PDF using pdfplumber."""
        try:
            import pdfplumber  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "pdfplumber is required for PDF parsing. "
                "Install it with: pip install pdfplumber"
            ) from exc

        pages: list[dict] = []
        all_text_parts: list[str] = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                page_text: str = page.extract_text() or ""
                pages.append({"page_num": i, "text": page_text})
                all_text_parts.append(page_text)

        full_text = "\n".join(all_text_parts)
        logger.info(
            "Parsed PDF document_id=%s: %d pages, %d chars",
            document_id,
            len(pages),
            len(full_text),
        )
        return ParsedDocument(
            text=full_text,
            pages=pages,
            document_id=document_id,
            mime_type="application/pdf",
        )

    def _parse_image(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_id: str,
    ) -> ParsedDocument:
        """OCR an image using pytesseract."""
        try:
            import pytesseract  # type: ignore[import]
            from PIL import Image  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "pytesseract and Pillow are required for image OCR. "
                "Install them with: pip install pytesseract Pillow"
            ) from exc

        image = Image.open(io.BytesIO(file_bytes))
        page_text: str = pytesseract.image_to_string(image) or ""

        pages = [{"page_num": 1, "text": page_text}]
        logger.info(
            "OCR'd image document_id=%s: %d chars",
            document_id,
            len(page_text),
        )
        return ParsedDocument(
            text=page_text,
            pages=pages,
            document_id=document_id,
            mime_type=mime_type,
        )
