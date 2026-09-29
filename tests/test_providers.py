from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from embodied_book_labs.providers import ProviderError, qwen_review  # noqa: E402


class ProviderTest(unittest.TestCase):
    def test_qwen_requires_explicit_runtime_key(self) -> None:
        previous = os.environ.pop("DASHSCOPE_API_KEY", None)
        try:
            with self.assertRaises(ProviderError):
                qwen_review({}, {})
        finally:
            if previous is not None:
                os.environ["DASHSCOPE_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
