"""India-specific PII regex patterns."""

from __future__ import annotations

import re

PHONE_IN = re.compile(r"(?:\+91[-\s]?)?[6-9]\d{9}")
AADHAAR_LIKE = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")


def find_indian_pii(text: str) -> dict[str, list[str]]:
    return {
        "phone_in": PHONE_IN.findall(text),
        "aadhaar_like": AADHAAR_LIKE.findall(text),
    }

