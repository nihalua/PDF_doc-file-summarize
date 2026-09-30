# PDF_doc-file-summarize

Summarize long **PDF, Word (DOCX / DOC) and text** files in **English or Turkish** —
**completely offline**. Your files are processed on your own computer and never uploaded
anywhere. No AI service is used.

For every document you get:

- **Purpose** – the sentence(s) where the document states what it is for
  ("The purpose of this policy…", "Bu sözleşmenin amacı…")
- **Overview** – the few sentences that best represent the whole document
- **Key points** – the most representative sentences, without repeats, in document order
- **Obligations & requirements** – sentences with *shall / must / is required to /
  zorundadır / yükümlüdür / -malıdır…*
- **Important details** – dates, amounts, percentages, time limits, article/section
  references and e-mail addresses, each with the sentence it came from
- **Main topics** and the document's **structure** (headings)
- Page numbers for PDFs, so you can jump to the source

The app's labels can be shown in English or Turkish. The quoted sentences always stay in the
document's own language.

## How it works (and its limits)

This is **extractive** summarization: the summary is made of the document's own sentences,
chosen by classic text statistics (TF-IDF centroid scoring with a diversity step), plus
English/Turkish cue phrases for purpose and obligations and patterns for dates, amounts and
so on. That means:

- ✅ Nothing leaves your computer; it works without internet; results are instant, even for
  hundreds of pages; every sentence shown is really in the document.
- ⚠️ It does not write new text. It can't rephrase, explain in its own words or translate.
  If a document never states its purpose, the app shows its best guess and says so.
- ⚠️ Scanned PDFs (images without a text layer) have no text to read. Run them through OCR
  first (e.g. Adobe Acrobat "Recognize text" or the free [OCRmyPDF](https://ocrmypdf.readthedocs.io/)).

## Download for Windows (no Python needed)

1. Open the repository's **[Releases](../../releases)** page and download `DocumentSummarizer.exe`
   from the latest release.
2. Double-click it. A console window opens (keep it open; closing it stops the app) and the app
   opens in your browser at `http://localhost:…`. The browser is only the app's window: the page is
   served by the program on your own computer.

Notes:
- Windows SmartScreen may warn that the app is from an unknown publisher, because the exe isn't
  code-signed. Click **More info → Run anyway**.
- The first start takes a few seconds while the program unpacks.
- Legacy `.doc` files need [LibreOffice](https://www.libreoffice.org/) installed (it converts
  them locally); PDF, DOCX and TXT work as is.

### Publishing a new version

The `Build Windows app` GitHub Actions workflow builds and tests the exe on every pull request
(download it from the run's **Artifacts**). To publish a release, push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

To build it yourself on Windows: `pip install -r requirements-dev.txt` then `python build_exe.py`;
the exe appears in `dist\`.

## Run from source

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py             # web app on http://localhost:8501
```

Or from the command line:

```bash
python -m docsum report.pdf                         # English labels, to stdout
python -m docsum sozlesme.docx --ui tr              # Turkish labels
python -m docsum thesis.pdf --detail detailed -o summary.md
```

## Project layout

```
app.py                Streamlit UI (English / Turkish)
launcher.py           Entry point of the Windows exe (starts the app, opens the browser)
build_exe.py          PyInstaller build script
docsum/extract.py     File loading: PDF, DOCX, DOC, TXT
docsum/textproc.py    Language detection, sentence splitting, stemming (EN/TR)
docsum/summarizer.py  Sentence scoring and selection, purpose, obligations
docsum/details.py     Patterns for dates, amounts, percentages, time limits, references
docsum/stopwords.py   English and Turkish stopword lists
docsum/render.py      Markdown output with labels in the chosen language
docsum/__main__.py    Command line interface
tests/                pytest suite, including a test that fails on any network access
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
