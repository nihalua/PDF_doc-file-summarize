"""Find concrete facts in sentences: dates, money amounts, percentages,
time limits, references to articles/sections, and e-mail addresses."""

from __future__ import annotations

import re

EN_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december|"
    "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)
TR_MONTHS = "ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık"
MONTHS = f"{EN_MONTHS}|{TR_MONTHS}"

NUMBER = r"\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
CURRENCY_WORDS = (
    r"TL|TRY|₺|USD|EUR|GBP|CHF|Türk\s+Lirası|lira|dollars?|euros?|pounds?|dolar|avro"
)
MULTIPLIER = r"million|billion|milyon|milyar|bin|thousand|bn"

PATTERNS: dict[str, re.Pattern] = {
    "date": re.compile(
        rf"\b(?:\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}|\d{{4}}-\d{{2}}-\d{{2}}|"
        rf"\d{{1,2}}\s+(?:{MONTHS})\.?,?\s+\d{{4}}|(?:{MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}|"
        rf"(?:{MONTHS})\s+\d{{4}})\b",
        re.IGNORECASE,
    ),
    "amount": re.compile(
        rf"(?:[$€£₺]\s?(?:{NUMBER})(?:\s?(?:{MULTIPLIER}|m|k)\b)?"
        rf"|\b(?:{NUMBER})\s?(?:(?:{MULTIPLIER})\s)?(?:{CURRENCY_WORDS})(?![\w]))",
        re.IGNORECASE,
    ),
    "percentage": re.compile(rf"(?:%\s?(?:{NUMBER})|\byüzde\s(?:{NUMBER})|\b(?:{NUMBER})\s?(?:%|percent|per cent)(?!\w))", re.IGNORECASE),
    "time_limit": re.compile(
        r"\b(?:within|no later than|at least|at most|up to|en geç|en az|en fazla|içinde|süresince)?\s?"
        r"\d+\s?(?:\(\w+\)\s?)?(?:business\s+|working\s+|calendar\s+|iş\s+)?"
        r"(?:days?|weeks?|months?|years?|hours?|gün|hafta|ay|yıl|saat)"
        r"(?:\s+(?:içinde|içerisinde|önce|sonra|süreyle))?\b",
        re.IGNORECASE,
    ),
    "reference": re.compile(
        r"\b(?:(?:article|section|clause|annex|appendix|schedule|chapter|madde|bölüm|fıkra|ek)\s+"
        r"\d+(?:\.\d+)*(?:\s?\([a-z0-9]+\))?|\d+(?:\.\d+)*\.?\s+madde(?:si|de|ye)?)\b",
        re.IGNORECASE,
    ),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
}

# Numbers alone ("30 days") often appear inside a date or amount already found.
_TIME_UNIT_ONLY = re.compile(r"^\s*$")


def find_details(sentence: str) -> list[tuple[str, str]]:
    """(kind, matched text) pairs in the sentence, without overlaps."""
    found: list[tuple[int, int, str, str]] = []
    for kind, pattern in PATTERNS.items():
        for m in pattern.finditer(sentence):
            value = m.group(0).strip(" ,.;:")
            if not value or _TIME_UNIT_ONLY.match(value):
                continue
            s, e = m.span()
            if any(s < fe and e > fs for fs, fe, _, _ in found):
                continue  # already covered by an earlier (more specific) kind
            found.append((s, e, kind, value))
    return [(kind, value) for _, _, kind, value in sorted(found)]
