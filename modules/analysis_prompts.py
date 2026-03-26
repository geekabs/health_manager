"""AI 分析用システム指示の読み込み。

既定はプロジェクト直下 `prompts/analysis_system.txt`（UTF-8）。
編集はそのテキストファイルを直接変更する。

優先順位:
1. 環境変数 `GEMINI_SYSTEM_PROMPT_FILE`（絶対パスまたはカレントからの相対パス）
2. 上記が未設定または読めない場合、`prompts/analysis_system.txt`
3. ファイルが存在しない場合のみ、モジュール内の短いフォールバック
"""

from __future__ import annotations

import os
from pathlib import Path

# プロジェクトルート（modules/ の親）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BUNDLED_PROMPT = _PROJECT_ROOT / "prompts" / "analysis_system.txt"

FALLBACK_SYSTEM_INSTRUCTION = (
    "健康データの集計のみを根拠に、簡潔に生活習慣の観点から整理せよ。"
    "診断・治療指示は行わない。Markdown、箇条書き優先。"
)


def _read_utf8(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
        return text or None
    except OSError:
        return None


def load_system_instruction() -> str:
    """分析のたびに呼ぶ。テキストファイルを UTF-8 で読み込む。"""
    env_path = (os.getenv("GEMINI_SYSTEM_PROMPT_FILE") or "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        t = _read_utf8(p)
        if t:
            return t

    t = _read_utf8(_BUNDLED_PROMPT)
    if t:
        return t

    return FALLBACK_SYSTEM_INSTRUCTION
