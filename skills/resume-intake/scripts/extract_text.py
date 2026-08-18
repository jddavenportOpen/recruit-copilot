#!/usr/bin/env python3
"""Pull readable text out of the resumes you already have, so the model can merge
them into one experience bank.

Nobody is going to hand-write a 100-bullet JSON file. But almost everyone has four
or five old resumes sitting in a folder: the long one, the one tuned for the job
you did not get, the version from two roles ago that still has the good numbers on
it. That pile is the real input, and this reads it.

Handles .pdf, .docx, .txt, .md, .json. Standard library only.

Usage:
    python3 extract_text.py ~/Documents/resumes/          # a folder
    python3 extract_text.py old.pdf new.docx --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "resume-builder", "scripts"))
import pdftext  # noqa: E402

SUPPORTED = {".pdf", ".docx", ".txt", ".md", ".markdown", ".json"}
MAX_BYTES = 12 * 1024 * 1024


def from_pdf(path: str) -> str:
    """Delegates to the shared PDF reader, which knows the filter chains real
    resumes arrive with (ASCII85 then Flate is what reportlab emits) and prefers
    PyMuPDF when it is installed."""
    text, _engine = pdftext.extract(path)
    return text


def from_docx(path: str) -> str:
    """Paragraph text out of the OOXML body. A .docx is a zip of XML."""
    with zipfile.ZipFile(path) as z:
        names = [n for n in ("word/document.xml",) if n in z.namelist()]
        if not names:
            return ""
        xml = z.read(names[0]).decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&apos;", "'"))
    return re.sub(r"\n{3,}", "\n\n", text)


def from_plain(path: str) -> str:
    return open(path, "r", encoding="utf-8", errors="replace").read()


def extract(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    rec = {"path": path, "ext": ext, "chars": 0, "text": "", "error": None}
    try:
        if os.path.getsize(path) > MAX_BYTES:
            rec["error"] = "file is larger than 12MB, skipped"
            return rec
        if ext == ".pdf":
            rec["text"] = from_pdf(path)
        elif ext == ".docx":
            rec["text"] = from_docx(path)
        elif ext in (".txt", ".md", ".markdown", ".json"):
            rec["text"] = from_plain(path)
        else:
            rec["error"] = f"unsupported type {ext}"
            return rec
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        return rec

    rec["text"] = re.sub(r"[ \t]+", " ", rec["text"]).strip()
    rec["chars"] = len(rec["text"])
    if rec["chars"] < 200:
        rec["error"] = (f"only {rec['chars']} characters came out; if this is a scanned "
                        "image, export a text PDF or paste the text into a .txt")
    return rec


def collect(targets: list[str]) -> list[str]:
    files = []
    for t in targets:
        t = os.path.expanduser(t)
        if os.path.isdir(t):
            for root, _dirs, names in os.walk(t):
                for n in sorted(names):
                    if os.path.splitext(n)[1].lower() in SUPPORTED and not n.startswith("."):
                        files.append(os.path.join(root, n))
        elif os.path.exists(t):
            files.append(t)
        else:
            print(f"not found: {t}", file=sys.stderr)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("targets", nargs="+", help="files and/or folders")
    ap.add_argument("--json", action="store_true", help="full text as JSON, for the model")
    ap.add_argument("--max-chars", type=int, default=60000, help="per-file cap")
    a = ap.parse_args()

    files = collect(a.targets)
    if not files:
        print("no readable resumes found", file=sys.stderr)
        sys.exit(1)

    recs = [extract(f) for f in files]
    for r in recs:
        r["text"] = r["text"][:a.max_chars]

    if a.json:
        print(json.dumps({"documents": recs}, indent=1))
        return

    ok = [r for r in recs if not r["error"]]
    print(f"read {len(ok)} of {len(recs)} document(s)\n")
    for r in recs:
        mark = "  ok " if not r["error"] else "SKIP "
        print(f"{mark}{os.path.basename(r['path'])} ({r['chars']} chars)"
              + (f"\n       {r['error']}" if r["error"] else ""))
    if ok:
        print(f"\nRe-run with --json to hand the full text to the model, "
              f"or run /recruit:intake and let it drive.")


if __name__ == "__main__":
    main()
