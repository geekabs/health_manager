"""心電図（ECG）: 波形の読み込み・描画は今後実装予定。現状は UI プレースホルダーのみ。"""

from __future__ import annotations

import streamlit as st

from modules.i18n import LANG_JA, tr
from modules import ui_components as ui


def render_ecg_placeholder(lang: str = LANG_JA) -> None:
    """生データ未実装のためエラーにならないよう案内のみ表示する。"""
    st.markdown(ui.section_title_html(tr(lang, "ecg_title")), unsafe_allow_html=True)
    st.info(tr(lang, "ecg_info"))
    st.caption(tr(lang, "ecg_caption"))
