"""Offline, extractive summarization for English and Turkish documents.

No AI model and no network: the summary is built from the document's own
sentences. Each sentence is scored by how well it represents the document's
main vocabulary (TF-IDF centroid similarity), with small boosts for early
position and overlap with the title and headings. A diversity step (MMR)
avoids picking several sentences that say the same thing.

Purpose and obligations come from cue phrases ("the purpose of", "amacı",
"shall", "yükümlüdür", ...); concrete details come from patterns
(dates, amounts, percentages, time limits, references).
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Literal

from . import textproc
from .details import find_details
from .extract import LoadedDocument
from .stopwords import BY_LANGUAGE
from .textproc import Lang

Detail = Literal["brief", "standard", "detailed"]

KEY_POINTS = {"brief": 5, "standard": 10, "detailed": 20}
# ...but never more than this share of the document's sentences.
KEY_POINT_SHARE = {"brief": 0.1, "standard": 0.17, "detailed": 0.3}
OVERVIEW_SENTENCES = {"brief": 2, "standard": 3, "detailed": 5}
MAX_ITEMS = {"brief": 5, "standard": 10, "detailed": 25}

# Explicit statements of purpose, then weaker hints ("this report describes").
PURPOSE_CUES = {
    "en": re.compile(
        r"\b(the (main |primary |overall )?(purpose|aim|objective|goal)s? of|aims? to|is intended to|"
        r"(is|are) designed to|seeks? to|we propose)\b",
        re.IGNORECASE,
    ),
    "tr": re.compile(
        r"(amacı|amacıyla|amaçlanma|amaçla|hedeflenme|hedefi|konusu|ilişkin usul ve esasları)",
        re.IGNORECASE,
    ),
}
WEAK_PURPOSE_CUES = {
    "en": re.compile(
        r"\bthis (document|report|agreement|contract|policy|paper|study|memo|guide|manual|proposal|"
        r"plan|procedure) (sets out|describes|defines|provides|establishes|outlines|explains|presents|"
        r"covers|governs|applies)|\bscope of\b",
        re.IGNORECASE,
    ),
    "tr": re.compile(
        r"(bu (belge|rapor|sözleşme|yönetmelik|yönerge|politika|çalışma|doküman|protokol|şartname|"
        r"prosedür|makale|tez)|kapsamı|düzenlemek|belirlemek)",
        re.IGNORECASE,
    ),
}

OBLIGATION_CUES = {
    "en": re.compile(
        r"\b(shall|must|is required to|are required to|is obliged to|are obliged to|is responsible for|"
        r"are responsible for|agrees? to|undertakes? to|no later than|deadline|should|is prohibited|"
        r"may not|must not|shall not|is entitled to|required|mandatory|recommend(s|ed)?)\b",
        re.IGNORECASE,
    ),
    "tr": re.compile(
        r"(zorundadır|zorunludur|yükümlüdür|yükümlülüğündedir|mecburdur|sorumludur|gerekmektedir|"
        r"gerekir|gereklidir|şarttır|mal[ıi]d[ıi]r|mel[ıi]d[ıi]r|en geç|yasaktır|edemez|yapamaz|"
        r"hakkına sahiptir|taahhüt eder|kabul eder|önerilir|önerilmektedir|tavsiye edilir)",
        re.IGNORECASE,
    ),
}


@dataclass
class Sentence:
    text: str
    page: int | None
    index: int
    section: str | None
    terms: list[str]
    vector: dict[str, float] = field(default_factory=dict)
    score: float = 0.0


@dataclass
class Fact:
    kind: str
    value: str
    page: int | None
    context: str


@dataclass
class Point:
    text: str
    page: int | None


@dataclass
class DocumentSummary:
    title: str
    language: Lang
    page_count: int | None
    word_count: int
    reading_minutes: int
    purpose: list[Point]
    purpose_from_cues: bool
    overview: list[Point]
    key_points: list[Point]
    keywords: list[str]
    key_phrases: list[str]
    outline: list[Point]
    facts: list[Fact]
    obligations: list[Point]


class SummaryError(Exception):
    """The document couldn't be summarized."""


# ---------------------------------------------------------------- segmentation

def _segment(doc: LoadedDocument, lang: Lang) -> tuple[list[Sentence], list[Point]]:
    sentences: list[Sentence] = []
    headings: list[Point] = []
    section = None
    for page_no, page in enumerate(doc.pages, start=1):
        page_ref = page_no if doc.page_count else None
        for block in textproc.blocks(page):
            if block.kind == "heading":
                section = block.text
                headings.append(Point(block.text, page_ref))
                continue
            if " | " in block.text:
                continue  # table rows: details are still mined below, not summarized
            for text in textproc.split_sentences(block.text, lang):
                n_words = len(text.split())
                if n_words < 5 or n_words > 120:
                    continue
                letters = sum(c.isalpha() for c in text)
                if letters < 0.5 * len(text):
                    continue  # mostly numbers or symbols
                sentences.append(Sentence(
                    text=text, page=page_ref, index=len(sentences), section=section,
                    terms=textproc.content_terms(text, lang),
                ))
    return sentences, headings


# ---------------------------------------------------------------- scoring

def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def _normalize(vec: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in vec.values()))
    return {k: v / norm for k, v in vec.items()} if norm else {}


def _score(sentences: list[Sentence], title_terms: set[str], heading_terms: set[str]) -> None:
    n = len(sentences)
    df = Counter(t for s in sentences for t in set(s.terms))
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}

    centroid: dict[str, float] = defaultdict(float)
    for s in sentences:
        tf = Counter(s.terms)
        s.vector = _normalize({t: (1 + math.log(c)) * idf[t] for t, c in tf.items()})
        for t, v in s.vector.items():
            centroid[t] += v
    # The document's topic signature: its 150 strongest terms.
    top = dict(sorted(centroid.items(), key=lambda kv: -kv[1])[:150])
    centroid_vec = _normalize(top)

    for s in sentences:
        score = _cosine(s.vector, centroid_vec)
        position = s.index / max(n - 1, 1)
        if position < 0.1:
            score *= 1.25
        elif position > 0.9:
            score *= 1.05  # conclusions often sit at the end
        if s.terms:
            unique = set(s.terms)
            score += 0.15 * len(unique & title_terms) / len(unique)
            score += 0.10 * len(unique & heading_terms) / len(unique)
        n_words = len(s.text.split())
        if n_words < 8:
            score *= 0.7
        elif n_words > 50:
            score *= 0.85
        s.score = score


def _select(candidates: list[Sentence], k: int, exclude: set[int] = frozenset(), diversity: float = 0.3) -> list[Sentence]:
    """Maximal marginal relevance: high score, low overlap with what's already chosen."""
    pool = sorted((s for s in candidates if s.index not in exclude), key=lambda s: -s.score)[:400]
    if not pool:
        return []
    top_score = pool[0].score or 1.0
    chosen: list[Sentence] = []
    while pool and len(chosen) < k:
        best = max(
            pool,
            key=lambda s: (1 - diversity) * s.score / top_score
            - diversity * max((_cosine(s.vector, c.vector) for c in chosen), default=0.0),
        )
        chosen.append(best)
        pool.remove(best)
    return sorted(chosen, key=lambda s: s.index)


# ---------------------------------------------------------------- pieces

def _title(doc: LoadedDocument, headings: list[Point]) -> str:
    first_page = doc.pages[0] if doc.pages else ""
    for block in textproc.blocks(first_page):
        if block.kind == "heading" and len(block.text) > 3:
            return block.text
        break
    if headings and (headings[0].page in (None, 1)):
        return headings[0].text
    stem = doc.filename.rsplit(".", 1)[0]
    return re.sub(r"[_-]+", " ", stem).strip() or doc.filename


def _keywords(sentences: list[Sentence], lang: Lang) -> tuple[list[str], list[str]]:
    stop = BY_LANGUAGE[lang]
    counts: Counter[str] = Counter()
    surface: dict[str, Counter[str]] = defaultdict(Counter)
    bigrams: Counter[tuple[str, str]] = Counter()
    bigram_surface: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for s in sentences:
        text = re.sub(r"\S+@\S+|https?://\S+|www\.\S+", " ", s.text)
        # Word pairs never span punctuation ("Kiracı, taşınmazı" is not a phrase).
        for segment in re.split(r"[,;:.()\[\]\"“”!?/–-]", text):
            prev = None
            for w in textproc.words(segment, lang):
                if len(w) <= 2 or w in stop:
                    prev = None
                    continue
                st = textproc.stem(w, lang)
                counts[st] += 1
                surface[st][w] += 1
                if prev:
                    key = (prev[0], st)
                    bigrams[key] += 1
                    bigram_surface[key][f"{prev[1]} {w}"] += 1
                prev = (st, w)
    phrases = [
        bigram_surface[key].most_common(1)[0][0]
        for key, c in bigrams.most_common(8)
        if c >= 2
    ]
    in_phrases = {textproc.stem(w, lang) for p in phrases for w in p.split()}
    keywords = [
        surface[st].most_common(1)[0][0]
        for st, c in counts.most_common(40)
        if st not in in_phrases and c >= 2
    ]
    return keywords, phrases


def _purpose(sentences: list[Sentence], lang: Lang) -> tuple[list[Sentence], bool]:
    if not sentences:
        return [], False
    head = sentences[: max(40, len(sentences) // 4)]
    for cues in (PURPOSE_CUES[lang], WEAK_PURPOSE_CUES[lang]):
        matches = [s for s in head if cues.search(s.text)]
        if matches:
            # More representative and earlier first.
            ranked = sorted(matches, key=lambda s: -(s.score + 0.5 / (1 + s.index)))[:2]
            return sorted(ranked, key=lambda s: s.index), True
    best = max(sentences[: max(10, len(sentences) // 10)], key=lambda s: s.score)
    return [best], False


def _obligations(sentences: list[Sentence], lang: Lang, limit: int) -> list[Sentence]:
    cue = OBLIGATION_CUES[lang]
    hits = [(len(cue.findall(s.text)), s) for s in sentences]
    hits = [(n, s) for n, s in hits if n]
    ranked = sorted(hits, key=lambda ns: -(ns[1].score + 0.05 * ns[0]))[:limit]
    return sorted((s for _, s in ranked), key=lambda s: s.index)


def _facts(doc: LoadedDocument, lang: Lang, limit: int) -> list[Fact]:
    seen: set[tuple[str, str]] = set()
    per_kind: Counter[str] = Counter()
    facts: list[Fact] = []
    for page_no, page in enumerate(doc.pages, start=1):
        page_ref = page_no if doc.page_count else None
        for block in textproc.blocks(page):
            if block.kind == "heading":
                continue
            for sentence in textproc.split_sentences(block.text, lang):
                for kind, value in find_details(sentence):
                    key = (kind, re.sub(r"\s+", " ", value.lower()))
                    if key in seen or per_kind[kind] >= limit:
                        continue
                    seen.add(key)
                    per_kind[kind] += 1
                    context = sentence if len(sentence) <= 220 else _window(sentence, value, 220)
                    facts.append(Fact(kind, value, page_ref, context))
    return facts


def _window(text: str, value: str, width: int) -> str:
    i = max(text.find(value), 0)
    start = max(0, i - width // 2)
    end = min(len(text), start + width)
    return ("…" if start else "") + text[start:end].strip() + ("…" if end < len(text) else "")


# ---------------------------------------------------------------- entry point

def summarize(doc: LoadedDocument, detail: Detail = "standard") -> DocumentSummary:
    lang = textproc.detect_language(doc.text)
    sentences, headings = _segment(doc, lang)
    if len(sentences) < 2:
        raise SummaryError(
            "Not enough readable text was found in this document to summarize."
        )

    title = _title(doc, headings)
    title_terms = set(textproc.content_terms(title, lang))
    heading_terms = {t for h in headings for t in textproc.content_terms(h.text, lang)}
    _score(sentences, title_terms, heading_terms)

    purpose, from_cues = _purpose(sentences, lang)
    obligations = _obligations(sentences, lang, MAX_ITEMS[detail])
    used = {s.index for s in purpose}

    n_overview = min(OVERVIEW_SENTENCES[detail], max(1, len(sentences) // 10))
    overview = _select(sentences, n_overview, exclude=used, diversity=0.4)
    used |= {s.index for s in overview}

    # Key points complement the obligations list rather than repeating it,
    # unless the document is mostly obligations (a contract, say).
    n_points = min(KEY_POINTS[detail], max(3, round(len(sentences) * KEY_POINT_SHARE[detail])))
    key_points = _select(sentences, n_points, exclude=used | {s.index for s in obligations})
    if len(key_points) < min(3, n_points):
        key_points = _select(sentences, n_points, exclude=used)

    keywords, phrases = _keywords(sentences, lang)
    word_count = len(doc.text.split())
    n_keywords = {"brief": 8, "standard": 12, "detailed": 15}[detail]

    return DocumentSummary(
        title=title,
        language=lang,
        page_count=doc.page_count,
        word_count=word_count,
        reading_minutes=max(1, round(word_count / 200)),
        purpose=[Point(s.text, s.page) for s in purpose],
        purpose_from_cues=from_cues,
        overview=[Point(s.text, s.page) for s in overview],
        key_points=[Point(s.text, s.page) for s in key_points],
        keywords=keywords[: max(0, n_keywords - len(phrases))],
        key_phrases=phrases,
        outline=headings[:40],
        facts=_facts(doc, lang, MAX_ITEMS[detail]),
        obligations=[Point(s.text, s.page) for s in obligations],
    )
