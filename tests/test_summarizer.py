import json
from types import SimpleNamespace

import pytest

from docsum import summarizer
from docsum.extract import LoadedDocument
from docsum.render import to_markdown
from docsum.summarizer import SummaryError, chunk_text, summarize

SUMMARY = {
    "title": "Kira Sözleşmesi",
    "document_type": "Sözleşme",
    "source_language": "Türkçe",
    "purpose": "Kiracı ile mal sahibi arasındaki kira şartlarını belirlemek.",
    "executive_summary": "Özet metni.",
    "key_points": ["Birinci nokta", "İkinci nokta"],
    "important_details": [{"label": "Kira bedeli", "value": "10.000 TL"}],
    "action_items": ["Kiracı her ayın 5'ine kadar öder."],
    "conclusion": "Sonuç.",
}


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    def __init__(self, stop_reason="end_turn"):
        self.calls = []
        self.stop_reason = stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kwargs):
        self.calls.append(kwargs)
        fmt = kwargs["output_config"].get("format")
        text = json.dumps(SUMMARY) if fmt else f"notes {len(self.calls)}"
        return FakeStream(SimpleNamespace(
            stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        ))


def test_single_pass_pdf():
    client = FakeClient()
    doc = LoadedDocument("a.pdf", pdf_batches=[b"%PDF-1.4"], page_count=1)
    s = summarize(doc, language="tr", client=client)
    assert s.title == "Kira Sözleşmesi"
    call = client.calls[0]
    assert len(client.calls) == 1
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert "Turkish" in call["system"]
    block = call["messages"][0]["content"][0]
    assert block["source"]["media_type"] == "application/pdf"
    assert call["output_config"]["format"]["schema"] == summarizer.SUMMARY_SCHEMA


def test_long_text_uses_map_reduce(monkeypatch):
    monkeypatch.setattr(summarizer, "SINGLE_PASS_MAX_TOKENS", 100)
    monkeypatch.setattr(summarizer, "CHUNK_TOKENS", 100)
    client = FakeClient()
    text = "\n\n".join(["paragraph " * 20] * 6)
    steps = []
    s = summarize(LoadedDocument("t.txt", text=text), client=client, progress=steps.append)
    assert s.key_points == ["Birinci nokta", "İkinci nokta"]
    n_sections = len(client.calls) - 1
    assert n_sections > 1
    final = client.calls[-1]["messages"][0]["content"][0]["text"]
    assert f"notes {n_sections}" in final and "notes 1" in final
    assert any("section 1 of" in m for m in steps)


def test_refusal_and_truncation_raise():
    doc = LoadedDocument("t.txt", text="x")
    with pytest.raises(SummaryError, match="declined"):
        summarize(doc, client=FakeClient(stop_reason="refusal"))
    with pytest.raises(SummaryError, match="cut off"):
        summarize(doc, client=FakeClient(stop_reason="max_tokens"))


def test_chunk_text_respects_limit_and_keeps_content():
    text = "\n\n".join(["a" * 30, "b" * 30, "c" * 250, "d" * 10])
    chunks = chunk_text(text, 100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")


def test_schema_matches_model():
    assert set(summarizer.SUMMARY_SCHEMA["required"]) == set(summarizer.SUMMARY_SCHEMA["properties"])


def test_markdown_headings_follow_language():
    s = summarizer.DocumentSummary.model_validate(SUMMARY)
    tr = to_markdown(s, "tr")
    assert "## Belgenin amacı" in tr and "| Kira bedeli | 10.000 TL |" in tr
    assert "## Purpose of the document" in to_markdown(s, "en")
