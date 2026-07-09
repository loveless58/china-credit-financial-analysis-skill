#!/usr/bin/env python3
"""Write a standardized Markdown change log for DOCX financial-section edits."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True)
    parser.add_argument("--workspace-copy", required=True)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--sources", default="")
    parser.add_argument("--pending", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    body = f"""# 修改说明

## 文件路径

- 用户提供原文件：`{args.original}`
- 工作区副本：`{args.workspace_copy}`
- 编辑前备份：`{args.backup}`
- 更新版文件：`{args.output}`

## 写回模式

- 模式：{args.mode}
- 位置：{args.location}

## 使用的数据来源

{args.sources or "- 未提供"}

## 待人工核验事项

{args.pending or "- 未提供"}
"""
    args.out.write_text(body, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
