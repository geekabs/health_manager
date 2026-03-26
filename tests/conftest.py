"""共有フィクスチャ."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest


@pytest.fixture
def sample_health_df() -> pd.DataFrame:
    """日次ヘルス指標の最小 DataFrame。"""
    d = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.DataFrame(
        {
            "Date": d,
            "Systolic": [120.0, 118.0, 122.0, 119.0, 121.0],
            "Diastolic": [80.0, 78.0, 81.0, 79.0, 80.0],
            "HeartRate": [70.0, 72.0, 71.0, 73.0, 70.0],
            "DietaryEnergy": [2000.0, 2100.0, 1950.0, 2050.0, 2000.0],
            "SleepHours": [6.5, 7.0, 6.2, 6.8, 7.0],
            "Steps": [5000.0, 6000.0, 5500.0, 5200.0, 5100.0],
        }
    )


@pytest.fixture
def date_range_jan3_to_5() -> tuple[date, date]:
    return (date(2024, 1, 3), date(2024, 1, 5))
