"""data_loader の公開 API と一部内部ヘルパ。"""

from __future__ import annotations

from datetime import date
from io import BytesIO
import zipfile

import pandas as pd
import pytest

from modules.data_loader import (
    build_stats_for_ai,
    compute_kpis,
    filter_by_date_range,
    load_health_zip,
    _classify_file,
    _process_csv_bytes,
)
from modules.i18n import LANG_EN


def test_load_health_zip_none() -> None:
    r = load_health_zip(None, lang="ja")
    assert r.df is None
    assert r.error is None


def test_filter_by_date_range(sample_health_df: pd.DataFrame, date_range_jan3_to_5: tuple[date, date]) -> None:
    start, end = date_range_jan3_to_5
    out = filter_by_date_range(sample_health_df, start, end)
    assert len(out) == 3
    assert out["Date"].min().date() == start
    assert out["Date"].max().date() == end


def test_filter_by_date_range_empty() -> None:
    empty = pd.DataFrame(columns=["Date", "Systolic"])
    out = filter_by_date_range(empty, date(2024, 1, 1), date(2024, 1, 2))
    assert out.empty


def test_compute_kpis(sample_health_df: pd.DataFrame) -> None:
    k = compute_kpis(sample_health_df)
    assert k["avg_systolic"] is not None
    assert pytest.approx(k["avg_systolic"], rel=1e-6) == sample_health_df["Systolic"].mean()
    assert k["avg_steps"] is not None


def test_compute_kpis_empty() -> None:
    df = pd.DataFrame(
        {
            "Date": pd.DatetimeIndex([]),
            "Systolic": [],
            "Diastolic": [],
            "HeartRate": [],
            "DietaryEnergy": [],
            "SleepHours": [],
            "Steps": [],
        }
    )
    k = compute_kpis(df)
    assert k["avg_systolic"] is None


def test_build_stats_for_ai(sample_health_df: pd.DataFrame) -> None:
    stats = build_stats_for_ai(sample_health_df)
    assert stats["row_count"] == 5
    assert stats["date_range"] is not None
    assert "Systolic" in stats["columns"]
    assert stats["columns"]["Systolic"]["count_non_null"] == 5


def test_build_stats_for_ai_empty() -> None:
    stats = build_stats_for_ai(pd.DataFrame())
    assert stats["row_count"] == 0
    assert stats["date_range"] is None


def test_classify_file_steps() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "steps": [4000, 5000],
        }
    )
    assert _classify_file("export_steps_daily.csv", df) == "steps"


def test_process_csv_bytes_steps() -> None:
    raw = b"date,steps\n2024-01-01,4000\n2024-01-02,5000\n"
    frames, skipped = _process_csv_bytes("my_steps.csv", raw)
    assert skipped == 0
    assert len(frames) == 1
    assert "Steps" in frames[0].columns
    assert "Date" in frames[0].columns


def test_process_csv_bytes_invalid_utf8_returns_skip() -> None:
    raw = bytes([0xFF, 0xFE, 0x41])
    frames, skipped = _process_csv_bytes("bad.csv", raw)
    assert frames == []
    assert skipped == 1


def test_load_health_zip_invalid_not_zip() -> None:
    class Fake:
        def getvalue(self) -> bytes:
            return b"not a zip"

    r = load_health_zip(Fake(), lang="en")
    assert r.df is None
    assert r.error is not None
    assert "ZIP" in r.error or "zip" in r.error.lower()


def test_load_health_zip_warn_message_english() -> None:
    """空の ZIP（CSV なし）ではエラー文言が英語になる。"""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "hello")
    raw = buf.getvalue()

    class Fake:
        def getvalue(self) -> bytes:
            return raw

    r = load_health_zip(Fake(), lang=LANG_EN)
    assert r.df is None
    assert r.error is not None
