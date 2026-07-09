#!/usr/bin/env python3
"""Extract financial-looking lines from annual-report or announcement text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

KEYWORDS = ("营业收入", "营业成本", "净利润", "归属于", "扣非", "资产总计", "负债合计", "货币资金", "应收账款", "存货", "经营活动")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("text_file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    text = args.text_file.read_text(encoding="utf-8-sig", errors="ignore")
    lines = [line.strip() for line in text.splitlines() if any(k in line for k in KEYWORDS)]
    args.out.write_text(json.dumps({"source": str(args.text_file), "candidate_lines": lines}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"candidate_lines": len(lines), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
