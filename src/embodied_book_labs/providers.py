from __future__ import annotations

import json
import os
import base64
import hashlib
import hmac
import urllib.request
import urllib.parse
from email.utils import formatdate
from typing import Any, Optional


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


class XunfeiSpeechProvider(SpeechProvider):
    """Optional iFlytek IAT/TTS adapter; credentials remain in process memory."""

    def __init__(self) -> None:
        self.app_id = os.getenv("XUNFEI_APP_ID", "")
        self.api_key = os.getenv("XUNFEI_API_KEY", "")
        self.api_secret = os.getenv("XUNFEI_API_SECRET", "")
        if not all((self.app_id, self.api_key, self.api_secret)):
            raise ProviderError("XUNFEI_APP_ID, XUNFEI_API_KEY and XUNFEI_API_SECRET are required")

    def _signed_url(self, base_url: str, now: Optional[str] = None) -> str:
        parts = urllib.parse.urlsplit(base_url)
        date = now or formatdate(usegmt=True)
        signature_origin = f"host: {parts.netloc}\ndate: {date}\nGET {parts.path} HTTP/1.1"
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode(), signature_origin.encode(), hashlib.sha256).digest()
        ).decode()
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode()).decode()
        query = urllib.parse.urlencode({"authorization": authorization, "date": date, "host": parts.netloc})
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))

    @staticmethod
    def _connect(url: str):
        try:
            import websocket
        except ImportError as exc:
            raise ProviderError("Install the speech extra: pip install '.[speech]'") from exc
        try:
            return websocket.create_connection(url, timeout=30)
        except Exception as exc:
            raise ProviderError(f"iFlytek connection failed: {exc}") from exc

    def transcribe(self, audio: bytes) -> str:
        """Transcribe mono 16 kHz, 16-bit PCM audio."""
        socket = self._connect(self._signed_url("wss://iat-api.xfyun.cn/v2/iat"))
        payload = {
            "common": {"app_id": self.app_id},
            "business": {"language": "zh_cn", "domain": "iat", "accent": "mandarin", "dwa": "wpgs"},
            "data": {"status": 2, "format": "audio/L16;rate=16000", "encoding": "raw", "audio": base64.b64encode(audio).decode()},
        }
        fragments: dict[int, str] = {}
        try:
            socket.send(json.dumps(payload))
            while True:
                message = json.loads(socket.recv())
                if message.get("code") != 0:
                    raise ProviderError(f"iFlytek ASR failed with code {message.get('code')}")
                data = message.get("data", {})
                result = data.get("result", {})
                text = "".join(candidate.get("w", "") for item in result.get("ws", []) for candidate in item.get("cw", [])[:1])
                if text:
                    fragments[int(result.get("sn", len(fragments)))] = text
                if data.get("status") == 2:
                    break
        finally:
            socket.close()
        return "".join(fragments[index] for index in sorted(fragments))

    def synthesize(self, text: str) -> bytes:
        """Synthesize Mandarin speech and return MP3 bytes."""
        socket = self._connect(self._signed_url("wss://tts-api.xfyun.cn/v2/tts"))
        payload = {
            "common": {"app_id": self.app_id},
            "business": {"aue": "lame", "auf": "audio/L16;rate=16000", "vcn": "xiaoyan", "tte": "utf8"},
            "data": {"status": 2, "text": base64.b64encode(text.encode()).decode()},
        }
        chunks: list[bytes] = []
        try:
            socket.send(json.dumps(payload))
            while True:
                message = json.loads(socket.recv())
                if message.get("code") != 0:
                    raise ProviderError(f"iFlytek TTS failed with code {message.get('code')}")
                data = message.get("data", {})
                if data.get("audio"):
                    chunks.append(base64.b64decode(data["audio"]))
                if data.get("status") == 2:
                    break
        finally:
            socket.close()
        return b"".join(chunks)
