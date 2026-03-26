"""analysis_prompts の読み込み."""

from __future__ import annotations

from modules.analysis_prompts import (
    FALLBACK_SYSTEM_INSTRUCTION,
    load_system_instruction,
)
from modules.i18n import LANG_EN, LANG_JA


def test_load_system_instruction_ja_non_empty() -> None:
    s = load_system_instruction(LANG_JA)
    assert isinstance(s, str)
    assert len(s) > 20


def test_load_system_instruction_en_non_empty() -> None:
    s = load_system_instruction(LANG_EN)
    assert isinstance(s, str)
    assert len(s) > 20
    # 英語プロンプトは bundled かフォールバック
    assert "health" in s.lower() or "lifestyle" in s.lower() or "markdown" in s.lower()


def test_fallback_constant_exists() -> None:
    assert "健康" in FALLBACK_SYSTEM_INSTRUCTION or len(FALLBACK_SYSTEM_INSTRUCTION) > 10
