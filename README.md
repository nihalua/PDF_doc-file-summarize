# PDF_doc-file-summarize

Summarize long **PDF, Word (DOCX / DOC) and text** files in **English or Turkish** with Claude.
For every document you get:

- **Purpose** – why the document exists and what it's trying to achieve
- **Summary** – the substance of the document
- **Key points** – the most important findings, decisions and terms, most important first
- **Important details** – dates, deadlines, amounts, parties, reference numbers
- **Action items & obligations** – what the document requires or recommends, and from whom
- **Conclusion** – the bottom line

The summary is written in the language you choose, whatever language the document is in
(e.g. an English contract summarized in Turkish, or the other way round).

## Download for Windows (no Python needed)

1. Open the repository's **[Releases](../../releases)** page and download `DocumentSummarizer.exe`
   from the latest release.
2. Double-click it. A console window opens (keep it open; closing it stops the app) and the app
   opens in your browser.
3. The first time, paste your Anthropic API key (from [console.anthropic.com](https://console.anthropic.com))
   into **Anthropic API key** in the sidebar and click **Save key**. It is stored only on your computer,
   in `%APPDATA%\DocumentSummarizer\config.json`.

Notes:
- Windows SmartScreen may warn that the app is from an unknown publisher, because the exe isn't
  code-signed. Click **More info → Run anyway**.
- The first start takes a few seconds while the program unpacks.
- Legacy `.doc` files need [LibreOffice](https://www.libreoffice.org/) installed; PDF, DOCX and TXT work as is.

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
export ANTHROPIC_API_KEY=sk-ant-...   # Windows: set ANTHROPIC_API_KEY=...
```

Legacy `.doc` files are converted with [LibreOffice](https://www.libreoffice.org/) (`soffice`),
so install it if you need `.doc` support. `.docx`, `.pdf` and `.txt` need nothing extra.

## Web app

```bash
streamlit run app.py
```

Pick the summary language (English / Türkçe) and detail level (brief / standard / detailed) in
the sidebar, upload a file, click **Summarize**. The result can be downloaded as Markdown.

## Command line

```bash
python -m docsum report.pdf                      # English summary to stdout
python -m docsum sozlesme.docx --lang tr         # Turkish summary
python -m docsum thesis.pdf --detail detailed --effort high -o summary.md
```

`--effort` controls how hard the model thinks (`low` … `max`); `medium` is the default and a good
balance of quality, speed and cost for summaries.

## How it handles long documents

| Input | What happens |
|---|---|
| PDF up to 100 pages | Sent to Claude as a PDF, so tables, charts and scanned pages are read too |
| Longer PDF with a text layer | Text is extracted per page (much cheaper than page images) |
| Longer scanned PDF | Split into 100-page PDF batches |
| DOCX / DOC | Text extracted with headings, lists and tables kept in document order |
| TXT / MD | Decoded as UTF-8, falling back to Turkish Windows encodings (cp1254 / ISO-8859-9) |

Anything that fits in one request (Claude's context is 1M tokens — several hundred pages of text)
is summarized in a single pass. Bigger documents are split into sections; each section is
condensed into notes, and the final summary is written from all the notes.

The model is `claude-opus-5-5` with structured JSON output, so every summary has the same
sections. The document is prompt-cached, so re-summarizing the same file in the other language
within a few minutes is much cheaper.

## Project layout

```
app.py               Streamlit UI (English / Turkish)
launcher.py          Entry point of the Windows exe (starts the app, opens the browser)
build_exe.py         PyInstaller build script
docsum/extract.py    File loading: PDF, DOCX, DOC, TXT
docsum/summarizer.py Claude calls, prompts, long-document map-reduce
docsum/render.py     Markdown output with headings in the chosen language
docsum/settings.py   Saves the API key in the user's profile
docsum/__main__.py   Command line interface
tests/               pytest suite (no API key needed; the Claude client is faked)
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
