from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_report(bundle: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    cards = []
    for title, value in bundle.items():
        pretty = html.escape(json.dumps(value, ensure_ascii=False, indent=2))
        cards.append(f"<section><h2>{html.escape(title)}</h2><pre>{pretty}</pre></section>")
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>具身智能教材实验报告</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f3f6fa;color:#172033}}
header{{background:#123a63;color:white;padding:2rem max(4vw,1rem)}}
main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1rem;padding:1rem max(4vw,1rem)}}
section{{background:white;border-radius:12px;padding:1rem;box-shadow:0 4px 20px #10203014}}
h1{{margin:0}} h2{{font-size:1.05rem;color:#0d5a8c}} pre{{white-space:pre-wrap;word-break:break-word;font-size:.82rem}}
</style></head><body><header><h1>递送蓝色杯子：六章实验结果</h1><p>同一任务从观测、理解、规划、运动、学习到运行时执行。</p></header><main>{''.join(cards)}</main></body></html>"""
    path = output_dir / "index.html"
    path.write_text(document, encoding="utf-8")
    return path
