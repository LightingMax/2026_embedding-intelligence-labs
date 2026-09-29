from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


class ProviderError(RuntimeError):
    pass


def qwen_review(task_spec: dict[str, Any], plan_spec: dict[str, Any]) -> dict[str, Any]:
    """Ask Qwen to review a candidate plan without granting execution authority."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ProviderError("DASHSCOPE_API_KEY is not set")
    prompt = {
        "task_spec": task_spec,
        "plan_spec": plan_spec,
        "request": (
            "Review this embodied task plan. Return JSON with keys summary, "
            "missing_preconditions, and questions. Do not invent tools or declare "
            "physical feasibility."
        ),
    }
    body = json.dumps(
        {
            "model": os.getenv("QWEN_MODEL", "qwen-plus"),
            "messages": [
                {
                    "role": "system",
                    "content": "You review robot task plans. Output valid JSON only.",
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except Exception as exc:
        raise ProviderError(f"Qwen request failed: {exc}") from exc
    content = payload["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProviderError("Qwen returned non-JSON content") from exc


class SpeechProvider:
    """Boundary for optional ASR/TTS providers used by classroom deployments."""

    def transcribe(self, audio: bytes) -> str:
        raise NotImplementedError

    def synthesize(self, text: str) -> bytes:
        raise NotImplementedError
