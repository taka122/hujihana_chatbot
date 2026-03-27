from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.config import get_settings
from app.services.gemini_client import GeminiApiError, GeminiClient
from app.services.text_decode import decode_text_bytes, extract_charset_from_mime

logger = logging.getLogger(__name__)


class IngestionError(RuntimeError):
    pass


class UnsupportedDocumentError(IngestionError):
    def __init__(self, message: str, tags: list[str]) -> None:
        super().__init__(message)
        self.tags = tags


@dataclass
class TextBlock:
    text: str
    page: int | None
    section_title: str | None


@dataclass
class ParseResult:
    page_count: int | None
    extracted_pages: int
    failed_pages: list[dict]
    ocr_used_pages: list[int]
    tags: list[str]
    blocks: list[TextBlock]


@dataclass
class ChunkPayload:
    chunk_index: int
    text: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    snippet: str


def parse_document(
    file_name: str,
    mime_type: str,
    data: bytes,
    gemini_api_key_override: str | None = None,
) -> ParseResult:
    ext = Path(file_name).suffix.lower()
    normalized_mime = (mime_type or "").lower()

    if ext == ".pdf" or normalized_mime == "application/pdf":
        return _parse_pdf(
            data,
            gemini_api_key_override=gemini_api_key_override,
        )

    if ext == ".docx" or normalized_mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        return _parse_docx(data)

    if ext in {".txt", ".md"} or normalized_mime.startswith("text/"):
        declared_encoding = extract_charset_from_mime(mime_type)
        decoded = decode_text_bytes(data, declared_encoding=declared_encoding)
        if decoded.suspicious_mojibake:
            logger.warning("Possible mojibake detected. encoding=%s file=%s", decoded.encoding, file_name)
        return _parse_text_like(decoded.text, ext=ext, decode_tags=decoded.tags)

    if ext in {".ppt", ".pptx"}:
        raise UnsupportedDocumentError("PPT/PPTX is not supported in MVP", tags=["UNSUPPORTED_PPT", "OCR_CANDIDATE"])
    if ext in {".xls", ".xlsx"}:
        raise UnsupportedDocumentError("XLS/XLSX is not supported in MVP", tags=["UNSUPPORTED_XLS", "TABLE_EXTRACT_FAILED"])
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
        raise UnsupportedDocumentError("Image file requires OCR (not enabled in MVP)", tags=["OCR_REQUIRED"])

    raise UnsupportedDocumentError("Unsupported file type", tags=["UNSUPPORTED_TYPE"])


def build_chunks(blocks: list[TextBlock]) -> list[ChunkPayload]:
    settings = get_settings()
    chunk_size = settings.chunk_size_chars
    overlap = settings.chunk_overlap_chars

    units: list[TextBlock] = []
    for block in blocks:
        for part in _split_text(block.text, max_chars=chunk_size):
            if part.strip():
                units.append(TextBlock(text=part.strip(), page=block.page, section_title=block.section_title))

    if not units:
        return []

    chunks: list[ChunkPayload] = []
    current: list[TextBlock] = []
    current_len = 0

    def emit(chunk_index: int, selected: list[TextBlock]) -> ChunkPayload | None:
        if not selected:
            return None
        text = "\n".join(item.text for item in selected).strip()
        if not text:
            return None
        pages = [item.page for item in selected if item.page is not None]
        section = next((item.section_title for item in selected if item.section_title), None)
        snippet = re.sub(r"\s+", " ", text)[:300]
        return ChunkPayload(
            chunk_index=chunk_index,
            text=text,
            page_start=min(pages) if pages else None,
            page_end=max(pages) if pages else None,
            section_title=section,
            snippet=snippet,
        )

    for unit in units:
        projected_len = current_len + len(unit.text) + (1 if current else 0)
        if current and projected_len > chunk_size:
            payload = emit(len(chunks), current)
            if payload:
                chunks.append(payload)

            overlap_text = payload.text[-overlap:] if payload else ""
            current = []
            current_len = 0
            if overlap_text.strip():
                current.append(
                    TextBlock(
                        text=overlap_text.strip(),
                        page=payload.page_end if payload else None,
                        section_title=payload.section_title if payload else None,
                    )
                )
                current_len = len(overlap_text)

        current.append(unit)
        current_len += len(unit.text) + (1 if len(current) > 1 else 0)

    last_payload = emit(len(chunks), current)
    if last_payload:
        chunks.append(last_payload)

    return chunks


def _parse_pdf(
    data: bytes,
    gemini_api_key_override: str | None = None,
) -> ParseResult:
    settings = get_settings()
    reader = PdfReader(io.BytesIO(data))
    page_count = len(reader.pages)
    min_text_chars = settings.pdf_min_text_chars_per_page

    blocks: list[TextBlock] = []
    failed_pages: list[dict] = []
    ocr_used_pages: list[int] = []
    short_text_pages: list[int] = []
    tags: list[str] = []
    extracted_pages = 0
    low_text_pages = 0

    ocr_client: GeminiClient | None = None
    ocr_pages_attempted = 0
    ocr_enabled = settings.pdf_ocr_enabled
    override_gemini_key = _normalize_api_key(gemini_api_key_override)
    if ocr_enabled:
        api_key = override_gemini_key or settings.gemini_api_key
        if not api_key:
            logger.info("PDF OCR is enabled but skipped because Gemini API key is not set.")
            ocr_enabled = False
        else:
            ocr_client = GeminiClient(api_key=api_key, base_url=settings.gemini_base_url)

    for index, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = raw.strip()
        if len(text) >= min_text_chars:
            extracted_pages += 1
            blocks.append(TextBlock(text=text, page=index, section_title=None))
            continue

        low_text_pages += 1

        ocr_text = ""
        if ocr_enabled and ocr_client and ocr_pages_attempted < settings.pdf_ocr_max_pages_per_doc:
            ocr_pages_attempted += 1
            ocr_text = _extract_page_text_via_ocr(page, ocr_client, settings.pdf_ocr_model)

        if len(ocr_text) >= min_text_chars:
            extracted_pages += 1
            ocr_used_pages.append(index)
            blocks.append(TextBlock(text=ocr_text, page=index, section_title=None))
            continue

        short_candidate = ""
        used_ocr_for_short = False
        if text or ocr_text:
            if len(ocr_text) > len(text):
                short_candidate = ocr_text
                used_ocr_for_short = True
            else:
                short_candidate = text

        if short_candidate:
            extracted_pages += 1
            short_text_pages.append(index)
            if used_ocr_for_short:
                ocr_used_pages.append(index)
            blocks.append(TextBlock(text=short_candidate, page=index, section_title=None))
            continue

        failed_pages.append({"page": index, "reason": "image_only_or_no_text"})

    if page_count > 0 and low_text_pages / page_count >= settings.image_only_pdf_ratio_threshold:
        tags.append("IMAGE_ONLY_PDF")
    if short_text_pages:
        tags.append("SHORT_TEXT_INCLUDED")
    if ocr_used_pages:
        tags.append("OCR_USED")
    if extracted_pages == 0:
        tags.append("OCR_REQUIRED")

    return ParseResult(
        page_count=page_count,
        extracted_pages=extracted_pages,
        failed_pages=failed_pages,
        ocr_used_pages=ocr_used_pages,
        tags=tags,
        blocks=blocks,
    )


def _parse_docx(data: bytes) -> ParseResult:
    doc = DocxDocument(io.BytesIO(data))
    blocks: list[TextBlock] = []
    current_heading: str | None = None

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
        if style_name.startswith("heading"):
            current_heading = text
            continue
        blocks.append(TextBlock(text=text, page=None, section_title=current_heading))

    if not blocks:
        raise IngestionError("DOCX has no extractable paragraphs")

    return ParseResult(
        page_count=None,
        extracted_pages=1,
        failed_pages=[],
        ocr_used_pages=[],
        tags=[],
        blocks=blocks,
    )


def _parse_text_like(text: str, ext: str, decode_tags: list[str] | None = None) -> ParseResult:
    blocks: list[TextBlock] = []

    if ext == ".md":
        current_heading: str | None = None
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                current_heading = stripped.lstrip("#").strip()
                continue
            blocks.append(TextBlock(text=stripped, page=None, section_title=current_heading))
    else:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                blocks.append(TextBlock(text=stripped, page=None, section_title=None))

    if not blocks:
        raise IngestionError("Text document is empty")

    return ParseResult(
        page_count=None,
        extracted_pages=1,
        failed_pages=[],
        ocr_used_pages=[],
        tags=list(decode_tags or []),
        blocks=blocks,
    )


def _extract_page_text_via_ocr(page: Any, client: GeminiClient, model: str) -> str:
    images = _extract_page_images_for_ocr(page)
    if not images:
        return ""

    try:
        ocr_text = client.extract_text_from_images(
            model=model,
            images=images,
            prompt=(
                "この画像に含まれる文字をOCRしてください。"
                "推測や要約をせず、読み取れた文字だけを改行を保って返してください。"
            ),
        )
    except GeminiApiError as exc:
        logger.warning("Gemini OCR failed: %s", exc)
        return ""

    return ocr_text.strip()


def _extract_page_images_for_ocr(page: Any) -> list[tuple[str, bytes]]:
    page_images = getattr(page, "images", None)
    if not page_images:
        return []

    candidates: list[tuple[str, bytes]] = []
    for image in page_images:
        raw = getattr(image, "data", None)
        if not isinstance(raw, (bytes, bytearray)):
            continue
        data = bytes(raw)
        if len(data) < 128:
            continue
        mime_type = _detect_image_mime(image, data)
        if not mime_type.startswith("image/"):
            continue
        candidates.append((mime_type, data))

    # OCRトークン削減のため、容量の大きい画像を優先して最大3枚まで使う
    candidates.sort(key=lambda item: len(item[1]), reverse=True)
    return candidates[:3]


def _detect_image_mime(image: Any, data: bytes) -> str:
    name = str(getattr(image, "name", "")).lower()
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith((".tif", ".tiff")):
        return "image/tiff"
    if name.endswith(".gif"):
        return "image/gif"

    signature = data[:16]
    if signature.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if signature.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    if signature.startswith(b"GIF87a") or signature.startswith(b"GIF89a"):
        return "image/gif"
    if signature.startswith(b"RIFF") and b"WEBP" in signature:
        return "image/webp"

    # 未判別フォーマットはOCR対象外にする
    return "application/octet-stream"


def _normalize_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _split_text(text: str, max_chars: int) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [segment.strip() for segment in normalized.split("\n\n") if segment.strip()]

    if not paragraphs:
        paragraphs = [normalized.strip()]

    parts: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            parts.append(paragraph)
            continue
        start = 0
        while start < len(paragraph):
            parts.append(paragraph[start : start + max_chars])
            start += max_chars

    return parts
