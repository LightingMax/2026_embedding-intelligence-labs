from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from embodied_book_labs.providers import ProviderError, XunfeiSpeechProvider, qwen_review  # noqa: E402


class ProviderTest(unittest.TestCase):
    def test_qwen_requires_explicit_runtime_key(self) -> None:
        previous = os.environ.pop("DASHSCOPE_API_KEY", None)
        try:
            with self.assertRaises(ProviderError):
                qwen_review({}, {})
        finally:
            if previous is not None:
                os.environ["DASHSCOPE_API_KEY"] = previous

    def test_xunfei_signature_keeps_credentials_out_of_query(self) -> None:
        names = ("XUNFEI_APP_ID", "XUNFEI_API_KEY", "XUNFEI_API_SECRET")
        previous = {name: os.environ.get(name) for name in names}
        os.environ.update({"XUNFEI_APP_ID": "test-app", "XUNFEI_API_KEY": "test-key", "XUNFEI_API_SECRET": "test-secret"})
        try:
            provider = XunfeiSpeechProvider()
            url = provider._signed_url("wss://tts-api.xfyun.cn/v2/tts", "Mon, 01 Jan 2024 00:00:00 GMT")
            self.assertIn("authorization=", url)
            self.assertNotIn("test-secret", url)
            self.assertNotIn("test-key", url)
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
