"""Streamlit web app: streamlit run app.py"""

from __future__ import annotations

from pathlib import Path

import anthropic
import streamlit as st

from docsum import ExtractionError, SummaryError, load_document, summarize, to_markdown
from docsum import settings
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
        "no_key": "Enter your Anthropic API key in the sidebar to start.",
        "key_section": "Anthropic API key",
        "key_input": "API key",
        "key_help": "Get one at console.anthropic.com. It is saved only on this computer.",
        "key_save": "Save key",
        "key_saved": "Key saved on this computer.",
        "key_forget": "Forget saved key",
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
        "no_key": "Başlamak için kenar çubuğuna Anthropic API anahtarınızı girin.",
        "key_section": "Anthropic API anahtarı",
        "key_input": "API anahtarı",
        "key_help": "console.anthropic.com adresinden alabilirsiniz. Yalnızca bu bilgisayara kaydedilir.",
        "key_save": "Anahtarı kaydet",
        "key_saved": "Anahtar bu bilgisayara kaydedildi.",
        "key_forget": "Kayıtlı anahtarı sil",
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

api_key = settings.load_api_key()
with st.sidebar.expander(t["key_section"], expanded=not api_key):
    entered = st.text_input(t["key_input"], type="password", help=t["key_help"])
    if st.button(t["key_save"]) and entered.strip():
        settings.save_api_key(entered)
        api_key = entered.strip()
        st.success(t["key_saved"])
    if api_key and st.button(t["key_forget"]):
        settings.forget_api_key()
        api_key = settings.load_api_key()

if not api_key:
    st.warning(t["no_key"])

uploaded = st.file_uploader(t["upload"], type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS])

if uploaded and st.button(t["go"], type="primary", disabled=not api_key):
    try:
        doc = load_document(uploaded.name, uploaded.getvalue())
        if doc.page_count:
            st.caption(f"{uploaded.name} · {doc.page_count} {t['pages']}")
        with st.status("…", expanded=False) as status:
            summary = summarize(
                doc, language=lang, detail=detail,
                client=anthropic.Anthropic(api_key=api_key),
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
