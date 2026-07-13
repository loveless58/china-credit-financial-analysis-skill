#!/usr/bin/env python3
"""Write a standardized Markdown change log for DOCX financial-section edits."""

from __future__ import annotations

import argparse
from pathlib import Path


def _markdown_list(items: list[str], empty: str = "未提供") -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {empty}"


def write_change_log(
    out: Path,
    original: Path,
    workspace_copy: Path,
    backup: Path,
    output: Path,
    mode: str,
    location: str,
    sources: list[str],
    pending: list[str],
    table_preservation: str,
    validation_failed: list[str],
) -> Path:
    body = f"""# 修改说明

## 文件路径

- 用户提供原文件：`{original}`
- 工作区副本：`{workspace_copy}`
- 编辑前备份：`{backup}`
- 更新版文件：`{output}`

## 写回模式

- 模式：{mode}
- 位置：{location}

## 使用的数据来源

{_markdown_list(sources)}

## 待人工核验事项

{_markdown_list(pending)}

## 表格格式保护

- {table_preservation}

## 结构校验失败项

{_markdown_list(validation_failed, "无")}
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    return out


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
    parser.add_argument("--table-preservation", default="未提供")
    parser.add_argument("--validation-failed", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    output = write_change_log(
        out=args.out,
        original=Path(args.original),
        workspace_copy=Path(args.workspace_copy),
        backup=Path(args.backup),
        output=Path(args.output),
        mode=args.mode,
        location=args.location,
        sources=[args.sources] if args.sources else [],
        pending=[args.pending] if args.pending else [],
        table_preservation=args.table_preservation,
        validation_failed=[args.validation_failed]
        if args.validation_failed
        else [],
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
