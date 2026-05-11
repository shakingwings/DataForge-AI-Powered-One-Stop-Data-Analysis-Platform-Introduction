from __future__ import annotations
import numpy as np
import pandas as pd


def basic_stats(df: pd.DataFrame, columns: list[str] | None = None) -> dict:
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
    result = {}
    for col in cols:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        if not np.issubdtype(s.dtype, np.number):
            continue
        result[col] = {
            "count": int(s.count()),
            "mean": round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "std": round(float(s.std()), 4),
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
            "q25": round(float(s.quantile(0.25)), 4),
            "q75": round(float(s.quantile(0.75)), 4),
            "sum": round(float(s.sum()), 4),
        }
    return result


def trend_analysis(df: pd.DataFrame, time_col: str, value_col: str) -> dict:
    df = df.sort_values(time_col).copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df["ma_3"] = df[value_col].rolling(window=3, min_periods=1).mean()
    df["ma_5"] = df[value_col].rolling(window=5, min_periods=1).mean()
    df["pct_change"] = df[value_col].pct_change() * 100

    trend_data = []
    for _, row in df.iterrows():
        entry = {
            "date": str(row[time_col]),
            "value": round(float(row[value_col]), 4) if pd.notna(row[value_col]) else None,
            "ma_3": round(float(row["ma_3"]), 4) if pd.notna(row["ma_3"]) else None,
            "ma_5": round(float(row["ma_5"]), 4) if pd.notna(row["ma_5"]) else None,
            "pct_change": round(float(row["pct_change"]), 2) if pd.notna(row["pct_change"]) else None,
        }
        trend_data.append(entry)

    values = df[value_col].dropna()
    overall_growth = float((values.iloc[-1] - values.iloc[0]) / values.iloc[0] * 100) if len(values) >= 2 and values.iloc[0] != 0 else 0

    return {
        "data": trend_data,
        "overall_growth": round(overall_growth, 2),
        "avg_value": round(float(values.mean()), 4),
        "max_value": round(float(values.max()), 4),
        "min_value": round(float(values.min()), 4),
    }


def compare_analysis(df: pd.DataFrame, group_col: str, value_col: str) -> dict:
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    grouped = df.groupby(group_col)[value_col].agg(["sum", "mean", "count"]).reset_index()
    total = grouped["sum"].sum()
    grouped["percentage"] = (grouped["sum"] / total * 100).round(2) if total != 0 else 0

    result = []
    for _, row in grouped.iterrows():
        result.append({
            "group": str(row[group_col]),
            "sum": round(float(row["sum"]), 4),
            "mean": round(float(row["mean"]), 4),
            "count": int(row["count"]),
            "percentage": round(float(row["percentage"]), 2),
        })

    result.sort(key=lambda x: x["sum"], reverse=True)
    return {"groups": result, "total": round(float(total), 4)}


def correlation_analysis(df: pd.DataFrame, columns: list[str] | None = None) -> dict:
    numeric_df = df.select_dtypes(include=[np.number])
    if columns:
        cols = [c for c in columns if c in numeric_df.columns]
        numeric_df = numeric_df[cols]
    if numeric_df.shape[1] < 2:
        return {"matrix": {}, "top_correlations": []}

    corr = numeric_df.corr().round(4)
    matrix = {}
    for col in corr.columns:
        matrix[col] = {row: float(corr.loc[row, col]) for row in corr.index}

    top_corr = []
    seen = set()
    for i, col1 in enumerate(corr.columns):
        for j, col2 in enumerate(corr.columns):
            if i < j:
                pair = tuple(sorted([col1, col2]))
                if pair not in seen:
                    seen.add(pair)
                    val = float(corr.loc[col1, col2])
                    if abs(val) > 0.1:
                        top_corr.append({"col1": col1, "col2": col2, "correlation": round(val, 4)})
    top_corr.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return {"matrix": matrix, "top_correlations": top_corr[:20]}


def anomaly_detection(df: pd.DataFrame, columns: list[str] | None = None) -> dict:
    numeric_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
    anomalies = {}
    for col in numeric_cols:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        if not np.issubdtype(s.dtype, np.number) or len(s) < 4:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outlier_mask = (s < lower) | (s > upper)
        if outlier_mask.any():
            outlier_indices = s[outlier_mask].index.tolist()
            anomaly_records = []
            for idx in outlier_indices[:20]:
                anomaly_records.append({
                    "index": int(idx),
                    "value": round(float(s[idx]), 4),
                    "lower_bound": round(float(lower), 4),
                    "upper_bound": round(float(upper), 4),
                })
            anomalies[col] = {
                "count": int(outlier_mask.sum()),
                "lower_bound": round(float(lower), 4),
                "upper_bound": round(float(upper), 4),
                "anomalies": anomaly_records,
            }
    return anomalies


def distribution_analysis(df: pd.DataFrame, column: str) -> dict:
    s = df[column].dropna()
    if not np.issubdtype(s.dtype, np.number):
        return {"error": f"列 {column} 不是数值类型"}
    hist, bin_edges = np.histogram(s, bins=10)
    return {
        "column": column,
        "histogram": {
            "counts": [int(h) for h in hist],
            "bins": [round(float(b), 4) for b in bin_edges],
        },
        "skewness": round(float(s.skew()), 4),
        "kurtosis": round(float(s.kurtosis()), 4),
    }


def generate_yoy_mom(df: pd.DataFrame, time_col: str, value_col: str) -> dict:
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col])
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.sort_values(time_col)

    df["year"] = df[time_col].dt.year
    df["month"] = df[time_col].dt.month
    monthly = df.groupby(["year", "month"])[value_col].sum().reset_index()
    monthly = monthly.sort_values(["year", "month"])

    result = []
    for i, row in monthly.iterrows():
        prev_idx = i - 1
        prev_year_idx = None
        for j, r in monthly.iterrows():
            if r["year"] == row["year"] - 1 and r["month"] == row["month"]:
                prev_year_idx = j
                break

        mom = None
        yoy = None
        if prev_idx in monthly.index:
            prev_val = monthly.loc[prev_idx, value_col]
            if prev_val != 0:
                mom = round((row[value_col] - prev_val) / prev_val * 100, 2)
        if prev_year_idx is not None:
            prev_val = monthly.loc[prev_year_idx, value_col]
            if prev_val != 0:
                yoy = round((row[value_col] - prev_val) / prev_val * 100, 2)

        result.append({
            "period": f"{int(row['year'])}-{int(row['month']):02d}",
            "value": round(float(row[value_col]), 4),
            "mom": mom,
            "yoy": yoy,
        })
    return result
