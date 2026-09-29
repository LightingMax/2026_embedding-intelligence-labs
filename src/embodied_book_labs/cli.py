from __future__ import annotations

import argparse
import json
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from .pipeline import result_bundle
from .report import write_report


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ARTIFACTS = ROOT / "artifacts" / "latest"


def run(args: argparse.Namespace) -> int:
    if args.llm != "none" and args.llm == "qwen" and not os.getenv("DASHSCOPE_API_KEY"):
        raise SystemExit("选择Qwen时需要在进程环境设置DASHSCOPE_API_KEY")
    bundle = result_bundle(DATA, fault=args.fault)
    path = write_report(bundle, ARTIFACTS)
    print(json.dumps({"status": "ok", "fault": args.fault, "report": str(path)}, ensure_ascii=False))
    return 0


def chapter(args: argparse.Namespace) -> int:
    if args.number not in range(1, 7):
        raise SystemExit("章节编号必须为1到6")
    bundle = result_bundle(DATA)
    key = next(key for key in bundle if key.startswith(f"chapter_{args.number}_"))
    print(json.dumps(bundle[key], ensure_ascii=False, indent=2))
    return 0


def serve(args: argparse.Namespace) -> int:
    if not (ARTIFACTS / "index.html").exists():
        write_report(result_bundle(DATA), ARTIFACTS)
    os.chdir(ARTIFACTS)
    server = ThreadingHTTPServer((args.host, args.port), SimpleHTTPRequestHandler)
    print(f"http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--fault", choices=["none", "target_moved", "human_entered", "user_cancel"], default="none")
    run_parser.add_argument("--llm", choices=["none", "qwen"], default="none")
    run_parser.set_defaults(func=run)
    chapter_parser = sub.add_parser("chapter")
    chapter_parser.add_argument("number", type=int)
    chapter_parser.set_defaults(func=chapter)
    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.set_defaults(func=serve)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
