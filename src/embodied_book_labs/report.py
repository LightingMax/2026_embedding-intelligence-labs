from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


CHAPTER_NAMES = {
    "chapter_1_scene_state": "第1章 感知与状态",
    "chapter_2_task_spec": "第2章 认知与任务语义",
    "chapter_3_plan_spec": "第3章 离散任务规划",
    "chapter_4_motion_check": "第4章 运动可行性",
    "chapter_5_learned_policy": "第5章 学习与评价",
    "chapter_6_runtime": "第6章 智能体运行时",
}


def _json(value: Any) -> str:
    return html.escape(json.dumps(value, ensure_ascii=False, indent=2))


def _summary(bundle: dict[str, Any]) -> list[tuple[str, str, str]]:
    if "experiment_matrix" in bundle:
        matrix = bundle["experiment_matrix"]
        faults = matrix.get("chapter_6_agent_faults", {})
        recovered = sum(row.get("final_status") == "succeeded" for name, row in faults.items() if name != "none")
        return [
            ("实验章节", "6", "ok"),
            ("故障条件", str(len(faults)), "ok"),
            ("自动恢复", str(recovered), "ok"),
            ("数据性质", "可重复", "ok"),
        ]
    scene = bundle.get("chapter_1_scene_state", {})
    task = bundle.get("chapter_2_task_spec", {})
    plan = bundle.get("chapter_3_plan_spec", {})
    motion = bundle.get("chapter_4_motion_check", {})
    runtime = bundle.get("chapter_6_runtime", {}).get("runtime_state", {})
    return [
        ("场景对象", str(len(scene.get("objects", []))), "ok"),
        ("目标绑定", str(task.get("target_object_id") or task.get("status", "unknown")), "ok" if task.get("status") == "resolved" else "warn"),
        ("计划步骤", str(len(plan.get("steps", []))), "ok" if plan.get("status") == "valid" else "warn"),
        ("运动检查", "可行" if motion.get("feasible") else str(motion.get("reason", "unknown")), "ok" if motion.get("feasible") else "warn"),
        ("最终状态", str(runtime.get("task_status", "unknown")), "ok" if runtime.get("task_status") == "succeeded" else "warn"),
        ("恢复次数", str(runtime.get("recovery_count", 0)), "ok"),
    ]


def _write_timeline(bundle: dict[str, Any], output_dir: Path) -> None:
    events = bundle.get("chapter_6_runtime", {}).get("events", [])
    if not events:
        return
    with (output_dir / "timeline.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["t", "event_type", "status", "detail_json"])
        for event in events:
            writer.writerow([event["t"], event["event_type"], event["status"], json.dumps(event.get("detail", {}), ensure_ascii=False)])


def _timeline_html(bundle: dict[str, Any]) -> str:
    events = bundle.get("chapter_6_runtime", {}).get("events", [])
    if not events:
        return ""
    rows = []
    for event in events:
        rows.append(
            "<tr>"
            f"<td>{event['t']:.3f}</td>"
            f"<td>{html.escape(event['event_type'])}</td>"
            f"<td><span class=\"status {html.escape(event['status'])}\">{html.escape(event['status'])}</span></td>"
            f"<td><code>{html.escape(json.dumps(event.get('detail', {}), ensure_ascii=False))}</code></td>"
            "</tr>"
        )
    return (
        '<section id="timeline" class="view"><div class="section-head"><h2>运行时间线</h2>'
        '<a href="timeline.csv">下载 CSV</a></div><div class="table-wrap"><table><thead><tr>'
        '<th>t / s</th><th>事件</th><th>状态</th><th>证据与参数</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div></section>"
    )


def write_report(bundle: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "result.json"
    result_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_timeline(bundle, output_dir)

    metadata = bundle.get("run_metadata", {})
    summary_cards = "".join(
        f'<article class="metric {tone}"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></article>'
        for label, value, tone in _summary(bundle)
    )
    sections = []
    for key, value in bundle.items():
        if key == "run_metadata":
            continue
        title = CHAPTER_NAMES.get(key, "六章实验矩阵" if key == "experiment_matrix" else key)
        sections.append(
            f'<section class="result"><div class="section-head"><h2>{html.escape(title)}</h2>'
            f'<button type="button" class="copy" data-copy="{html.escape(key)}">复制 JSON</button></div>'
            f'<pre id="{html.escape(key)}">{_json(value)}</pre></section>'
        )

    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>具身智能教材实验证据</title>
<style>
:root{{--ink:#17202a;--muted:#617080;--line:#dce3e8;--paper:#fff;--wash:#f4f6f7;--blue:#146a8f;--green:#1f7a4d;--amber:#9a5b00}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--wash);color:var(--ink);font-family:system-ui,-apple-system,"PingFang SC",sans-serif;letter-spacing:0}}
header{{background:#182d3a;color:white;padding:28px max(24px,calc((100vw - 1180px)/2)) 24px;border-bottom:4px solid #38a6a5}}
header h1{{font-size:28px;margin:0 0 8px}} header p{{margin:0;color:#c9d8df}} nav{{display:flex;gap:8px;margin-top:20px;flex-wrap:wrap}}
nav a{{color:white;text-decoration:none;border:1px solid #66818f;padding:7px 10px;border-radius:4px;font-size:14px}}
main{{max-width:1180px;margin:0 auto;padding:24px}} .metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:22px}}
.metric{{background:var(--paper);border:1px solid var(--line);border-top:3px solid var(--blue);border-radius:6px;padding:12px;min-height:78px}}
.metric span{{display:block;color:var(--muted);font-size:13px}} .metric strong{{display:block;font-size:20px;margin-top:10px;overflow-wrap:anywhere}}
.metric.warn{{border-top-color:var(--amber)}} .result,.view{{background:var(--paper);border:1px solid var(--line);border-radius:6px;margin:0 0 16px}}
.section-head{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-bottom:1px solid var(--line)}} h2{{font-size:17px;margin:0}}
button,.section-head a{{border:1px solid #b4c1c8;background:white;color:#164e68;border-radius:4px;padding:6px 9px;text-decoration:none;cursor:pointer}}
pre{{margin:0;padding:14px;max-height:520px;overflow:auto;font:12px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word}}
.table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}} th{{background:#edf4f6}}
td code{{white-space:pre-wrap;word-break:break-word}} .status{{font-weight:650;color:var(--blue)}} .status.succeeded,.status.passed,.status.recovered{{color:var(--green)}}
.status.failed,.status.blocked,.status.unknown,.status.paused,.status.replan_required{{color:var(--amber)}} footer{{color:var(--muted);font-size:12px;padding:4px 0 24px}}
@media(max-width:620px){{header h1{{font-size:23px}}main{{padding:14px}}.section-head{{align-items:flex-start}}}}
</style></head><body>
<header><h1>递送蓝色杯子：实验证据</h1><p>场景 {html.escape(str(metadata.get('scenario', metadata.get('kind', 'nominal'))))} · 故障 {html.escape(str(metadata.get('fault', 'none')))} · 接口版本 {html.escape(str(metadata.get('schema_version', 1)))}</p>
<nav><a href="#results">逐章结果</a><a href="#timeline">运行时间线</a><a href="result.json">完整 JSON</a></nav></header>
<main><div class="metrics">{summary_cards}</div><div id="results">{''.join(sections)}</div>{_timeline_html(bundle)}
<footer>报告由配套实验项目生成；结论只覆盖报告中声明的场景、模型与扰动条件。</footer></main>
<script>document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',async()=>{{const e=document.getElementById(b.dataset.copy);await navigator.clipboard.writeText(e.textContent);const old=b.textContent;b.textContent='已复制';setTimeout(()=>b.textContent=old,1200)}}));</script>
</body></html>"""
    path = output_dir / "index.html"
    path.write_text(document, encoding="utf-8")
    return path
