"""ヘルスケア ZIP の読み込み・検証・期間フィルタ・集計."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "Date",
    "Systolic",
    "Diastolic",
    "HeartRate",
    "DietaryEnergy",
    "SleepHours",
    "Steps",
]

NUMERIC_COLUMNS = [
    "Systolic",
    "Diastolic",
    "HeartRate",
    "DietaryEnergy",
    "SleepHours",
    "Steps",
]

ZIP_LOAD_ERROR = "有効なヘルスケアデータのZIPファイルをアップロードしてください"


@dataclass
class LoadResult:
    df: pd.DataFrame | None
    error: str | None = None
    warning: str | None = None


_DATE_PRIORITY = (
    "startdate",
    "creationdate",
    "date",
    "enddate",
    "start date",
    "end date",
    "datetime",
    "time",
)

_TYPE_COL_NAMES = ("type", "typename", "hktype", "quantity type")

# Apple Health 公式 ZIP は apple_health_export/export.xml に全 Quantity/Category を格納
_APPLE_EXPORT_XML_PATHS = (
    "apple_health_export/export.xml",
    "apple_health_export\\export.xml",
)
_HK_HEART = "HKQuantityTypeIdentifierHeartRate"
_HK_STEPS = "HKQuantityTypeIdentifierStepCount"
_HK_DIETARY = "HKQuantityTypeIdentifierDietaryEnergyConsumed"
_HK_SYS = "HKQuantityTypeIdentifierBloodPressureSystolic"
_HK_DIA = "HKQuantityTypeIdentifierBloodPressureDiastolic"
_HK_SLEEP = "HKCategoryTypeIdentifierSleepAnalysis"



def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _should_skip_zip_path(name: str) -> bool:
    norm = name.replace("\\", "/")
    parts = norm.split("/")
    if "__MACOSX" in parts:
        return True
    base = parts[-1] if parts else name
    if base == ".DS_Store" or base.startswith("._"):
        return True
    # Apple Health: ECG は波形 CSV のみでダッシュボード指標ではない（スキップ警告に含めない）
    if "electrocardiograms" in norm.lower():
        return True
    return False


def _is_csv_entry(name: str) -> bool:
    if not name or name.endswith("/"):
        return False
    return name.lower().endswith(".csv")




def _find_apple_export_xml(zf: zipfile.ZipFile) -> str | None:
    for p in _APPLE_EXPORT_XML_PATHS:
        try:
            zf.getinfo(p)
            return p
        except KeyError:
            continue
    return None


def _parse_apple_date_to_day(s: str | None) -> pd.Timestamp | None:
    if not s:
        return None
    ts = pd.Timestamp(s)
    if pd.isna(ts):
        return None
    return ts.normalize()


def _frames_from_apple_export_xml(zf: zipfile.ZipFile, inner_path: str) -> list[pd.DataFrame]:
    hr_by_day: dict[pd.Timestamp, list[float]] = defaultdict(list)
    steps_by_day: dict[pd.Timestamp, float] = defaultdict(float)
    dietary_by_day: dict[pd.Timestamp, float] = defaultdict(float)
    sys_by_day: dict[pd.Timestamp, list[float]] = defaultdict(list)
    dia_by_day: dict[pd.Timestamp, list[float]] = defaultdict(list)
    sleep_by_day: dict[pd.Timestamp, float] = defaultdict(float)

    with zf.open(inner_path) as fp:
        for _event, elem in ET.iterparse(fp, events=("end",)):
            if elem.tag != "Record":
                elem.clear()
                continue
            att = elem.attrib
            rtype = att.get("type", "")
            try:
                if rtype == _HK_HEART:
                    v = att.get("value")
                    if v is None:
                        raise ValueError
                    day = _parse_apple_date_to_day(att.get("startDate"))
                    if day is not None:
                        hr_by_day[day].append(float(v))
                elif rtype == _HK_STEPS:
                    v = att.get("value")
                    if v is None:
                        raise ValueError
                    day = _parse_apple_date_to_day(att.get("startDate"))
                    if day is not None:
                        steps_by_day[day] += float(v)
                elif rtype == _HK_DIETARY:
                    v = att.get("value")
                    if v is None:
                        raise ValueError
                    day = _parse_apple_date_to_day(att.get("startDate"))
                    if day is not None:
                        unit = (att.get("unit") or "").lower()
                        val = float(v)
                        if "kilocalorie" in unit or "kcal" in unit:
                            dietary_by_day[day] += val
                        elif "calorie" in unit and "kilo" not in unit:
                            dietary_by_day[day] += val / 1000.0
                        else:
                            dietary_by_day[day] += val
                elif rtype == _HK_SYS:
                    v = att.get("value")
                    if v is None:
                        raise ValueError
                    day = _parse_apple_date_to_day(att.get("startDate"))
                    if day is not None:
                        sys_by_day[day].append(float(v))
                elif rtype == _HK_DIA:
                    v = att.get("value")
                    if v is None:
                        raise ValueError
                    day = _parse_apple_date_to_day(att.get("startDate"))
                    if day is not None:
                        dia_by_day[day].append(float(v))
                elif rtype == _HK_SLEEP:
                    val = att.get("value") or ""
                    if "Asleep" in val:
                        sd = _parse_apple_date_to_day(att.get("startDate"))
                        ed_raw = att.get("endDate")
                        if sd is not None and ed_raw:
                            t0 = pd.Timestamp(att.get("startDate"))
                            t1 = pd.Timestamp(ed_raw)
                            if pd.notna(t0) and pd.notna(t1) and t1 > t0:
                                hours = (t1 - t0).total_seconds() / 3600.0
                                if hours > 0:
                                    sleep_by_day[sd] += hours
            except (TypeError, ValueError):
                pass
            elem.clear()

    out: list[pd.DataFrame] = []
    if hr_by_day:
        keys = sorted(hr_by_day.keys())
        out.append(
            pd.DataFrame(
                {
                    "Date": keys,
                    "HeartRate": [sum(hr_by_day[d]) / len(hr_by_day[d]) for d in keys],
                }
            )
        )
    if steps_by_day:
        keys = sorted(steps_by_day.keys())
        out.append(pd.DataFrame({"Date": keys, "Steps": [steps_by_day[d] for d in keys]}))
    if dietary_by_day:
        keys = sorted(dietary_by_day.keys())
        out.append(pd.DataFrame({"Date": keys, "DietaryEnergy": [dietary_by_day[d] for d in keys]}))
    if sys_by_day:
        keys = sorted(sys_by_day.keys())
        out.append(
            pd.DataFrame(
                {"Date": keys, "Systolic": [sum(sys_by_day[d]) / len(sys_by_day[d]) for d in keys]}
            )
        )
    if dia_by_day:
        keys = sorted(dia_by_day.keys())
        out.append(
            pd.DataFrame(
                {"Date": keys, "Diastolic": [sum(dia_by_day[d]) / len(dia_by_day[d]) for d in keys]}
            )
        )
    if sleep_by_day:
        keys = sorted(sleep_by_day.keys())
        out.append(pd.DataFrame({"Date": keys, "SleepHours": [sleep_by_day[d] for d in keys]}))
    return out


def _score_text_for_metrics(text: str) -> dict[str, float]:
    t = text.lower()
    scores = {"bp_sys": 0.0, "bp_dia": 0.0, "bp": 0.0, "heart": 0.0, "energy": 0.0, "sleep": 0.0, "steps": 0.0}
    if "systolic" in t or "bloodpressuresystolic" in t:
        scores["bp_sys"] += 2.0
        scores["bp"] += 1.0
    if "diastolic" in t or "bloodpressurediastolic" in t:
        scores["bp_dia"] += 2.0
        scores["bp"] += 1.0
    if "bloodpressure" in t or "blood pressure" in t:
        scores["bp"] += 1.5
    if any(k in t for k in ("heartrate", "heart rate", "heart_rate", "pulse", "bpm")):
        scores["heart"] += 2.5
    if any(k in t for k in ("stepcount", "step count", "steps", "pedometer")):
        scores["steps"] += 2.5
    if any(k in t for k in ("dietaryenergy", "dietary energy", "activeenergy", "active energy", "calorie", "kilocalorie")):
        scores["energy"] += 2.0
    if "sleep" in t and "analysis" not in t:
        scores["sleep"] += 2.0
    return scores


def _merge_scores(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    keys = set(a) | set(b)
    return {k: a.get(k, 0.0) + b.get(k, 0.0) for k in keys}


def _find_type_column(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if _norm_key(str(c)) in {_norm_key(x) for x in _TYPE_COL_NAMES}:
            return c
        nk = _norm_key(str(c))
        if nk == "type" or nk.endswith("typeidentifier"):
            return c
    return None


def _find_date_column(df: pd.DataFrame) -> str | None:
    mapped = {_norm_key(str(c)): c for c in df.columns}
    for pref in _DATE_PRIORITY:
        nk = _norm_key(pref)
        if nk in mapped:
            return mapped[nk]
    for c in df.columns:
        nk = _norm_key(str(c))
        if "date" in nk or nk in ("start", "end"):
            return c
    return None


def _find_value_column(df: pd.DataFrame, skip: set[str]) -> str | None:
    for name in ("value", "val", "quantity", "amount"):
        for c in df.columns:
            if c in skip:
                continue
            if _norm_key(str(c)) == _norm_key(name):
                return c
    for c in df.columns:
        if c in skip:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            return c
    return None


def _parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce").dt.tz_localize(None)


def _to_day_date(series: pd.Series) -> pd.Series:
    dt = _parse_dates(series)
    return pd.to_datetime(dt.dt.normalize())


def _classify_file(filename: str, df: pd.DataFrame) -> str | None:
    if df.empty or len(df.columns) == 0:
        return None
    scores = _score_text_for_metrics(filename)
    cols_blob = " ".join(str(c) for c in df.columns)
    scores = _merge_scores(scores, _score_text_for_metrics(cols_blob))
    sample_n = min(30, len(df))
    tcol = _find_type_column(df)
    if tcol is not None:
        blob = " ".join(df[tcol].astype(str).head(sample_n))
        scores = _merge_scores(scores, _score_text_for_metrics(blob))
    # Wide BP: two columns
    col_norms = {_norm_key(str(c)): c for c in df.columns}
    has_sys_col = any(
        x in col_norms
        for x in ("systolic", "bloodpressuresystolic", "bpsystolic", "systolicmmhg")
    ) or any("systolic" in _norm_key(str(c)) for c in df.columns)
    has_dia_col = any(
        x in col_norms
        for x in ("diastolic", "bloodpressurediastolic", "bpdiastolic", "diastolicmmhg")
    ) or any("diastolic" in _norm_key(str(c)) for c in df.columns)
    if has_sys_col and has_dia_col:
        scores["bp"] += 5.0
    best = max(scores.values()) if scores else 0.0
    if best < 1.5:
        return None
    # Resolve tie: prefer BP wide, then long categories
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    top_name, top_val = ranked[0]
    if top_val < 1.5:
        return None
    if has_sys_col and has_dia_col and scores.get("bp", 0) >= 1.5:
        return "bp_wide"
    if tcol is not None and (scores.get("bp_sys", 0) > 0 or scores.get("bp_dia", 0) > 0) and scores.get("bp", 0) >= 2:
        return "bp_long"
    if top_name == "bp_sys" and scores.get("bp_dia", 0) < 1:
        return "bp_sys_only"
    if top_name == "bp_dia" and scores.get("bp_sys", 0) < 1:
        return "bp_dia_only"
    mapping = {
        "bp": "bp_long" if tcol is not None else None,
        "heart": "heart",
        "energy": "energy",
        "sleep": "sleep",
        "steps": "steps",
    }
    if top_name.startswith("bp"):
        if has_sys_col and has_dia_col:
            return "bp_wide"
        if tcol is not None:
            return "bp_long"
        if top_name == "bp_sys":
            return "bp_sys_only"
        if top_name == "bp_dia":
            return "bp_dia_only"
        return None
    return mapping.get(top_name)


def _col_matching(df: pd.DataFrame, substr: str) -> str | None:
    sub = _norm_key(substr)
    for c in df.columns:
        if sub in _norm_key(str(c)):
            return c
    return None


def _extract_bp_wide(df: pd.DataFrame) -> pd.DataFrame:
    dcol = _find_date_column(df)
    scol = _col_matching(df, "systolic")
    dicol = _col_matching(df, "diastolic")
    if not dcol or not scol or not dicol:
        return pd.DataFrame(columns=["Date", "Systolic", "Diastolic"])
    out = pd.DataFrame(
        {
            "Date": _to_day_date(df[dcol]),
            "Systolic": pd.to_numeric(df[scol], errors="coerce"),
            "Diastolic": pd.to_numeric(df[dicol], errors="coerce"),
        }
    )
    return out.dropna(subset=["Date"])


def _row_metric_from_type(type_str: str) -> str | None:
    t = str(type_str).lower()
    if "bloodpressure" in t.replace(" ", "") or "blood_pressure" in t:
        if "systolic" in t:
            return "Systolic"
        if "diastolic" in t:
            return "Diastolic"
    if "systolic" in t and "diastolic" not in t:
        return "Systolic"
    if "diastolic" in t:
        return "Diastolic"
    if "heartrate" in t.replace(" ", "") or "heart_rate" in t:
        return "HeartRate"
    if "stepcount" in t.replace(" ", ""):
        return "Steps"
    if any(x in t for x in ("dietaryenergy", "activeenergy", "dietary energy")):
        return "DietaryEnergy"
    if "sleep" in t and "analysis" not in t:
        return "SleepHours"
    return None


def _extract_long(df: pd.DataFrame) -> list[pd.DataFrame]:
    tcol = _find_type_column(df)
    dcol = _find_date_column(df)
    if not tcol or not dcol:
        return []
    vcol = _find_value_column(df, {tcol, dcol})
    if not vcol:
        return []
    unit_col = None
    for c in df.columns:
        if _norm_key(str(c)) == "unit":
            unit_col = c
            break
    frames: list[pd.DataFrame] = []
    dates = _to_day_date(df[dcol])
    types = df[tcol].astype(str)
    vals = pd.to_numeric(df[vcol], errors="coerce")
    units = df[unit_col].astype(str) if unit_col else None

    systolic_rows: list[pd.Series] = []
    diastolic_rows: list[pd.Series] = []
    other: dict[str, list[pd.Series]] = {k: [] for k in ("HeartRate", "Steps", "DietaryEnergy", "SleepHours")}

    for i in range(len(df)):
        m = _row_metric_from_type(types.iloc[i])
        if m is None:
            continue
        val = vals.iloc[i]
        if pd.isna(val):
            continue
        date_v = dates.iloc[i]
        if pd.isna(date_v):
            continue
        u = units.iloc[i].lower() if units is not None else ""
        if m == "SleepHours":
            if "min" in u and "hour" not in u:
                val = val / 60.0
        if m == "Systolic":
            systolic_rows.append(pd.Series({"Date": date_v, "Systolic": val}))
        elif m == "Diastolic":
            diastolic_rows.append(pd.Series({"Date": date_v, "Diastolic": val}))
        elif m in other:
            other[m].append(pd.Series({"Date": date_v, m: val}))

    if systolic_rows:
        frames.append(pd.DataFrame(systolic_rows))
    if diastolic_rows:
        frames.append(pd.DataFrame(diastolic_rows))
    for k, rows in other.items():
        if rows:
            frames.append(pd.DataFrame(rows))
    return frames


def _extract_single_metric(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    dcol = _find_date_column(df)
    if not dcol:
        return pd.DataFrame(columns=["Date", metric])
    skip = {dcol}
    vcol = _find_value_column(df, skip)
    if not vcol:
        return pd.DataFrame(columns=["Date", metric])
    unit_col = None
    for c in df.columns:
        if _norm_key(str(c)) == "unit":
            unit_col = c
            break
    out = pd.DataFrame(
        {
            "Date": _to_day_date(df[dcol]),
            metric: pd.to_numeric(df[vcol], errors="coerce"),
        }
    )
    if metric == "SleepHours" and unit_col is not None:
        u = df[unit_col].astype(str).str.lower()
        mask = u.str.contains("min") & ~u.str.contains("hour")
        out.loc[mask, metric] = out.loc[mask, metric] / 60.0
    out = out.dropna(subset=["Date"])
    return out


def _process_csv_bytes(filename: str, data: bytes) -> tuple[list[pd.DataFrame], int]:
    """Returns list of partial frames (Date + 1-2 metric cols) and skip count."""
    skipped = 0
    try:
        df = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")
    except Exception:
        return [], 1
    if df.empty:
        return [], 0
    tcol = _find_type_column(df)
    dcol = _find_date_column(df)
    if tcol is not None and dcol is not None:
        vcol = _find_value_column(df, {tcol, dcol})
        if vcol is not None:
            long_frames = _extract_long(df)
            if long_frames:
                return long_frames, 0
    kind = _classify_file(filename, df)
    if kind is None:
        return [], 1
    frames: list[pd.DataFrame] = []
    if kind == "bp_wide":
        w = _extract_bp_wide(df)
        if not w.empty:
            frames.append(w)
        else:
            skipped += 1
    elif kind == "bp_long":
        frames.extend(_extract_long(df))
        if not frames:
            skipped += 1
    elif kind == "bp_sys_only":
        f = _extract_single_metric(df, "Systolic")
        if not f.empty:
            frames.append(f)
        else:
            skipped += 1
    elif kind == "bp_dia_only":
        f = _extract_single_metric(df, "Diastolic")
        if not f.empty:
            frames.append(f)
        else:
            skipped += 1
    elif kind == "heart":
        f = _extract_single_metric(df, "HeartRate")
        if not f.empty:
            frames.append(f)
        else:
            skipped += 1
    elif kind == "energy":
        f = _extract_single_metric(df, "DietaryEnergy")
        if not f.empty:
            frames.append(f)
        else:
            skipped += 1
    elif kind == "sleep":
        f = _extract_single_metric(df, "SleepHours")
        if not f.empty:
            frames.append(f)
        else:
            skipped += 1
    elif kind == "steps":
        f = _extract_single_metric(df, "Steps")
        if not f.empty:
            frames.append(f)
        else:
            skipped += 1
    return frames, skipped


def _aggregate_metric(frames: list[pd.DataFrame], col: str, how: str) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=["Date", col])
    cat = pd.concat(frames, ignore_index=True)
    if col not in cat.columns:
        return pd.DataFrame(columns=["Date", col])
    cat = cat.dropna(subset=["Date", col])
    if cat.empty:
        return pd.DataFrame(columns=["Date", col])
    g = cat.groupby("Date", as_index=False)[col].agg(how)
    return g


def _merge_daily(parts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    out: pd.DataFrame | None = None
    for col in NUMERIC_COLUMNS:
        df = parts.get(col)
        if df is None or df.empty:
            continue
        if out is None:
            out = df.copy()
        else:
            out = pd.merge(out, df, on="Date", how="outer")
    if out is None:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    for c in NUMERIC_COLUMNS:
        if c not in out.columns:
            out[c] = pd.NA
    out = out[REQUIRED_COLUMNS].sort_values("Date").reset_index(drop=True)
    return out


def load_health_zip(uploaded_file: Any) -> LoadResult:
    if uploaded_file is None:
        return LoadResult(df=None)

    try:
        raw_bytes = uploaded_file.getvalue()
    except Exception:
        return LoadResult(df=None, error=ZIP_LOAD_ERROR)

    bio = io.BytesIO(raw_bytes)
    if not zipfile.is_zipfile(bio):
        return LoadResult(df=None, error=ZIP_LOAD_ERROR)

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile:
        return LoadResult(df=None, error=ZIP_LOAD_ERROR)

    all_frames: list[pd.DataFrame] = []
    skip_files = 0
    with zf:
        xml_path = _find_apple_export_xml(zf)
        if xml_path:
            try:
                all_frames.extend(_frames_from_apple_export_xml(zf, xml_path))
            except Exception:
                pass
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if _should_skip_zip_path(name) or not _is_csv_entry(name):
                continue
            if info.file_size == 0:
                continue
            try:
                data = zf.read(info)
            except Exception:
                skip_files += 1
                continue
            frames, sk = _process_csv_bytes(name, data)
            skip_files += sk
            all_frames.extend(frames)

    if not all_frames:
        w = f"読み取れた CSV が {skip_files} 件スキップされました。" if skip_files else None
        return LoadResult(df=None, error=ZIP_LOAD_ERROR, warning=w)

    systolic_f: list[pd.DataFrame] = []
    diastolic_f: list[pd.DataFrame] = []
    heart_f: list[pd.DataFrame] = []
    energy_f: list[pd.DataFrame] = []
    sleep_f: list[pd.DataFrame] = []
    steps_f: list[pd.DataFrame] = []

    for fr in all_frames:
        cols = set(fr.columns)
        if "Systolic" in cols:
            systolic_f.append(fr[["Date", "Systolic"]])
        if "Diastolic" in cols:
            diastolic_f.append(fr[["Date", "Diastolic"]])
        if "HeartRate" in cols:
            heart_f.append(fr[["Date", "HeartRate"]])
        if "DietaryEnergy" in cols:
            energy_f.append(fr[["Date", "DietaryEnergy"]])
        if "SleepHours" in cols:
            sleep_f.append(fr[["Date", "SleepHours"]])
        if "Steps" in cols:
            steps_f.append(fr[["Date", "Steps"]])

    parts: dict[str, pd.DataFrame] = {
        "Systolic": _aggregate_metric(systolic_f, "Systolic", "mean"),
        "Diastolic": _aggregate_metric(diastolic_f, "Diastolic", "mean"),
        "HeartRate": _aggregate_metric(heart_f, "HeartRate", "mean"),
        "DietaryEnergy": _aggregate_metric(energy_f, "DietaryEnergy", "sum"),
        "SleepHours": _aggregate_metric(sleep_f, "SleepHours", "sum"),
        "Steps": _aggregate_metric(steps_f, "Steps", "sum"),
    }

    merged = _merge_daily(parts)
    if merged.empty or merged["Date"].isna().all():
        return LoadResult(df=None, error=ZIP_LOAD_ERROR)

    for col in NUMERIC_COLUMNS:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    if getattr(merged["Date"].dtype, "tz", None) is not None:
        merged["Date"] = pd.to_datetime(merged["Date"].dt.strftime("%Y-%m-%d"))

    warn = None
    if skip_files:
        warn = f"解釈できなかった CSV ファイルを {skip_files} 件スキップしました。"

    return LoadResult(df=merged, warning=warn)


def filter_by_date_range(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    if df.empty:
        return df
    d = df["Date"].dt.date
    return df[(d >= start) & (d <= end)].copy()


def compute_kpis(df: pd.DataFrame) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    if df.empty:
        for key in (
            "avg_systolic",
            "avg_diastolic",
            "avg_heartrate",
            "avg_calories",
            "avg_sleep",
            "avg_steps",
        ):
            out[key] = None
        return out

    def mean_col(name: str) -> float | None:
        s = df[name].dropna()
        if s.empty:
            return None
        return float(s.mean())

    out["avg_systolic"] = mean_col("Systolic")
    out["avg_diastolic"] = mean_col("Diastolic")
    out["avg_heartrate"] = mean_col("HeartRate")
    out["avg_calories"] = mean_col("DietaryEnergy")
    out["avg_sleep"] = mean_col("SleepHours")
    out["avg_steps"] = mean_col("Steps")
    return out


def build_stats_for_ai(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "row_count": 0,
            "date_range": None,
            "columns": {},
        }

    start = df["Date"].min()
    end = df["Date"].max()
    cols: dict[str, dict[str, float | int]] = {}
    for c in NUMERIC_COLUMNS:
        s = df[c].dropna()
        cols[c] = {
            "count_non_null": int(s.shape[0]),
            "mean": float(s.mean()) if not s.empty else 0.0,
            "std": float(s.std()) if len(s) > 1 else 0.0,
            "min": float(s.min()) if not s.empty else 0.0,
            "max": float(s.max()) if not s.empty else 0.0,
        }

    return {
        "row_count": int(len(df)),
        "date_range": {
            "start": start.isoformat() if pd.notna(start) else None,
            "end": end.isoformat() if pd.notna(end) else None,
        },
        "columns": cols,
    }
