from __future__ import annotations

import re
from typing import Iterable


_NON_WORD_RE = re.compile(r"[^0-9a-zа-яё]+", re.IGNORECASE)


def normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    cleaned = _NON_WORD_RE.sub(" ", lowered)
    return " ".join(cleaned.split()).strip()


def tokenize(text: str) -> list[str]:
    norm = normalize_text(text)
    if not norm:
        return []
    return norm.split()


def build_keywords(*parts: Iterable[str | None]) -> str:
    tokens: list[str] = []
    for part in parts:
        if not part:
            continue
        if isinstance(part, str):
            tokens.extend(tokenize(part))
        else:
            for value in part:
                tokens.extend(tokenize(value or ""))
    uniq = list(dict.fromkeys(tokens))
    return " ".join(uniq)
