"""Streamlit ヘルスケアダッシュボード."""

from __future__ import annotations

from datetime import timedelta

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from modules.ai_analyzer import get_api_key, run_analysis
from modules.data_loader import (
    build_stats_for_ai,
    compute_kpis,
    filter_by_date_range,
    load_health_zip,
)
from modules import ecg
from modules import ui_components as ui
from modules import visualizer as viz

load_dotenv()

st.set_page_config(page_title="ヘルスケアダッシュボード", layout="wide", initial_sidebar_state="expanded")
st.markdown(ui.inject_custom_css(), unsafe_allow_html=True)

st.markdown("# ヘルスケアダッシュボード")

uploaded = st.sidebar.file_uploader(
    "ヘルスデータ ZIP（ドラッグ＆ドロップ、またはファイルを選択）",
    type=["zip"],
    help="エクスポートアプリが出力した .zip（複数フォルダ内の CSV を含む想定）。1 ファイルあたり最大 200MB。",
)
result = load_health_zip(uploaded)

if result.warning:
    st.warning(result.warning)

df_view = None

if result.error:
    st.error(result.error)
elif result.df is None:
    st.info("サイドバーから ZIP ファイルをアップロードしてください。")
else:
    df_full = result.df
    min_d = df_full["Date"].min().date()
    max_d = df_full["Date"].max().date()
    st.sidebar.subheader("表示する期間")
    st.sidebar.caption(
        f"ZIP 内のデータ日付: {min_d.isoformat()} ～ {max_d.isoformat()}（この範囲で絞り込み）"
    )
    range_mode = st.sidebar.selectbox(
        "期間の指定",
        [
            "カスタム（開始・終了を個別に選ぶ）",
            "過去7日",
            "過去30日",
            "過去90日",
            "過去1年（365日）",
            "全期間",
        ],
        help="KPI・グラフ・AI 分析は、ここで選んだ期間の行だけを使います。",
    )

    if range_mode.startswith("カスタム"):
        c1, c2 = st.sidebar.columns(2)
        with c1:
            start = st.date_input("開始日", value=min_d, min_value=min_d, max_value=max_d, key="hm_start")
        with c2:
            end = st.date_input("終了日", value=max_d, min_value=min_d, max_value=max_d, key="hm_end")
    else:
        end = max_d
        if range_mode == "全期間":
            start = min_d
        else:
            days_map = {
                "過去7日": 7,
                "過去30日": 30,
                "過去90日": 90,
                "過去1年（365日）": 365,
            }
            n = days_map[range_mode]
            # 終了日を含む n 日分（末日 = max_d）
            start = end - timedelta(days=n - 1)
            if start < min_d:
                start = min_d
        st.sidebar.caption(f"適用中: {start.isoformat()} ～ {end.isoformat()}")

    if start > end:
        st.warning("開始日は終了日以前にしてください。")
        df_view = pd.DataFrame()
    else:
        df_view = filter_by_date_range(df_full, start, end)

if df_view is not None:
    if df_view.empty:
        st.warning("選択期間にデータがありません。")
    else:
        _r0 = df_view["Date"].min().date()
        _r1 = df_view["Date"].max().date()
        _n = len(df_view)
        st.caption(f"表示中の集計期間: {_r0.isoformat()} ～ {_r1.isoformat()}（{_n} 行）")
        kpis = compute_kpis(df_view)

        def fmt_val(v: float | None, nd: int = 1) -> str:
            if v is None:
                return "—"
            return f"{v:.{nd}f}"

        specs = [
            ("平均 最高血圧", fmt_val(kpis["avg_systolic"], 0), "mmHg"),
            ("平均 最低血圧", fmt_val(kpis["avg_diastolic"], 0), "mmHg"),
            ("平均 心拍数", fmt_val(kpis["avg_heartrate"], 0), "回/分"),
            ("平均 摂取カロリー", fmt_val(kpis["avg_calories"], 0), "キロカロリー"),
            ("平均 睡眠時間", fmt_val(kpis["avg_sleep"], 1), "時間"),
            ("平均 歩数", fmt_val(kpis["avg_steps"], 0), "歩"),
        ]

        r1 = st.columns(3)
        r2 = st.columns(3)
        for i, col in enumerate(r1 + r2):
            label, val, unit = specs[i]
            with col:
                st.markdown(ui.kpi_card_html(label, val, unit), unsafe_allow_html=True)

        st.markdown(ui.section_title_html("トレンド"), unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(viz.fig_blood_pressure(df_view), use_container_width=True)
        with g2:
            st.plotly_chart(viz.fig_heart_rate(df_view), use_container_width=True)
        g3, g4 = st.columns(2)
        with g3:
            st.plotly_chart(viz.fig_calories_steps(df_view), use_container_width=True)
        with g4:
            st.plotly_chart(viz.fig_sleep(df_view), use_container_width=True)

        ecg.render_ecg_placeholder()

        st.markdown(ui.section_title_html("AI 分析"), unsafe_allow_html=True)
        if not get_api_key():
            st.warning("`.env` に GEMINI_API_KEY を設定してください。")

        run_btn = st.button("分析を実行", type="primary", use_container_width=False)
        if run_btn:
            if not get_api_key():
                st.error("API キーが未設定です。`.env` に GEMINI_API_KEY を記載してください。")
            else:
                with st.spinner("分析中..."):
                    stats = build_stats_for_ai(df_view)
                    text, err = run_analysis(stats)
                if err:
                    st.error(err)
                elif text:
                    with st.container():
                        st.markdown("---")
                        st.markdown(text)
