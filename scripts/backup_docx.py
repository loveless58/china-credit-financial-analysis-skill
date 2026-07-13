#!/usr/bin/env python3
"""Create a timestamped backup for a DOCX file."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def backup_path(
    source: Path,
    directory: Path | None = None,
    reserved: Path | None = None,
) -> Path:
    target_dir = directory.resolve() if directory else source.resolve().parent
    reserved = reserved.resolve() if reserved else None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = target_dir / f"{source.stem}.backup-{stamp}{source.suffix}"
    counter = 1
    while candidate.exists() or (reserved is not None and candidate.resolve() == reserved):
        candidate = target_dir / f"{source.stem}.backup-{stamp}-{counter}{source.suffix}"
        counter += 1
    return candidate


def create_backup(source: Path, target: Path | None = None) -> Path:
    source = source.resolve()
    if source.suffix.lower() != ".docx" or not source.is_file():
        raise ValueError(f"invalid DOCX source: {source}")
    target = target.resolve() if target else backup_path(source)
    if target.exists():
        raise FileExistsError(f"backup already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--out", type=Path, help="Optional explicit backup path")
    args = parser.parse_args()

    try:
        target = create_backup(args.docx, args.out)
    except (ValueError, FileExistsError) as error:
        raise SystemExit(str(error)) from error
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
