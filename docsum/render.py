"""Render a DocumentSummary as Markdown with headings in the output language."""

from __future__ import annotations

from .summarizer import DocumentSummary, Language

HEADINGS = {
    "en": {
        "type": "Document type",
        "language": "Original language",
        "purpose": "Purpose of the document",
        "summary": "Summary",
        "key_points": "Key points",
        "details": "Important details",
        "actions": "Action items & obligations",
        "conclusion": "Conclusion",
    },
    "tr": {
        "type": "Belge türü",
        "language": "Orijinal dil",
        "purpose": "Belgenin amacı",
        "summary": "Özet",
        "key_points": "Önemli noktalar",
        "details": "Önemli ayrıntılar",
        "actions": "Yapılacaklar ve yükümlülükler",
        "conclusion": "Sonuç",
    },
}


def to_markdown(s: DocumentSummary, language: Language) -> str:
    h = HEADINGS[language]
    out = [
        f"# {s.title}",
        "",
        f"**{h['type']}:** {s.document_type}  ",
        f"**{h['language']}:** {s.source_language}",
        "",
        f"## {h['purpose']}",
        s.purpose,
        "",
        f"## {h['summary']}",
        s.executive_summary,
        "",
        f"## {h['key_points']}",
        *[f"- {p}" for p in s.key_points],
    ]
    if s.important_details:
        out += ["", f"## {h['details']}", "", "| | |", "|---|---|"]
        out += [f"| {d.label} | {d.value.replace('|', '/')} |" for d in s.important_details]
    if s.action_items:
        out += ["", f"## {h['actions']}", *[f"- {a}" for a in s.action_items]]
    out += ["", f"## {h['conclusion']}", s.conclusion, ""]
    return "\n".join(out)
