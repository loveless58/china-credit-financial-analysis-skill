#!/usr/bin/env python3
"""Create a timestamped backup for a DOCX file."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def backup_path(source: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = source.with_name(f"{source.stem}.backup-{stamp}{source.suffix}")
    counter = 1
    while candidate.exists():
        candidate = source.with_name(f"{source.stem}.backup-{stamp}-{counter}{source.suffix}")
        counter += 1
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--out", type=Path, help="Optional explicit backup path")
    args = parser.parse_args()

    source = args.docx.resolve()
    if source.suffix.lower() != ".docx":
        raise SystemExit("only .docx files are supported")
    if not source.exists():
        raise SystemExit(f"file not found: {source}")

    target = args.out.resolve() if args.out else backup_path(source)
    if target.exists():
        raise SystemExit(f"backup already exists: {target}")
    shutil.copy2(source, target)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
