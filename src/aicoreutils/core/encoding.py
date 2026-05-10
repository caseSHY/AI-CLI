"""Unified encoding boundary layer for aicoreutils.

All text decode/encode operations flow through this module.  Commands
read raw bytes from files/stdin and decode them here; JSON envelope
output uses ensure_ascii=False (UTF-8 safe); raw mode pipes pass bytes
unchanged.

Encoding detection order:
1. BOM match (utf-32-be/le, utf-16-be/le, utf-8-sig)
2. Explicit encoding (user-specified or default "utf-8")
3. Profile fallback chain (when encoding="auto" or --encoding-profile set)
4. latin-1 ultimate fallback (never fails, always warns)
"""

from __future__ import annotations

import codecs
from dataclasses import dataclass, field
from typing import Any

# ── BOM detection table ──────────────────────────────────────────────
# Ordered by BOM-length descending so longest prefix matches first.

BOM_TABLE: list[tuple[bytes, str, int]] = [
    (b"\x00\x00\xfe\xff", "utf-32-be", 4),
    (b"\xff\xfe\x00\x00", "utf-32-le", 4),
    (b"\xfe\xff", "utf-16-be", 2),
    (b"\xff\xfe", "utf-16-le", 2),
    (b"\xef\xbb\xbf", "utf-8-sig", 3),
]

# ── Encoding aliases ─────────────────────────────────────────────────
# User-facing names mapped to Python codec names.

_ENCODING_ALIASES: dict[str, str] = {
    "utf-8": "utf-8",
    "utf-8-sig": "utf-8-sig",
    "utf-16": "utf-16",
    "utf-16-le": "utf-16-le",
    "utf-16-be": "utf-16-be",
    "utf-32": "utf-32",
    "utf-32-le": "utf-32-le",
    "utf-32-be": "utf-32-be",
    "gb18030": "gb18030",
    "gbk": "gbk",
    "gb2312": "gb2312",
    "big5": "big5",
    "big5-hkscs": "big5hkscs",
    "shift_jis": "shift_jis",
    "euc-jp": "euc_jp",
    "euc-kr": "euc_kr",
    "cp949": "cp949",
    "cp932": "cp932",
    "cp936": "cp936",
    "cp950": "cp950",
    "latin-1": "latin_1",
    "windows-1252": "windows_1252",
}

# ── Encoding profiles ────────────────────────────────────────────────
# Each profile is an ordered fallback chain.  The first codec that
# successfully decodes (with errors="replace") wins.

ENCODING_PROFILES: dict[str, list[str]] = {
    "zh-cn": ["gb18030", "gbk", "utf-8", "latin-1"],
    "zh-tw": ["big5", "utf-8", "latin-1"],
    "ja": ["shift_jis", "euc-jp", "utf-8", "latin-1"],
    "ko": ["euc-kr", "cp949", "utf-8", "latin-1"],
    "western": ["windows-1252", "latin-1", "utf-8"],
    "universal": ["utf-8", "gb18030", "big5", "shift_jis", "euc-kr", "windows-1252", "latin-1"],
}


@dataclass
class EncodingResult:
    """Result of a decode operation with detection metadata."""

    text: str
    encoding_used: str
    bom_stripped: bool = False
    confidence: float = 1.0
    method: str = "exact"  # "bom" | "exact" | "profile_fallback" | "latin1_fallback"
    warnings: list[str] = field(default_factory=list)


# ── Public API ───────────────────────────────────────────────────────


def detect_bom(data: bytes) -> tuple[str | None, int]:
    """Detect BOM in raw bytes.

    Returns (encoding_name, bom_length).  encoding_name is None when
    no BOM is found; bom_length is 0 in that case.
    """
    for bom_bytes, enc, length in BOM_TABLE:
        if data.startswith(bom_bytes):
            return enc, length
    return None, 0


def normalize_encoding(name: str) -> str:
    """Resolve a user-facing encoding name to a Python codec name.

    Case-insensitive; dashes/underscores are treated equivalently.
    Raises ValueError for unknown names.
    """
    key = name.lower().replace("_", "-").strip()
    if key == "auto":
        return "auto"
    alias = _ENCODING_ALIASES.get(key)
    if alias is not None:
        return alias
    # Try as a raw Python codec
    try:
        codecs.lookup(name)
        return name.lower()
    except LookupError:
        raise ValueError(f"Unsupported encoding: {name!r}") from None


def _try_decode(data: bytes, codec: str, errors: str) -> str | None:
    """Attempt to decode data with a given codec and error strategy.

    Returns the decoded string on success, or None on failure.
    """
    try:
        return data.decode(codec, errors)
    except (UnicodeDecodeError, LookupError):
        return None


def _confidence_from_replacement(text: str, total_bytes: int) -> float:
    """Estimate confidence based on replacement-character ratio.

    U+FFFD characters indicate bytes that could not be decoded.
    100% replacement means near-zero confidence.
    """
    if total_bytes == 0:
        return 1.0
    replacement_count = text.count("�")
    if replacement_count == 0:
        return 0.95  # decoded cleanly but might be wrong codec
    ratio = replacement_count / max(total_bytes, 1)
    return max(0.1, 1.0 - ratio * 2.0)


def decode_bytes(
    data: bytes,
    *,
    encoding: str = "utf-8",
    errors: str = "replace",
    profile: str | None = None,
) -> EncodingResult:
    """Decode raw bytes to str with BOM detection and fallback chains.

    Args:
        data: Raw bytes to decode.
        encoding: Declared encoding ("auto" triggers detection).
        errors: Error strategy: "strict", "replace", or "surrogateescape".
        profile: Fallback chain profile name when encoding="auto" or
                 detection is needed.

    Returns:
        EncodingResult with the decoded text and metadata.
    """
    warnings: list[str] = []

    # ── Step 1: BOM detection ──
    bom_enc, bom_len = detect_bom(data)
    if bom_enc is not None:
        decoded = _try_decode(data, bom_enc, errors)
        if decoded is not None:
            warn = None
            if encoding != "auto" and normalize_encoding(encoding) != bom_enc:
                warn = f"BOM indicates {bom_enc} but declared encoding is {encoding}"
                warnings.append(warn)
            return EncodingResult(
                text=decoded,
                encoding_used=bom_enc,
                bom_stripped=True,
                confidence=1.0,
                method="bom",
                warnings=warnings,
            )

    # ── Step 2: Explicit encoding ──
    if encoding != "auto":
        codec = normalize_encoding(encoding)
        if errors == "strict":
            text = data.decode(codec, errors="strict")
            return EncodingResult(
                text=text,
                encoding_used=codec,
                confidence=1.0,
                method="exact",
            )
        decoded = _try_decode(data, codec, errors)
        if decoded is not None:
            confidence = _confidence_from_replacement(decoded, len(data))
            w = warnings[:]
            if confidence < 0.8:
                w.append(f"Low confidence ({confidence:.0%}) decoding with {encoding}")
            return EncodingResult(
                text=decoded,
                encoding_used=codec,
                confidence=confidence,
                method="exact",
                warnings=w,
            )
        # Explicit encoding failed — fall through to profile/latin-1
        warnings.append(f"Explicit encoding {encoding!r} failed; trying fallback")

    # ── Step 3: Profile fallback chain ──
    chain = ENCODING_PROFILES.get(profile or "universal", ENCODING_PROFILES["universal"])
    best_text: str | None = None
    best_codec: str = "latin-1"
    best_confidence: float = 0.0

    for codec in chain:
        decoded = _try_decode(data, codec, "replace")
        if decoded is None:
            continue
        conf = _confidence_from_replacement(decoded, len(data))
        if conf > best_confidence:
            best_text = decoded
            best_codec = codec
            best_confidence = conf
        if conf >= 0.95:
            break  # Good enough

    # ── Step 4: Ultimate latin-1 fallback ──
    if best_text is None:
        decoded = data.decode("latin-1", errors="replace")
        best_text = decoded
        best_codec = "latin-1"
        best_confidence = 0.1
        warnings.append("All codecs failed; fell back to latin-1 (byte passthrough)")

    if best_confidence < 0.5:
        warnings.append(
            f"Low confidence decoding ({best_confidence:.0%}); best match was {best_codec!r}. Output may be garbled."
        )

    method = "latin1_fallback" if best_codec == "latin-1" and best_confidence <= 0.1 else "profile_fallback"
    return EncodingResult(
        text=best_text,
        encoding_used=best_codec,
        confidence=round(best_confidence, 2),
        method=method,
        warnings=warnings,
    )


def detect_encoding(
    data: bytes,
    *,
    profile: str = "universal",
    hint: str | None = None,
) -> tuple[str, float, str, list[str]]:
    """Detect the likely encoding of raw bytes without decoding to text.

    Returns (encoding_name, confidence, method, warnings).
    This is a convenience wrapper around decode_bytes that discards the
    text after detection.
    """
    r = decode_bytes(data, encoding="auto", errors="replace", profile=profile)
    return r.encoding_used, r.confidence, r.method, r.warnings


def encoding_metadata(result: EncodingResult, declared: str | None = None) -> dict[str, Any]:
    """Build the JSON encoding metadata dict for --show-encoding output.

    Args:
        result: The EncodingResult from decode_bytes.
        declared: The user-declared encoding name (or None).

    Returns:
        A dict suitable for inclusion in the JSON result envelope:
        {"declared": ..., "detected": ..., "confidence": ..., "method": ..., "warnings": ...}
    """
    meta: dict[str, Any] = {
        "declared": declared,
        "detected": result.encoding_used,
        "confidence": result.confidence,
        "method": result.method,
    }
    if result.warnings:
        meta["warnings"] = result.warnings
    else:
        meta["warnings"] = []
    return meta
