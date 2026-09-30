"""Entry point for the packaged desktop app (DocumentSummarizer.exe).

Starts the Streamlit app on a free local port and opens it in the default
browser. The console window stays open while the app runs; closing it stops
the app.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser

import docsum  # noqa: F401  - makes PyInstaller bundle the package app.py imports
from streamlit.web import cli as stcli


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _open_browser_when_ready(url: str, port: int) -> None:
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    print(f"\nDocument Summarizer is running at {url}", flush=True)
    print("Keep this window open while you use it. Close it to stop the app.\n", flush=True)
    if not os.environ.get("DOCSUM_NO_BROWSER"):
        webbrowser.open(url)


def main() -> int:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    port = int(os.environ.get("DOCSUM_PORT") or _free_port())
    url = f"http://localhost:{port}"
    print("Starting Document Summarizer...", flush=True)
    threading.Thread(target=_open_browser_when_ready, args=(url, port), daemon=True).start()
    sys.argv = [
        "streamlit", "run", os.path.join(base, "app.py"),
        "--global.developmentMode=false",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    return stcli.main()


if __name__ == "__main__":
    sys.exit(main())
