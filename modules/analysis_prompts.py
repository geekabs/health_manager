"""AI 分析用システム指示の読み込み。

既定はプロジェクト直下 `prompts/analysis_system.txt`（UTF-8）。
編集はそのテキストファイルを直接変更する。

優先順位（`load_system_instruction(lang)`）:
- `lang=en`: `GEMINI_SYSTEM_PROMPT_FILE_EN` → `prompts/analysis_system_en.txt` → 英語フォールバック
- `lang=ja`: `GEMINI_SYSTEM_PROMPT_FILE` → `prompts/analysis_system.txt` → 日本語フォールバック
"""

from __future__ import annotations

import os
from pathlib import Path

# プロジェクトルート（modules/ の親）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BUNDLED_PROMPT = _PROJECT_ROOT / "prompts" / "analysis_system.txt"
_BUNDLED_PROMPT_EN = _PROJECT_ROOT / "prompts" / "analysis_system_en.txt"

FALLBACK_SYSTEM_INSTRUCTION = (
    "健康データの集計のみを根拠に、簡潔に生活習慣の観点から整理せよ。"
    "診断・治療指示は行わない。Markdown、箇条書き優先。"
)
FALLBACK_SYSTEM_INSTRUCTION_EN = (
    "Summarize lifestyle-relevant points from the aggregates only. "
    "No diagnosis or treatment instructions. Markdown, bullets preferred."
)


def _read_utf8(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
        return text or None
    except OSError:
        return None


def load_system_instruction(lang: str = "ja") -> str:
    """分析のたびに呼ぶ。テキストファイルを UTF-8 で読み込む。lang は ja | en。"""
    is_en = lang.lower().startswith("en")
    env_key = "GEMINI_SYSTEM_PROMPT_FILE_EN" if is_en else "GEMINI_SYSTEM_PROMPT_FILE"
    env_path = (os.getenv(env_key) or "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        t = _read_utf8(p)
        if t:
            return t

    bundled = _BUNDLED_PROMPT_EN if is_en else _BUNDLED_PROMPT
    t = _read_utf8(bundled)
    if t:
        return t

    return FALLBACK_SYSTEM_INSTRUCTION_EN if is_en else FALLBACK_SYSTEM_INSTRUCTION
