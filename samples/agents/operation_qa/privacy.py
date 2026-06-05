from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any


PHONE_RE = re.compile(r"(?<!\d)(\d{2,3})[-.\s]?(\d{3,4})[-.\s]?(\d{4})(?!\d)")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
RRN_RE = re.compile(r"(?<!\d)(\d{6})[-\s]?[1-4]\d{6}(?!\d)")

PHONE_KEYS = {"phone", "caller_phone", "guardian_phone"}
EMAIL_KEYS = {"email"}
ADDRESS_KEYS = {"address"}
BIRTH_KEYS = {"birth_date", "patient_birth_date_snapshot"}
TRANSCRIPT_KEYS = {"transcript_text", "transcript_raw_text", "transcript_edited_text"}
SENSITIVE_NOTE_TOKENS = (
    "disease",
    "allergy",
    "medication_note",
    "special_note",
    "request_memo",
    "remark",
)


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    return PHONE_RE.sub(r"\1-****-\3", value)


def mask_email(value: str | None) -> str | None:
    if not value:
        return value
    return EMAIL_RE.sub(r"\1***\2", value)


def mask_birth_date(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    text = value.isoformat() if isinstance(value, (date, datetime)) else str(value)
    return f"{text[:4]}-**-**" if len(text) >= 4 else "****-**-**"


def mask_text(value: str | None) -> str | None:
    if value is None:
        return None
    masked = PHONE_RE.sub(r"\1-****-\3", value)
    masked = EMAIL_RE.sub(r"\1***\2", masked)
    masked = RRN_RE.sub(r"\1-*******", masked)
    return masked


def sanitize_for_llm(value: Any) -> Any:
    return _sanitize(value, redact_sensitive_notes=True)


def sanitize_answer(value: str) -> str:
    return mask_text(value) or ""


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def _sanitize(value: Any, *, redact_sensitive_notes: bool) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_field(key, item, redact_sensitive_notes=redact_sensitive_notes)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item, redact_sensitive_notes=redact_sensitive_notes) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item, redact_sensitive_notes=redact_sensitive_notes) for item in value]
    return to_jsonable(value)


def _sanitize_field(key: str, value: Any, *, redact_sensitive_notes: bool) -> Any:
    normalized_key = key.lower()
    if normalized_key in PHONE_KEYS:
        return mask_phone(str(value)) if value is not None else None
    if normalized_key in EMAIL_KEYS:
        return mask_email(str(value)) if value is not None else None
    if normalized_key in ADDRESS_KEYS:
        return "[주소 마스킹]" if value else None
    if normalized_key in BIRTH_KEYS or normalized_key.endswith("_birth_date"):
        return mask_birth_date(value)
    if normalized_key in TRANSCRIPT_KEYS:
        return "[녹취 원문 마스킹]" if value else None
    if redact_sensitive_notes and any(token in normalized_key for token in SENSITIVE_NOTE_TOKENS):
        return "[민감정보 마스킹]" if value else None
    return _sanitize(value, redact_sensitive_notes=redact_sensitive_notes)
