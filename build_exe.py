"""Build the desktop app with PyInstaller: python build_exe.py

Produces dist/DocumentSummarizer.exe on Windows (dist/DocumentSummarizer
elsewhere). Used by .github/workflows/build-windows.yml.
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    "launcher.py",
    "--name=DocumentSummarizer",
    "--onefile",
    "--noconfirm",
    "--clean",
    # app.py is run by Streamlit as a script, so ship it as a data file.
    "--add-data=app.py:.",
    # Streamlit needs its static web files and its package metadata.
    "--collect-all=streamlit",
    "--copy-metadata=streamlit",
    "--collect-submodules=docsum",
    "--collect-data=docx",
])
