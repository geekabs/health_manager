"""心電図（ECG）: 波形の読み込み・描画は今後実装予定。現状は UI プレースホルダーのみ。"""

from __future__ import annotations

import streamlit as st

from modules import ui_components as ui


def render_ecg_placeholder() -> None:
    """生データ未実装のためエラーにならないよう案内のみ表示する。"""
    st.markdown(ui.section_title_html("心電図"), unsafe_allow_html=True)
    st.info(
        "心電図波形の表示は、今後アップロードされたデータから読み込み・可視化する予定です。"
        " 現在は Apple Health エクスポート内の `electrocardiograms` 配下の CSV は"
        " 日次指標の集計に使わず、不要なスキップ警告にも含めません。"
    )
    st.caption("医療診断には使用できません。参考表示のみを想定しています。")
