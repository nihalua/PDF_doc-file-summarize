"""Streamlit web app: streamlit run app.py"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from docsum import ExtractionError, SummaryError, load_document, summarize, to_markdown
from docsum.extract import SUPPORTED_EXTENSIONS

UI = {
    "en": {
        "title": "📄 Document Summarizer",
        "intro": "Upload a long PDF, Word (DOCX/DOC) or text file and get its purpose, "
                 "key points and important details.",
        "upload": "Choose a file",
        "language": "Summary language",
        "detail": "Detail level",
        "details": {"brief": "Brief", "standard": "Standard", "detailed": "Detailed"},
        "go": "Summarize",
        "download": "Download summary (.md)",
        "no_key": "Set the ANTHROPIC_API_KEY environment variable before starting the app.",
        "pages": "pages",
    },
    "tr": {
        "title": "📄 Belge Özetleyici",
        "intro": "Uzun bir PDF, Word (DOCX/DOC) veya metin dosyası yükleyin; belgenin amacını, "
                 "önemli noktalarını ve kritik ayrıntılarını alın.",
        "upload": "Dosya seçin",
        "language": "Özet dili",
        "detail": "Ayrıntı düzeyi",
        "details": {"brief": "Kısa", "standard": "Standart", "detailed": "Ayrıntılı"},
        "go": "Özetle",
        "download": "Özeti indir (.md)",
        "no_key": "Uygulamayı başlatmadan önce ANTHROPIC_API_KEY ortam değişkenini ayarlayın.",
        "pages": "sayfa",
    },
}

st.set_page_config(page_title="Document Summarizer / Belge Özetleyici", page_icon="📄")

lang = st.sidebar.radio(
    "Summary language / Özet dili",
    options=["en", "tr"],
    format_func=lambda c: {"en": "English", "tr": "Türkçe"}[c],
    horizontal=True,
)
t = UI[lang]
detail = st.sidebar.select_slider(
    t["detail"], options=["brief", "standard", "detailed"], value="standard",
    format_func=lambda d: t["details"][d],
)

st.title(t["title"])
st.write(t["intro"])

if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
    st.warning(t["no_key"])

uploaded = st.file_uploader(t["upload"], type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS])

if uploaded and st.button(t["go"], type="primary"):
    try:
        doc = load_document(uploaded.name, uploaded.getvalue())
        if doc.page_count:
            st.caption(f"{uploaded.name} · {doc.page_count} {t['pages']}")
        with st.status("…", expanded=False) as status:
            summary = summarize(
                doc, language=lang, detail=detail,
                progress=lambda msg: status.update(label=msg),
            )
            status.update(label="✅", state="complete")
    except (ExtractionError, SummaryError) as e:
        st.error(str(e))
    else:
        md = to_markdown(summary, lang)
        st.session_state["result"] = (uploaded.name, md)

if "result" in st.session_state:
    name, md = st.session_state["result"]
    st.divider()
    st.markdown(md)
    st.download_button(
        t["download"], data=md.encode("utf-8"),
        file_name=f"{Path(name).stem}-summary-{lang}.md", mime="text/markdown",
    )
