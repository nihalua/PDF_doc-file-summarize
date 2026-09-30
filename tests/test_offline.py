import socket
from pathlib import Path


import docsum
from docsum import load_document, summarize, to_markdown

FIXTURES = Path(__file__).parent / "fixtures"


def test_summarizing_never_touches_the_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    for name in ("remote_work_policy_en.txt", "kira_sozlesmesi_tr.txt"):
        doc = load_document(name, (FIXTURES / name).read_bytes())
        assert to_markdown(summarize(doc), "tr")


def test_no_ai_or_http_client_dependencies():
    requirements = (Path(__file__).parent.parent / "requirements.txt").read_text()
    for banned in ("anthropic", "openai", "requests", "httpx"):
        assert banned not in requirements
    source = "".join(p.read_text(encoding="utf-8") for p in Path(docsum.__file__).parent.glob("*.py"))
    for banned in ("import anthropic", "import requests", "import httpx", "urllib.request"):
        assert banned not in source
