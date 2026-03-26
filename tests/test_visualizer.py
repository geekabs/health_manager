"""Plotly 図のスモークテスト（描画エラーなし）。"""

from __future__ import annotations

import pandas as pd

from modules.i18n import LANG_EN, LANG_JA
from modules.visualizer import (
    fig_blood_pressure,
    fig_calories_steps,
    fig_heart_rate,
    fig_sleep,
)


def _minimal_df() -> pd.DataFrame:
    d = pd.date_range("2024-01-01", periods=3, freq="D")
    return pd.DataFrame(
        {
            "Date": d,
            "Systolic": [120.0, 118.0, 122.0],
            "Diastolic": [80.0, 78.0, 81.0],
            "HeartRate": [70.0, 72.0, 71.0],
            "DietaryEnergy": [2000.0, 2100.0, 1950.0],
            "SleepHours": [6.5, 7.0, 6.2],
            "Steps": [5000.0, 6000.0, 5500.0],
        }
    )


def test_fig_blood_pressure_empty_and_data() -> None:
    empty = pd.DataFrame(
        columns=["Date", "Systolic", "Diastolic", "HeartRate", "DietaryEnergy", "SleepHours", "Steps"]
    )
    fig_blood_pressure(empty, lang=LANG_JA)
    fig_blood_pressure(_minimal_df(), lang=LANG_EN)


def test_fig_heart_rate() -> None:
    fig_heart_rate(_minimal_df(), lang=LANG_EN)


def test_fig_calories_steps() -> None:
    fig_calories_steps(_minimal_df(), lang=LANG_JA)


def test_fig_sleep() -> None:
    fig_sleep(_minimal_df(), lang=LANG_EN)
