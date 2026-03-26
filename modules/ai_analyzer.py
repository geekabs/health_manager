"""Gemini API による統計ベースの分析."""

from __future__ import annotations

import json
import os
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

from modules.analysis_prompts import load_system_instruction

load_dotenv()

# 古い gemini-1.5-flash は API で 404 になることがある。`.env` で GEMINI_MODEL を上書き可。
MODEL_NAME = (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()


def get_api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def run_analysis(stats: dict[str, Any]) -> tuple[str | None, str | None]:
    """統計 dict のみを送信。戻り値: (markdown, error_message)"""
    key = get_api_key()
    if not key:
        return None, "`.env` に GEMINI_API_KEY が設定されていません。"

    genai.configure(api_key=key)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=load_system_instruction(),
    )
    user = (
        "以下は選択期間の集計のみ（個票・生ログ・身元情報は含まない）。\n\n"
        + json.dumps(stats, ensure_ascii=False, indent=2)
    )
    try:
        resp = model.generate_content(user)
        text = getattr(resp, "text", None)
        if not text and getattr(resp, "candidates", None):
            parts = []
            for c in resp.candidates:
                for p in getattr(c.content, "parts", []) or []:
                    if getattr(p, "text", None):
                        parts.append(p.text)
            text = "\n".join(parts) if parts else None
        if not text:
            return None, "モデルからの応答を取得できませんでした。"
        return text, None
    except Exception as e:
        return None, f"Gemini API の呼び出しに失敗しました: {e}"
