from __future__ import annotations

import codecs
import re
from dataclasses import dataclass


_CHARSET_RE = re.compile(r"charset\s*=\s*['\"]?([a-zA-Z0-9._\-]+)", re.IGNORECASE)
_MOJIBAKE_PATTERN_RE = re.compile(r"(?:Ã.|Â.|ã.|â.|ð.|�)")
_ALLOWED_TEXT_RE = re.compile(
    r"[a-zA-Z0-9\s"
    r"\u3040-\u309F"  # 平仮名
    r"\u30A0-\u30FF"  # 片仮名
    r"\u4E00-\u9FFF"  # 漢字
    r"\uFF01-\uFF5E"  # 全角記号
    r"\u0020-\u007E"  # 半角記号
    r"\u3000-\u303F"  # CJK punctuation
    r"、。！？「」ー]"
)
_SUSPICIOUS_SCRIPT_RE = re.compile(r"[\u0250-\u02AF\u0370-\u03FF\u0590-\u06FF\u0900-\u0D7F]")


@dataclass(frozen=True)
class DecodedText:
    text: str
    encoding: str
    had_replacements: bool
    suspicious_mojibake: bool

    @property
    def tags(self) -> list[str]:
        tags: list[str] = []
        if self.had_replacements:
            tags.append("DECODE_REPLACED")
        if self.suspicious_mojibake:
            tags.append("POSSIBLE_MOJIBAKE")
        return tags


def extract_charset_from_mime(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    match = _CHARSET_RE.search(mime_type)
    if not match:
        return None
    return _normalize_encoding_name(match.group(1))


def decode_text_bytes(data: bytes, declared_encoding: str | None = None) -> DecodedText:
    if not data:
        return DecodedText(text="", encoding="utf-8", had_replacements=False, suspicious_mojibake=False)

    bom_guess = _encoding_from_bom(data)
    candidates = _build_candidates(bom_guess=bom_guess, declared=declared_encoding)

    best_text: str | None = None
    best_encoding: str | None = None
    best_score: int | None = None

    for encoding in candidates:
        try:
            decoded = data.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            continue
        score = _decode_quality_score(decoded)
        if best_score is None or score < best_score:
            best_text = decoded
            best_encoding = encoding
            best_score = score

    if best_text is None or best_encoding is None:
        fallback = data.decode("utf-8", errors="replace")
        return DecodedText(
            text=fallback,
            encoding="utf-8(replace)",
            had_replacements=True,
            suspicious_mojibake=_looks_like_mojibake(fallback),
        )

    return DecodedText(
        text=best_text,
        encoding=best_encoding,
        had_replacements=False,
        suspicious_mojibake=_looks_like_mojibake(best_text),
    )


def _encoding_from_bom(data: bytes) -> str | None:
    if data.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if data.startswith(codecs.BOM_UTF32_LE) or data.startswith(codecs.BOM_UTF32_BE):
        return "utf-32"
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return "utf-16"
    return None


def _build_candidates(bom_guess: str | None, declared: str | None) -> list[str]:
    ordered = [
        bom_guess,
        declared,
        "utf-8-sig",
        "utf-8",
        "cp932",
        "shift_jis",
        "euc_jp",
        "iso2022_jp",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "cp1252",
    ]
    candidates: list[str] = []
    for item in ordered:
        normalized = _normalize_encoding_name(item)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def _normalize_encoding_name(name: str | None) -> str | None:
    if not name:
        return None
    try:
        return codecs.lookup(name).name
    except LookupError:
        return None


def _decode_quality_score(text: str) -> int:
    control_chars = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t")
    zero_bytes = text.count("\x00")
    mojibake_hits = len(_MOJIBAKE_PATTERN_RE.findall(text))
    # lower is better
    return (control_chars * 20) + (zero_bytes * 30) + (mojibake_hits * 8)


def is_probably_garbled_text(text: str) -> bool:
    if not text:
        return False

    if _looks_like_mojibake(text):
        return True

    total = max(len(text), 1)
    allowed = len(_ALLOWED_TEXT_RE.findall(text))
    suspicious = len(_SUSPICIOUS_SCRIPT_RE.findall(text))
    control_chars = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t")

    allowed_ratio = allowed / total
    suspicious_ratio = suspicious / total

    if control_chars > 0 and allowed_ratio < 0.85:
        return True
    if suspicious >= 4 and suspicious_ratio >= 0.05:
        return True
    return allowed_ratio < 0.45


def _looks_like_mojibake(text: str) -> bool:
    if not text:
        return False
    hits = len(_MOJIBAKE_PATTERN_RE.findall(text))
    if hits >= 8:
        return True
    ratio = hits / max(len(text), 1)
    return ratio >= 0.03 and hits >= 3
