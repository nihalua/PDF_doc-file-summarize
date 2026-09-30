"""Render a DocumentSummary as Markdown, with labels in English or Turkish.

The quoted sentences stay in the document's own language: they are taken
from the document, not written or translated.
"""

from __future__ import annotations

from typing import Literal

from .summarizer import DocumentSummary, Point

UiLang = Literal["en", "tr"]

LABELS = {
    "en": {
        "language": "Document language",
        "lang_en": "English",
        "lang_tr": "Turkish",
        "length": "Length",
        "pages": "pages",
        "words": "words",
        "reading": "min read",
        "note": "Offline summary: the sentences below are quoted from the document itself.",
        "purpose": "Purpose of the document",
        "purpose_guess": "Purpose of the document (best guess: no explicit statement of purpose was found)",
        "overview": "Overview",
        "key_points": "Key points",
        "keywords": "Main topics",
        "outline": "Structure",
        "facts": "Important details",
        "kinds": {
            "date": "Dates", "amount": "Amounts", "percentage": "Percentages",
            "time_limit": "Time limits", "reference": "References", "email": "E-mail addresses",
        },
        "obligations": "Obligations & requirements",
        "page": "p.",
    },
    "tr": {
        "language": "Belgenin dili",
        "lang_en": "İngilizce",
        "lang_tr": "Türkçe",
        "length": "Uzunluk",
        "pages": "sayfa",
        "words": "kelime",
        "reading": "dk okuma",
        "note": "Çevrimdışı özet: aşağıdaki cümleler doğrudan belgeden alınmıştır.",
        "purpose": "Belgenin amacı",
        "purpose_guess": "Belgenin amacı (tahmini: belgede açık bir amaç ifadesi bulunamadı)",
        "overview": "Genel bakış",
        "key_points": "Önemli noktalar",
        "keywords": "Ana konular",
        "outline": "Yapı",
        "facts": "Önemli ayrıntılar",
        "kinds": {
            "date": "Tarihler", "amount": "Tutarlar", "percentage": "Oranlar",
            "time_limit": "Süreler", "reference": "Atıflar", "email": "E-posta adresleri",
        },
        "obligations": "Yükümlülükler ve gereklilikler",
        "page": "s.",
    },
}


def _cite(p: Point, label: str) -> str:
    return f" *({label} {p.page})*" if p.page else ""


def to_markdown(s: DocumentSummary, ui: UiLang = "en") -> str:
    L = LABELS[ui]
    length = [f"{s.word_count:,} {L['words']}", f"~{s.reading_minutes} {L['reading']}"]
    if s.page_count:
        length.insert(0, f"{s.page_count} {L['pages']}")
    out = [
        f"# {s.title}",
        "",
        f"**{L['language']}:** {L['lang_' + s.language]}  ",
        f"**{L['length']}:** {' · '.join(length)}",
        "",
        f"> {L['note']}",
        "",
        f"## {L['purpose'] if s.purpose_from_cues else L['purpose_guess']}",
        *[f"- {p.text}{_cite(p, L['page'])}" for p in s.purpose],
        "",
        f"## {L['overview']}",
        " ".join(p.text for p in s.overview),
        "",
        f"## {L['key_points']}",
        *[f"- {p.text}{_cite(p, L['page'])}" for p in s.key_points],
    ]
    if s.obligations:
        out += ["", f"## {L['obligations']}", *[f"- {p.text}{_cite(p, L['page'])}" for p in s.obligations]]
    if s.facts:
        out += ["", f"## {L['facts']}"]
        for kind, heading in L["kinds"].items():
            items = [f for f in s.facts if f.kind == kind]
            if not items:
                continue
            out += ["", f"**{heading}**", "", "| | |", "|---|---|"]
            for f in items:
                where = f" ({L['page']} {f.page})" if f.page else ""
                context = f.context.replace("|", "/").replace("\n", " ")
                out.append(f"| **{f.value}**{where} | {context} |")
    if s.keywords or s.key_phrases:
        out += ["", f"## {L['keywords']}", ", ".join(s.key_phrases + s.keywords)]
    if len(s.outline) >= 2:
        out += ["", f"## {L['outline']}", *[f"- {p.text}{_cite(p, L['page'])}" for p in s.outline]]
    out.append("")
    return "\n".join(out)
