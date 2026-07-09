#!/usr/bin/env python3
"""Fetch official SSE announcement PDFs for a listed company."""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path


BASE = "https://www.sse.com.cn"
QUERY_URL = "https://query.sse.com.cn/security/stock/queryCompanyBulletin.do"


def request_json(stock_code: str, keyword: str) -> dict:
    params = {
        "isPagination": "true",
        "productId": stock_code,
        "keyWord": keyword,
        "securityType": "0101,120100,020100,020200,120200",
        "pageHelp.pageSize": "25",
        "pageHelp.pageNo": "1",
        "pageHelp.beginPage": "1",
        "pageHelp.cacheSize": "1",
        "pageHelp.endPage": "1",
        "_": str(int(time.time() * 1000)),
    }
    url = QUERY_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Referer": BASE + "/", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def pick_report(rows: list[dict], keyword: str) -> dict:
    non_summary = [row for row in rows if "摘要" not in (row.get("TITLE") or "")]
    exact = [row for row in non_summary if keyword in (row.get("TITLE") or "")]
    if exact:
        return exact[0]
    if non_summary:
        return non_summary[0]
    raise RuntimeError(f"未找到非摘要公告: {keyword}")


def solve_acw_cookie(html: str, url: str) -> str:
    script = f"""
const html = {html!r};
global.document = {{cookie: "", location: {{reload: () => {{}}}}}};
global.location = new URL({url!r});
global.window = global;
eval(html.replace(/^<html><script>/, "").replace(/<\\/script><\\/html>\\s*$/, ""));
console.log(document.cookie.split(";")[0]);
"""
    completed = subprocess.run(["node", "-e", script], check=True, text=True, capture_output=True, timeout=15)
    cookie = completed.stdout.strip()
    if not cookie.startswith("acw_sc__v2="):
        raise RuntimeError(f"无法计算上交所下载 Cookie: {cookie}")
    return cookie


def read_url(url: str, headers: dict[str, str]) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    if data.startswith(b"\x1f\x8b"):
        data = gzip.decompress(data)
    return data


def download_pdf(url: str, path: Path) -> None:
    headers = {"Referer": BASE + "/", "User-Agent": "Mozilla/5.0"}
    data = read_url(url, headers)
    if data.lstrip().startswith(b"<html><script>") and b"acw_sc__v2" in data:
        headers["Cookie"] = solve_acw_cookie(data.decode("utf-8", errors="replace"), url)
        data = read_url(url, headers)
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"下载结果不是PDF: {url} bytes={len(data)}")
    path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", required=True)
    parser.add_argument("--keywords", required=True, help="Comma-separated keywords")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for keyword in [item.strip() for item in args.keywords.split(",") if item.strip()]:
        data = request_json(args.stock_code, keyword)
        rows = data.get("pageHelp", {}).get("data") or []
        report = pick_report(rows, keyword)
        pdf_url = BASE + report["URL"]
        safe_title = "".join(ch if ch not in r'\/:*?"<>|' else "_" for ch in report["TITLE"])
        out_path = args.out_dir / f"{safe_title}.pdf"
        download_pdf(pdf_url, out_path)
        manifest.append(
            {
                "keyword": keyword,
                "title": report.get("TITLE"),
                "bulletin_year": report.get("BULLETIN_YEAR"),
                "bulletin_type": report.get("BULLETIN_TYPE"),
                "url": pdf_url,
                "file": str(out_path),
                "bytes": out_path.stat().st_size,
                "source_type": "official_disclosure",
            }
        )
        print(f"downloaded: {report.get('TITLE')} -> {out_path}")
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
