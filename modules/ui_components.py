"""カスタム CSS とカード UI."""

from __future__ import annotations


def inject_custom_css() -> str:
    return """
<style>
    .stApp {
        font-family: system-ui, -apple-system, "Segoe UI", "Hiragino Sans",
            "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Yu Gothic UI", "Meiryo", sans-serif;
        background: linear-gradient(180deg, #eef1f6 0%, #e4e8f0 100%);
        color: #1d1d1f;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    /* 上部ツールバー・ヘッダーを明るく統一 */
    header[data-testid="stHeader"] {
        background: rgba(255, 255, 255, 0.92) !important;
        border-bottom: 1px solid rgba(0, 0, 0, 0.06) !important;
    }
    [data-testid="stToolbar"] {
        background: transparent !important;
    }
    /* アラート: 黄背景でも本文を濃色で必ず読めるように */
    div[data-testid="stAlert"] {
        border-radius: 10px !important;
    }
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] span,
    div[data-testid="stAlert"] div[role="alert"] {
        color: #1a1a1a !important;
        font-weight: 500 !important;
    }
    div[data-testid="stAlert"][data-baseweb="notification"] {
        background-color: #fff8e6 !important;
        border: 1px solid #f0c14d !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fc 0%, #f0f2f7 100%) !important;
        border-right: 1px solid rgba(0,0,0,0.06);
    }
    /* サイドバー入力: ダークブロックをやわらかいライトに */
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div {
        background-color: #ffffff !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
        color: #1d1d1f !important;
        border-radius: 10px !important;
    }
    [data-testid="stFileUploader"] section {
        background: #ffffff !important;
        border: 1px dashed rgba(0, 0, 0, 0.18) !important;
        border-radius: 12px !important;
        color: #1d1d1f !important;
    }
    [data-testid="stFileUploader"] section small,
    [data-testid="stFileUploader"] section span {
        color: #3a3a3c !important;
    }
    [data-testid="stFileUploader"] button {
        border-radius: 8px !important;
    }
    /* メイン見出し */
    .main h1 {
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        color: #0f172a !important;
    }
    .hm-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(0, 0, 0, 0.04);
        min-height: 92px;
    }
    .hm-card-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #6e6e73;
        letter-spacing: 0.02em;
        margin-bottom: 0.35rem;
    }
    .hm-card-value {
        font-size: 1.45rem;
        font-weight: 650;
        color: #1d1d1f;
        line-height: 1.2;
    }
    .hm-card-unit {
        font-size: 0.85rem;
        font-weight: 500;
        color: #86868b;
        margin-left: 0.2rem;
    }
    .hm-section-title {
        font-size: 1.05rem;
        font-weight: 650;
        color: #1d1d1f;
        margin: 1.25rem 0 0.75rem 0;
        letter-spacing: -0.01em;
    }
    .hm-ai-box {
        background: #ffffff;
        border-radius: 14px;
        padding: 1.25rem 1.35rem;
        box-shadow: 0 2px 16px rgba(0, 0, 0, 0.07);
        border: 1px solid rgba(0, 0, 0, 0.05);
        margin-top: 0.5rem;
    }
</style>
"""


def kpi_card_html(label: str, value: str, unit: str = "") -> str:
    unit_html = f'<span class="hm-card-unit">{unit}</span>' if unit else ""
    return f"""
<div class="hm-card">
  <div class="hm-card-label">{label}</div>
  <div class="hm-card-value">{value}{unit_html}</div>
</div>
"""


def section_title_html(text: str) -> str:
    return f'<p class="hm-section-title">{text}</p>'
