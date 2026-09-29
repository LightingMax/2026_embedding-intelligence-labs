from __future__ import annotations

import argparse
import json
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from .pipeline import FAULTS, SCENARIOS, experiment_matrix, result_bundle
from .providers import ProviderError, XunfeiSpeechProvider, qwen_review
from .report import write_report


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ARTIFACTS = ROOT / "artifacts" / "latest"


def run(args: argparse.Namespace) -> int:
    bundle = result_bundle(DATA, fault=args.fault, scenario=args.scenario)
    if args.llm == "qwen":
        try:
            bundle["optional_qwen_plan_review"] = qwen_review(
                bundle["chapter_2_task_spec"], bundle["chapter_3_plan_spec"]
            )
        except ProviderError as exc:
            raise SystemExit(str(exc)) from exc
    path = write_report(bundle, ARTIFACTS)
    print(json.dumps({"status": "ok", "scenario": args.scenario, "fault": args.fault, "report": str(path)}, ensure_ascii=False))
    return 0


def chapter(args: argparse.Namespace) -> int:
    if args.number not in range(1, 7):
        raise SystemExit("章节编号必须为1到6")
    bundle = result_bundle(DATA, scenario=args.scenario)
    key = next(key for key in bundle if key.startswith(f"chapter_{args.number}_"))
    print(json.dumps(bundle[key], ensure_ascii=False, indent=2))
    return 0


def matrix(args: argparse.Namespace) -> int:
    bundle = {
        "run_metadata": {"kind": "experiment_matrix", "deterministic": True, "schema_version": 1},
        "experiment_matrix": experiment_matrix(DATA),
    }
    path = write_report(bundle, ARTIFACTS)
    print(json.dumps({"status": "ok", "report": str(path), "matrix": str(ARTIFACTS / "result.json")}, ensure_ascii=False))
    return 0


def speech(args: argparse.Namespace) -> int:
    try:
        provider = XunfeiSpeechProvider()
        if args.speech_command == "tts":
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(provider.synthesize(args.text))
            print(json.dumps({"status": "ok", "format": "mp3", "output": str(output)}, ensure_ascii=False))
        else:
            text = provider.transcribe(Path(args.input).read_bytes())
            print(json.dumps({"status": "ok", "text": text}, ensure_ascii=False))
    except ProviderError as exc:
        raise SystemExit(str(exc)) from exc
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
    run_parser.add_argument("--fault", choices=FAULTS, default="none")
    run_parser.add_argument("--scenario", choices=SCENARIOS, default="nominal")
    run_parser.add_argument("--llm", choices=["none", "qwen"], default="none")
    run_parser.set_defaults(func=run)
    chapter_parser = sub.add_parser("chapter")
    chapter_parser.add_argument("number", type=int)
    chapter_parser.add_argument("--scenario", choices=SCENARIOS, default="nominal")
    chapter_parser.set_defaults(func=chapter)
    matrix_parser = sub.add_parser("matrix")
    matrix_parser.set_defaults(func=matrix)
    speech_parser = sub.add_parser("speech")
    speech_sub = speech_parser.add_subparsers(dest="speech_command", required=True)
    tts_parser = speech_sub.add_parser("tts")
    tts_parser.add_argument("--text", required=True)
    tts_parser.add_argument("--output", default=str(ARTIFACTS / "speech.mp3"))
    tts_parser.set_defaults(func=speech)
    asr_parser = speech_sub.add_parser("asr")
    asr_parser.add_argument("--input", required=True, help="mono 16 kHz, 16-bit PCM")
    asr_parser.set_defaults(func=speech)
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
