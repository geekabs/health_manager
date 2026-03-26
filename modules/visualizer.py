"""Plotly 可視化."""

from __future__ import annotations

import pandas as pd

from modules.i18n import LANG_JA, tr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_GRID = "rgba(0,0,0,0.06)"
_LINE = "rgba(0,0,0,0.45)"


def _base_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1d1d1f")),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#fafbfc",
        margin=dict(l=50, r=30, t=50, b=50),
        hovermode="x unified",
        font=dict(color="#1d1d1f", family="system-ui, sans-serif"),
        legend=dict(
            font=dict(color="#1d1d1f", size=12),
            bgcolor="rgba(255,255,255,0.97)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1,
        ),
        hoverlabel=dict(
            font=dict(color="#1d1d1f", size=13),
            bgcolor="#ffffff",
            bordercolor="rgba(0,0,0,0.12)",
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=_GRID,
            zeroline=False,
            linecolor=_LINE,
            tickfont=dict(color="#3a3a3c"),
            title_font=dict(color="#1d1d1f"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=_GRID,
            zeroline=False,
            linecolor=_LINE,
            tickfont=dict(color="#3a3a3c"),
            title_font=dict(color="#1d1d1f"),
        ),
    )
    return fig


def fig_blood_pressure(df: pd.DataFrame, lang: str = LANG_JA) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        fig.add_annotation(
            text=tr(lang, "chart_no_data"),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color="#3a3a3c", size=14),
        )
        out = _base_layout(fig, tr(lang, "chart_bp_title"))
        out.update_yaxes(title_text=tr(lang, "chart_bp_yaxis"))
        return out

    x = df["Date"]
    fig.add_trace(
        go.Scatter(
            x=x,
            y=df["Diastolic"],
            name=tr(lang, "legend_diastolic"),
            mode="lines",
            line=dict(color="#34c759", width=2, shape="spline"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=df["Systolic"],
            name=tr(lang, "legend_systolic"),
            mode="lines",
            line=dict(color="#ff3b30", width=2.5, shape="spline"),
            fill="tonexty",
            fillcolor="rgba(255,59,48,0.12)",
        )
    )
    out = _base_layout(fig, tr(lang, "chart_bp_title"))
    out.update_yaxes(title_text=tr(lang, "chart_bp_yaxis"))
    return out


def fig_heart_rate(df: pd.DataFrame, lang: str = LANG_JA) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        fig.add_annotation(
            text=tr(lang, "chart_no_data"),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color="#3a3a3c", size=14),
        )
        out = _base_layout(fig, tr(lang, "chart_hr_title"))
        out.update_yaxes(title_text=tr(lang, "chart_hr_yaxis"))
        return out

    d = df.sort_values("Date").copy()
    d = d.set_index("Date")
    ma = d["HeartRate"].rolling("7D", min_periods=1).mean()
    d = d.reset_index()

    fig.add_trace(
        go.Scatter(
            x=d["Date"],
            y=d["HeartRate"],
            name=tr(lang, "legend_hr_raw"),
            mode="lines",
            line=dict(color="rgba(10,132,255,0.35)", width=1.2, shape="spline"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ma.index,
            y=ma.values,
            name=tr(lang, "legend_hr_ma"),
            mode="lines",
            line=dict(color="#007aff", width=3, shape="spline"),
        )
    )
    out = _base_layout(fig, tr(lang, "chart_hr_title"))
    out.update_yaxes(title_text=tr(lang, "chart_hr_yaxis"))
    return out


def fig_calories_steps(df: pd.DataFrame, lang: str = LANG_JA) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if df.empty:
        fig.add_annotation(
            text=tr(lang, "chart_no_data"),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color="#3a3a3c", size=14),
        )
        out = _base_layout(fig, tr(lang, "chart_cal_steps_title"))
        out.update_yaxes(
            title_text=tr(lang, "chart_yaxis_kcal"), secondary_y=False, gridcolor=_GRID, showgrid=True
        )
        out.update_yaxes(
            title_text=tr(lang, "chart_yaxis_steps"), secondary_y=True, gridcolor="rgba(0,0,0,0)", showgrid=False
        )
        return out

    x = df["Date"]
    fig.add_trace(
        go.Bar(
            x=x,
            y=df["DietaryEnergy"],
            name=tr(lang, "legend_cal"),
            marker=dict(color="rgba(255,149,0,0.85)", line=dict(width=0), cornerradius=6),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=df["Steps"],
            name=tr(lang, "legend_steps"),
            mode="lines",
            line=dict(color="#5856d6", width=2.5, shape="spline"),
        ),
        secondary_y=True,
    )
    fig.update_layout(barmode="overlay", bargap=0.25)
    out = _base_layout(fig, tr(lang, "chart_cal_steps_title"))
    out.update_yaxes(title_text=tr(lang, "chart_yaxis_kcal"), secondary_y=False, gridcolor=_GRID, showgrid=True)
    out.update_yaxes(
        title_text=tr(lang, "chart_yaxis_steps"), secondary_y=True, gridcolor="rgba(0,0,0,0)", showgrid=False
    )
    return out


def fig_sleep(df: pd.DataFrame, lang: str = LANG_JA) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        fig.add_annotation(
            text=tr(lang, "chart_no_data"),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color="#3a3a3c", size=14),
        )
        out = _base_layout(fig, tr(lang, "chart_sleep_title"))
        out.update_yaxes(title_text=tr(lang, "chart_sleep_yaxis"))
        return out

    fig.add_trace(
        go.Bar(
            x=df["Date"],
            y=df["SleepHours"],
            name=tr(lang, "legend_sleep"),
            marker=dict(color="rgba(88,86,214,0.75)", line=dict(width=0), cornerradius=5),
        )
    )
    fig.update_layout(bargap=0.2)
    out = _base_layout(fig, tr(lang, "chart_sleep_title"))
    out.update_yaxes(title_text=tr(lang, "chart_sleep_yaxis"))
    return out
