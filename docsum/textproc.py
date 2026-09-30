"""Language detection, paragraph/sentence splitting and word normalization
for English and Turkish text. Pure Python, no network, no models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Literal

from .stopwords import BY_LANGUAGE, EN, TR

Lang = Literal["en", "tr"]

TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
UPPER = "A-ZÇĞİÖŞÜÂÎÛ"


def lower(text: str, lang: Lang) -> str:
    if lang == "tr":
        # Turkish dotted/dotless i: I -> ı, İ -> i.
        text = text.replace("I", "ı").replace("İ", "i")
    return text.lower()


def detect_language(text: str) -> Lang:
    sample = text[:50_000]
    words = [w.lower() for w in WORD_RE.findall(sample)]
    if not words:
        return "en"
    en = sum(w in EN for w in words)
    tr = sum(w in TR for w in words)
    tr += sum(c in TURKISH_CHARS for c in sample) / 3
    return "tr" if tr > en else "en"


def words(text: str, lang: Lang) -> list[str]:
    """Lowercased words. Turkish suffixes after an apostrophe (Ankara'da) are dropped."""
    out = []
    for token in re.split(r"\s+", text):
        token = re.split(r"['’]", token, maxsplit=1)[0]
        out.extend(WORD_RE.findall(lower(token, lang)))
    return out


_EN_SUFFIXES = (
    "izations", "ization", "ational", "fulness", "iveness", "ousness", "ations", "ation",
    "ments", "ment", "ness", "ings", "ing", "ities", "ity", "ies", "ied", "edly", "ed",
    "ly", "es", "s",
)


def stem(word: str, lang: Lang) -> str:
    if lang == "tr":
        # Turkish is agglutinative; the first five letters are a well-known,
        # surprisingly effective stand-in for the root (e.g. sözleşmenin -> sözle).
        return word[:5]
    for suffix in _EN_SUFFIXES:
        if suffix == "es" and not word.endswith(("sses", "xes", "zes", "ches", "shes")):
            continue  # "employees" -> "employee" (via "s"), but "boxes" -> "box"
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            base = word[: -len(suffix)]
            return base + "y" if suffix in ("ies", "ied", "ities") else base
    return word


def content_terms(text: str, lang: Lang) -> list[str]:
    """Stems of the meaningful words in text (stopwords and short words removed)."""
    stop = BY_LANGUAGE[lang]
    return [stem(w, lang) for w in words(text, lang) if len(w) > 2 and w not in stop]


# ---------------------------------------------------------------- structure

HEADING_PREFIX = re.compile(
    rf"^(\d+(\.\d+)*\.?|[IVXLC]+\.|[{UPPER}]\)|madde\s+\d+|article\s+\d+|section\s+\d+|"
    rf"bölüm\s+\d+|chapter\s+\d+|ek\s*[-–]?\s*\d+|annex\s+\d+|appendix\s+[A-Z0-9]+)\b",
    re.IGNORECASE,
)
LIST_ITEM = re.compile(r"^([-•*▪◦·–]|\(?[0-9a-zA-Z]{1,3}[.)])\s+")


def is_heading(line: str, mid_sentence: bool = False) -> bool:
    """Guess whether a line is a heading. mid_sentence: the previous line ended
    without closing its sentence, so only unmistakable headings count."""
    if line.startswith("## "):
        return True
    if len(line) > 90 or line.endswith((".", ",", ";", "?", "!")):
        return False
    tokens = line.split()
    if not tokens or len(tokens) > 12:
        return False
    letters = [c for c in line if c.isalpha()]
    if len(letters) < 3:
        return False
    if all(c.isupper() for c in letters):
        return True
    if mid_sentence:
        return False
    prefix = HEADING_PREFIX.match(line)
    if prefix and len(tokens) <= 10:
        rest = line[prefix.end():].lstrip(" .–-:)")
        return not rest or rest[0].isupper()
    capitalized = sum(t[0].isupper() for t in tokens if t[0].isalpha())
    alpha_tokens = sum(t[0].isalpha() for t in tokens)
    return len(tokens) >= 2 and alpha_tokens > 0 and capitalized / alpha_tokens >= 0.75


@dataclass
class Block:
    kind: Literal["heading", "text"]
    text: str


def blocks(text: str) -> Iterator[Block]:
    """Headings and paragraphs, with hard-wrapped PDF lines joined back up."""
    for chunk in re.split(r"\n\s*\n", text):
        buffer: list[str] = []

        def flush() -> Iterator[Block]:
            if buffer:
                yield Block("text", " ".join(buffer))
                buffer.clear()

        for raw in chunk.split("\n"):
            line = raw.strip()
            if not line:
                continue
            if " | " in line:  # table row from DOCX: keep as its own block
                yield from flush()
                yield Block("text", line)
            elif is_heading(line, mid_sentence=bool(buffer) and not buffer[-1].endswith((".", "!", "?"))):
                yield from flush()
                yield Block("heading", line.removeprefix("## ").strip())
            elif LIST_ITEM.match(line):
                yield from flush()
                buffer.append(line)
            elif buffer and buffer[-1].endswith("-") and line[:1].islower():
                buffer[-1] = buffer[-1][:-1] + line  # re-join hyphenated word
            else:
                buffer.append(line)
        yield from flush()


# ---------------------------------------------------------------- sentences

ABBREVIATIONS = {
    "en": {
        "mr", "mrs", "ms", "dr", "prof", "inc", "ltd", "co", "corp", "vs", "etc", "e.g", "i.e",
        "no", "nos", "fig", "art", "sec", "para", "p", "pp", "vol", "ch", "approx", "est", "dept",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
        "st", "jr", "sr", "u.s", "u.k", "a.m", "p.m", "ref", "min", "max",
    },
    "tr": {
        "dr", "prof", "doç", "av", "sn", "vb", "vs", "örn", "bkz", "no", "md", "s", "sy", "yy",
        "yrd", "ltd", "şti", "a.ş", "tel", "cad", "sok", "mah", "apt", "hz", "müh", "uzm", "op",
        "alb", "gen", "t.c", "tic", "san", "ort", "vd", "krş", "çev", "ed", "haz",
    },
}

BOUNDARY = re.compile(rf"([.!?…]+)([\"'”’)\]]*)\s+(?=[\"“(\[]?[{UPPER}0-9])")


def split_sentences(paragraph: str, lang: Lang) -> list[str]:
    abbreviations = ABBREVIATIONS[lang]
    sentences, start = [], 0
    for m in BOUNDARY.finditer(paragraph):
        before = paragraph[start : m.start()]
        prev = before.rsplit(None, 1)[-1] if before.split() else ""
        prev_l = lower(prev, lang).strip("(\"'“")
        if m.group(1) == ".":
            if prev_l in abbreviations or (len(prev_l) == 1 and prev_l.isalpha()):
                continue  # "Dr. Smith", "J. Doe"
            if prev_l.isdigit() and lang == "tr":
                continue  # Turkish ordinals: "5. madde", "2. Bölüm"
        sentences.append(paragraph[start : m.end(2)].strip())
        start = m.end()
    tail = paragraph[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences
