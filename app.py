"""Streamlit web app: streamlit run app.py

Runs entirely on this computer. The uploaded file goes from the browser to
the local Streamlit server (127.0.0.1) and is processed in memory; nothing
is sent to the internet.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from docsum import ExtractionError, SummaryError, load_document, summarize, to_markdown
from docsum.extract import SUPPORTED_EXTENSIONS

UI = {
    "en": {
        "title": "📄 Document Summarizer",
        "intro": "Upload a long PDF, Word (DOCX/DOC) or text file in English or Turkish to see its "
                 "purpose, key points, obligations and important details.",
        "private": "🔒 Works offline: your file is processed on this computer and never uploaded "
                   "anywhere. No AI is used; the summary quotes the document's own sentences.",
        "upload": "Choose a file",
        "detail": "Detail level",
        "details": {"brief": "Brief", "standard": "Standard", "detailed": "Detailed"},
        "go": "Summarize",
        "working": "Reading the document…",
        "download": "Download summary (.md)",
        "pages": "pages",
    },
    "tr": {
        "title": "📄 Belge Özetleyici",
        "intro": "Türkçe veya İngilizce uzun bir PDF, Word (DOCX/DOC) ya da metin dosyası yükleyin; "
                 "belgenin amacını, önemli noktalarını, yükümlülüklerini ve kritik ayrıntılarını görün.",
        "private": "🔒 Çevrimdışı çalışır: dosyanız bu bilgisayarda işlenir ve hiçbir yere "
                   "yüklenmez. Yapay zekâ kullanılmaz; özet, belgenin kendi cümlelerinden oluşur.",
        "upload": "Dosya seçin",
        "detail": "Ayrıntı düzeyi",
        "details": {"brief": "Kısa", "standard": "Standart", "detailed": "Ayrıntılı"},
        "go": "Özetle",
        "working": "Belge okunuyor…",
        "download": "Özeti indir (.md)",
        "pages": "sayfa",
    },
}

st.set_page_config(page_title="Document Summarizer / Belge Özetleyici", page_icon="📄")

ui = st.sidebar.radio(
    "Language / Dil",
    options=["en", "tr"],
    format_func=lambda c: {"en": "English", "tr": "Türkçe"}[c],
    horizontal=True,
)
t = UI[ui]
detail = st.sidebar.select_slider(
    t["detail"], options=["brief", "standard", "detailed"], value="standard",
    format_func=lambda d: t["details"][d],
)

st.title(t["title"])
st.write(t["intro"])
st.info(t["private"])

uploaded = st.file_uploader(t["upload"], type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS])

if uploaded and st.button(t["go"], type="primary"):
    try:
        with st.spinner(t["working"]):
            doc = load_document(uploaded.name, uploaded.getvalue())
            summary = summarize(doc, detail=detail)
    except (ExtractionError, SummaryError) as e:
        st.error(str(e))
    else:
        st.session_state["result"] = (uploaded.name, summary)

if "result" in st.session_state:
    name, summary = st.session_state["result"]
    md = to_markdown(summary, ui)  # re-rendered so switching language relabels it
    st.divider()
    st.markdown(md)
    st.download_button(
        t["download"], data=md.encode("utf-8"),
        file_name=f"{Path(name).stem}-summary.md", mime="text/markdown",
    )
