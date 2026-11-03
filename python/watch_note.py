#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""watch_note.py -- append one semantic/feeling note to notes.jsonl.

This is a plain append-only log file, NOT a memory system. No database,
no network, no upload. Choose --dir to tell it where the log lives.

Options:
  --sem "what happened"
  --feel "how it felt", optional
  --source "screen" | "file" | a path, optional
  --dir <path> (default: system temp / dsh-njs-watch)
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem", required=True)
    ap.add_argument("--feel", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--dir", default=None)
    a = ap.parse_args()
    out_dir = a.dir or os.path.join(tempfile.gettempdir(), "dsh-njs-watch")
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, "notes.jsonl")
    rec = {"t": datetime.now().astimezone().isoformat(timespec="seconds"),
           "sem": a.sem, "feel": a.feel, "source": a.source}
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "file": p}, ensure_ascii=False))


if __name__ == "__main__":
    main()
