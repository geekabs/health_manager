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
from modules.i18n import LANG_JA, tr
from modules import ui_components as ui
from modules import visualizer as viz

load_dotenv()

st.session_state.setdefault("ui_lang", LANG_JA)

st.set_page_config(
    page_title=tr(st.session_state.ui_lang, "page_title"),
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(ui.inject_custom_css(), unsafe_allow_html=True)

lang = st.sidebar.selectbox(
    tr(st.session_state.ui_lang, "lang_label"),
    [LANG_JA, LANG_EN],
    format_func=lambda x: "日本語" if x == LANG_JA else "English",
    key="ui_lang",
)

st.markdown(f"# {tr(lang, 'app_title')}")

uploaded = st.sidebar.file_uploader(
    tr(lang, "upload_label"),
    type=["zip"],
    help=tr(lang, "upload_help"),
)
result = load_health_zip(uploaded, lang=lang)

if result.warning:
    st.warning(result.warning)

df_view = None

if result.error:
    st.error(result.error)
elif result.df is None:
    st.info(tr(lang, "info_upload"))
else:
    df_full = result.df
    min_d = df_full["Date"].min().date()
    max_d = df_full["Date"].max().date()
    st.sidebar.subheader(tr(lang, "period_header"))
    st.sidebar.caption(
        tr(
            lang,
            "period_caption_zip",
            start=min_d.isoformat(),
            end=max_d.isoformat(),
        )
    )

    _RANGE_KEYS = ("custom", "last_7d", "last_30d", "last_90d", "last_365d", "all")
    _RANGE_I18N = {
        "custom": "range_custom",
        "last_7d": "range_7d",
        "last_30d": "range_30d",
        "last_90d": "range_90d",
        "last_365d": "range_365d",
        "all": "range_all",
    }

    range_mode = st.sidebar.selectbox(
        tr(lang, "period_range_label"),
        options=list(_RANGE_KEYS),
        format_func=lambda k: tr(lang, _RANGE_I18N[k]),
        help=tr(lang, "period_range_help"),
        key="hm_range_mode",
    )

    if range_mode == "custom":
        c1, c2 = st.sidebar.columns(2)
        with c1:
            start = st.date_input(
                tr(lang, "date_start"), value=min_d, min_value=min_d, max_value=max_d, key="hm_start"
            )
        with c2:
            end = st.date_input(
                tr(lang, "date_end"), value=max_d, min_value=min_d, max_value=max_d, key="hm_end"
            )
    else:
        end = max_d
        if range_mode == "all":
            start = min_d
        else:
            days_map = {
                "last_7d": 7,
                "last_30d": 30,
                "last_90d": 90,
                "last_365d": 365,
            }
            n = days_map[range_mode]
            start = end - timedelta(days=n - 1)
            if start < min_d:
                start = min_d
        st.sidebar.caption(tr(lang, "range_applied", start=start.isoformat(), end=end.isoformat()))

    if start > end:
        st.warning(tr(lang, "warn_date_order"))
        df_view = pd.DataFrame()
    else:
        df_view = filter_by_date_range(df_full, start, end)

if df_view is not None:
    if df_view.empty:
        st.warning(tr(lang, "warn_no_rows"))
    else:
        _r0 = df_view["Date"].min().date()
        _r1 = df_view["Date"].max().date()
        _n = len(df_view)
        st.caption(tr(lang, "caption_rows", start=_r0.isoformat(), end=_r1.isoformat(), n=_n))
        kpis = compute_kpis(df_view)

        def fmt_val(v: float | None, nd: int = 1) -> str:
            if v is None:
                return "—"
            return f"{v:.{nd}f}"

        specs = [
            (tr(lang, "kpi_sys"), fmt_val(kpis["avg_systolic"], 0), "mmHg"),
            (tr(lang, "kpi_dia"), fmt_val(kpis["avg_diastolic"], 0), "mmHg"),
            (tr(lang, "kpi_hr"), fmt_val(kpis["avg_heartrate"], 0), tr(lang, "unit_bpm")),
            (tr(lang, "kpi_cal"), fmt_val(kpis["avg_calories"], 0), tr(lang, "unit_kcal")),
            (tr(lang, "kpi_sleep"), fmt_val(kpis["avg_sleep"], 1), tr(lang, "unit_hours")),
            (tr(lang, "kpi_steps"), fmt_val(kpis["avg_steps"], 0), tr(lang, "unit_steps")),
        ]

        r1 = st.columns(3)
        r2 = st.columns(3)
        for i, col in enumerate(r1 + r2):
            label, val, unit = specs[i]
            with col:
                st.markdown(ui.kpi_card_html(label, val, unit), unsafe_allow_html=True)

        st.markdown(ui.section_title_html(tr(lang, "section_trends")), unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(viz.fig_blood_pressure(df_view, lang=lang), use_container_width=True)
        with g2:
            st.plotly_chart(viz.fig_heart_rate(df_view, lang=lang), use_container_width=True)
        g3, g4 = st.columns(2)
        with g3:
            st.plotly_chart(viz.fig_calories_steps(df_view, lang=lang), use_container_width=True)
        with g4:
            st.plotly_chart(viz.fig_sleep(df_view, lang=lang), use_container_width=True)

        ecg.render_ecg_placeholder(lang=lang)

        st.markdown(ui.section_title_html(tr(lang, "section_ai")), unsafe_allow_html=True)
        if not get_api_key():
            st.warning(tr(lang, "warn_gemini_env"))

        run_btn = st.button(tr(lang, "btn_analyze"), type="primary", use_container_width=False)
        if run_btn:
            if not get_api_key():
                st.error(tr(lang, "err_gemini_env"))
            else:
                with st.spinner(tr(lang, "spinner_analyze")):
                    stats = build_stats_for_ai(df_view)
                    text, err = run_analysis(stats, lang=lang)
                if err:
                    st.error(err)
                elif text:
                    with st.container():
                        st.markdown("---")
                        st.markdown(text)
