from pathlib import Path

import pytest

from docsum import SummaryError, load_document, summarize, to_markdown
from docsum.extract import LoadedDocument

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return load_document(name, (FIXTURES / name).read_bytes())


def test_english_policy():
    s = summarize(load("remote_work_policy_en.txt"), "detailed")
    assert s.language == "en"
    assert s.title == "REMOTE WORK POLICY"
    assert s.purpose_from_cues
    assert s.purpose[0].text.startswith("The purpose of this policy")
    assert any("within 14 days" in p.text for p in s.obligations)
    assert any("shall not install unapproved software" in p.text for p in s.obligations)
    values = {(f.kind, f.value) for f in s.facts}
    assert {("date", "1 March 2027"), ("amount", "£30"), ("percentage", "78%"),
            ("time_limit", "within 24 hours"), ("email", "hr@northwind.example")} <= values
    assert "remote work" in s.key_phrases
    assert [p.text for p in s.outline][1] == "1. Introduction"


def test_turkish_contract():
    s = summarize(load("kira_sozlesmesi_tr.txt"))
    assert s.language == "tr"
    assert s.purpose[0].text.startswith("Bu sözleşmenin amacı")
    assert any("zorundadır" in p.text for p in s.obligations)
    values = {(f.kind, f.value) for f in s.facts}
    assert {("amount", "25.000 TL"), ("amount", "50.000 TL"), ("date", "1 Şubat 2027"),
            ("percentage", "%25"), ("time_limit", "en geç 30 gün")} <= values
    # Section headings aren't reported as references.
    assert not any(f.kind == "reference" and f.value.upper().startswith("MADDE") for f in s.facts)


def test_sections_do_not_repeat_each_other():
    s = summarize(load("remote_work_policy_en.txt"))
    purpose = {p.text for p in s.purpose}
    overview = {p.text for p in s.overview}
    key_points = {p.text for p in s.key_points}
    obligations = {p.text for p in s.obligations}
    assert not (purpose & overview) and not (overview & key_points) and not (key_points & obligations)


def test_detail_level_changes_length():
    doc = load("remote_work_policy_en.txt")
    assert len(summarize(doc, "brief").key_points) < len(summarize(doc, "detailed").key_points)


def test_markdown_labels_follow_ui_language():
    s = summarize(load("kira_sozlesmesi_tr.txt"))
    tr, en = to_markdown(s, "tr"), to_markdown(s, "en")
    assert "## Belgenin amacı" in tr and "**Belgenin dili:** Türkçe" in tr
    assert "## Purpose of the document" in en and "**Document language:** Turkish" in en
    assert "| **25.000 TL** |" in en


def test_page_numbers_are_cited_for_pdfs():
    pages = [
        "The purpose of this report is to review the annual budget of the city council in detail.",
        "Spending on public transport rose sharply. The council must publish the final figures by 1 June 2027.",
    ]
    s = summarize(LoadedDocument("r.pdf", pages, page_count=2))
    assert s.purpose[0].page == 1
    assert s.obligations[0].page == 2
    assert "*(p. 2)*" in to_markdown(s, "en")


def test_too_little_text():
    with pytest.raises(SummaryError):
        summarize(LoadedDocument("x.txt", ["Hello."]))


def test_long_document_is_fast():
    import time
    text = (FIXTURES / "remote_work_policy_en.txt").read_text(encoding="utf-8")
    doc = LoadedDocument("big.txt", [text] * 150)  # ~90k words
    start = time.perf_counter()
    s = summarize(doc, "detailed")
    assert time.perf_counter() - start < 20
    assert len(s.key_points) == 20
