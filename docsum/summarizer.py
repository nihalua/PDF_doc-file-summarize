"""Summarize a loaded document with Claude, in English or Turkish.

Short documents go to Claude in a single request. Documents too long for one
request are split into sections, each section is condensed into notes, and
the final summary is written from those notes (map-reduce).
"""

from __future__ import annotations

import base64
import json
from typing import Callable, Literal

import anthropic
from pydantic import BaseModel, ValidationError

from .extract import LoadedDocument

MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

Language = Literal["en", "tr"]
Detail = Literal["brief", "standard", "detailed"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]

LANGUAGE_NAMES = {"en": "English", "tr": "Turkish (Türkçe)"}

# ~3 characters per token is a conservative estimate for Turkish; English is
# closer to 4. The model has a 1M-token context; leave room for instructions
# and output.
CHARS_PER_TOKEN = 3
SINGLE_PASS_MAX_TOKENS = 600_000
CHUNK_TOKENS = 120_000


class KeyDetail(BaseModel):
    label: str
    value: str


class DocumentSummary(BaseModel):
    title: str
    document_type: str
    source_language: str
    purpose: str
    executive_summary: str
    key_points: list[str]
    important_details: list[KeyDetail]
    action_items: list[str]
    conclusion: str


# Hand-written so it meets structured-output rules (no extra keywords,
# additionalProperties false, every field required).
SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "document_type": {"type": "string"},
        "source_language": {"type": "string"},
        "purpose": {"type": "string"},
        "executive_summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "important_details": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
                "required": ["label", "value"],
                "additionalProperties": False,
            },
        },
        "action_items": {"type": "array", "items": {"type": "string"}},
        "conclusion": {"type": "string"},
    },
    "required": list(DocumentSummary.model_fields),
    "additionalProperties": False,
}

DETAIL_GUIDANCE = {
    "brief": "Keep it tight: a 2-3 sentence executive summary and the 3-5 most important key points.",
    "standard": "Write a one-paragraph executive summary and roughly 5-10 key points.",
    "detailed": (
        "Be thorough: a multi-paragraph executive summary and as many key points as the "
        "document genuinely warrants (often 10-20), covering every major section."
    ),
}


class SummaryError(Exception):
    """Summarization failed in a way worth showing to the user."""


ProgressFn = Callable[[str], None]


def _system_prompt(language: Language, detail: Detail) -> str:
    lang = LANGUAGE_NAMES[language]
    return f"""You summarize long documents for busy readers who need to understand \
what a document is for and what matters in it without reading it all.

Write every field of your answer in {lang}, whatever language the document is in. \
Keep proper names, product names, legal references and quoted figures exactly as \
they appear in the source.

What each field should contain:
- title: the document's title, or a short descriptive title if it has none.
- document_type: what kind of document this is (e.g. contract, research paper, \
policy, report, meeting minutes, user manual).
- source_language: the language the document itself is written in, named in {lang}.
- purpose: why this document exists and what it is trying to achieve, for whom - \
two or three sentences. This is the most important field; be specific, not generic.
- executive_summary: the substance of the document as a reader would want it retold.
- key_points: the most important findings, decisions, arguments, terms or \
conclusions, each one self-contained and concrete. Most important first.
- important_details: concrete facts a reader may need to look up later - dates, \
deadlines, amounts, percentages, parties, names, reference numbers. Each has a \
short label and its value. Empty list if the document has none.
- action_items: obligations, requirements, recommendations or next steps the \
document places on anyone, stating who when the document says. Empty list if none.
- conclusion: the document's overall conclusion or bottom line.

{DETAIL_GUIDANCE[detail]}

Only state what the document supports. If part of the document is unreadable or \
ambiguous, say so rather than guessing."""


def _doc_block(doc: LoadedDocument, pdf_bytes: bytes | None = None, text: str | None = None) -> dict:
    if pdf_bytes is not None:
        source = {
            "type": "base64",
            "media_type": "application/pdf",
            "data": base64.b64encode(pdf_bytes).decode("ascii"),
        }
    else:
        source = {"type": "text", "media_type": "text/plain", "data": text or ""}
    # Cache the document so re-summarizing it (other language or detail level)
    # within a few minutes costs a fraction of the input price.
    return {
        "type": "document",
        "source": source,
        "title": doc.filename,
        "cache_control": {"type": "ephemeral"},
    }


def _call(
    client: anthropic.Anthropic,
    *,
    system: str,
    content: list[dict],
    effort: Effort,
    schema: dict | None = None,
    max_tokens: int = 32_000,
) -> str:
    output_config: dict = {"effort": effort}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}

    # Streaming: long documents plus thinking can exceed a non-streaming
    # request's HTTP timeout.
    try:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config=output_config,
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        raise SummaryError("Invalid or missing Anthropic API key (ANTHROPIC_API_KEY).") from e
    except anthropic.RateLimitError as e:
        raise SummaryError("Rate limited by the Anthropic API. Please wait and retry.") from e
    except anthropic.BadRequestError as e:
        raise SummaryError(f"The API rejected the request: {e.message}") from e
    except anthropic.APIStatusError as e:
        raise SummaryError(f"Anthropic API error ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise SummaryError("Could not reach the Anthropic API. Check your connection.") from e

    if message.stop_reason == "refusal":
        raise SummaryError("The model declined to summarize this document.")
    if message.stop_reason == "max_tokens":
        raise SummaryError("The summary was cut off (output limit reached). Try a briefer detail level.")

    return "".join(b.text for b in message.content if b.type == "text")


def _parse_summary(raw: str) -> DocumentSummary:
    try:
        return DocumentSummary.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as e:
        raise SummaryError(f"Could not parse the model's summary: {e}") from e


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into pieces of at most max_chars, preferring paragraph breaks."""
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for para in text.split("\n\n"):
        # A single paragraph larger than a chunk gets hard-split.
        while len(para) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current, size = [], 0
            chunks.append(para[:max_chars])
            para = para[max_chars:]
        if size + len(para) + 2 > max_chars and current:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(para)
        size += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return [c for c in chunks if c.strip()]


def _section_notes(
    client: anthropic.Anthropic,
    doc: LoadedDocument,
    index: int,
    total: int,
    effort: Effort,
    *,
    text: str | None = None,
    pdf_bytes: bytes | None = None,
) -> str:
    system = (
        "You are condensing one section of a long document so that a later step can "
        "summarize the whole document from your notes. Write detailed, faithful notes in "
        "English: the section's topics, arguments, findings, decisions, obligations, and "
        "every concrete date, amount, name, and reference number. Note anything that hints "
        "at the overall document's purpose. No preamble."
    )
    content = [
        _doc_block(doc, pdf_bytes=pdf_bytes, text=text),
        {"type": "text", "text": f"This is section {index} of {total}. Write the notes."},
    ]
    return _call(client, system=system, content=content, effort=effort, max_tokens=16_000)


def summarize(
    doc: LoadedDocument,
    language: Language = "en",
    detail: Detail = "standard",
    effort: Effort = "medium",
    client: anthropic.Anthropic | None = None,
    progress: ProgressFn | None = None,
) -> DocumentSummary:
    client = client or anthropic.Anthropic()
    report = progress or (lambda _msg: None)
    system = _system_prompt(language, detail)
    instruction = {"type": "text", "text": "Summarize this document."}

    # Split into sections only when one request can't hold the whole document.
    if doc.is_pdf:
        sections = [("pdf", b) for b in doc.pdf_batches]
    else:
        text = doc.text or ""
        if len(text) <= SINGLE_PASS_MAX_TOKENS * CHARS_PER_TOKEN:
            sections = [("text", text)]
        else:
            sections = [("text", c) for c in chunk_text(text, CHUNK_TOKENS * CHARS_PER_TOKEN)]

    if len(sections) == 1:
        kind, payload = sections[0]
        report("Reading and summarizing the document…")
        block = _doc_block(doc, pdf_bytes=payload if kind == "pdf" else None,
                           text=payload if kind == "text" else None)
        raw = _call(client, system=system, content=[block, instruction],
                    effort=effort, schema=SUMMARY_SCHEMA)
        return _parse_summary(raw)

    notes = []
    for i, (kind, payload) in enumerate(sections, start=1):
        report(f"Long document: reading section {i} of {len(sections)}…")
        notes.append(
            _section_notes(
                client, doc, i, len(sections), effort,
                pdf_bytes=payload if kind == "pdf" else None,
                text=payload if kind == "text" else None,
            )
        )

    report("Combining section notes into the final summary…")
    combined = "\n\n".join(
        f"=== Notes on section {i} of {len(notes)} ===\n{n}" for i, n in enumerate(notes, start=1)
    )
    content = [
        {"type": "text", "text": (
            f"The document '{doc.filename}' was too long to read at once, so it was split "
            f"into {len(notes)} consecutive sections and each was condensed into notes. "
            f"Summarize the whole document from these notes.\n\n{combined}"
        )},
    ]
    raw = _call(client, system=system, content=content, effort=effort, schema=SUMMARY_SCHEMA)
    return _parse_summary(raw)
