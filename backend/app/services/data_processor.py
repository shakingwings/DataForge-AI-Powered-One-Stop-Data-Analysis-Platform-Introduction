from __future__ import annotations
import io
from pathlib import Path

import chardet
import numpy as np
import pandas as pd


def _fix_encoding(encoding: str) -> str:
    """Use utf-8-sig to auto-strip BOM when encoding is UTF-8."""
    enc = (encoding or "utf-8").lower().replace("-", "")
    if enc in ("utf8", "utf8sig", "ascii"):
        return "utf-8-sig"
    return encoding or "utf-8"


def load_data(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".csv", ".txt"):
        with open(path, "rb") as f:
            raw = f.read(10000)
        detected = chardet.detect(raw)
        encoding = _fix_encoding(detected.get("encoding", "utf-8"))
        df = pd.read_csv(path, encoding=encoding)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path, engine="openpyxl" if suffix == ".xlsx" else "xlrd")
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")

    df = _infer_dtypes(df)
    return df


def load_from_bytes(content: bytes, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix in (".csv", ".txt"):
        detected = chardet.detect(content[:10000])
        encoding = _fix_encoding(detected.get("encoding", "utf-8"))
        df = pd.read_csv(io.BytesIO(content), encoding=encoding)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")
    return _infer_dtypes(df)


def _infer_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_datetime(df[col])
            except (ValueError, TypeError):
                pass
    return df


def load_from_file(file_path: str | Path) -> pd.DataFrame:
    return load_data(file_path)


def get_data_info(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing": df.isnull().sum().to_dict(),
        "duplicates": int(df.duplicated().sum()),
        "preview": df.head(5).to_dict(orient="records"),
    }


def get_page(df: pd.DataFrame, page: int = 1, page_size: int = 50) -> dict:
    total = len(df)
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    page_data = df.iloc[start:end].to_dict(orient="records")
    return {
        "data": page_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def fill_missing(df: pd.DataFrame, columns: list[str] | None = None, method: str = "mean") -> pd.DataFrame:
    df = df.copy()
    cols = columns or [c for c in df.columns if df[c].isnull().any()]
    for col in cols:
        if col not in df.columns:
            continue
        if df[col].dtype in ("float64", "int64", "float32", "int32"):
            if method == "mean":
                df[col] = df[col].fillna(df[col].mean())
            elif method == "median":
                df[col] = df[col].fillna(df[col].median())
            elif method == "drop":
                df = df.dropna(subset=[col])
        else:
            if method == "drop":
                df = df.dropna(subset=[col])
            else:
                df[col] = df[col].fillna(df[col].mode().iloc[0] if not df[col].mode().empty else "未知")
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates()
    return df


def remove_outliers(df: pd.DataFrame, columns: list[str] | None = None, method: str = "iqr") -> pd.DataFrame:
    df = df.copy()
    numeric_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_cols:
        if col not in df.columns:
            continue
        if method == "iqr":
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            df = df[(df[col] >= lower) & (df[col] <= upper)]
        elif method == "zscore":
            mean, std = df[col].mean(), df[col].std()
            if std > 0:
                z = (df[col] - mean).abs() / std
                df = df[z <= 3]
    return df


def auto_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    steps = []
    df = drop_duplicates(df)
    steps.append("去除重复值")
    df = fill_missing(df, method="mean")
    steps.append("填充缺失值（数值列用均值，文本列用众数）")
    return df, steps


def trim_whitespace(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    df = df.copy()
    cols = columns or df.select_dtypes(include=["object"]).columns.tolist()
    for col in cols:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
    return df


def standardize_case(df: pd.DataFrame, columns: list[str] | None = None, case: str = "lower") -> pd.DataFrame:
    df = df.copy()
    cols = columns or df.select_dtypes(include=["object"]).columns.tolist()
    for col in cols:
        if col in df.columns and df[col].dtype == object:
            if case == "lower":
                df[col] = df[col].astype(str).str.lower()
            elif case == "upper":
                df[col] = df[col].astype(str).str.upper()
            elif case == "title":
                df[col] = df[col].astype(str).str.title()
    return df


def rename_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    return df.rename(columns=mapping)


def drop_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return df.drop(columns=[c for c in columns if c in df.columns])


def fill_missing_value(df: pd.DataFrame, columns: list[str], value: str = "") -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col in df.columns:
            if df[col].dtype in ("float64", "int64", "float32", "int32"):
                try:
                    df[col] = df[col].fillna(float(value))
                except (ValueError, TypeError):
                    df[col] = df[col].fillna(value)
            else:
                df[col] = df[col].fillna(value)
    return df


def fill_forward(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    df = df.copy()
    cols = columns or [c for c in df.columns if df[c].isnull().any()]
    df[cols] = df[cols].ffill()
    return df


def fill_backward(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    df = df.copy()
    cols = columns or [c for c in df.columns if df[c].isnull().any()]
    df[cols] = df[cols].bfill()
    return df


def drop_rows_by_condition(df: pd.DataFrame, column: str, operator: str, value: str) -> pd.DataFrame:
    df = df.copy()
    if column not in df.columns:
        return df
    try:
        num_val = float(value)
        col = pd.to_numeric(df[column], errors="coerce")
    except (ValueError, TypeError):
        col = df[column]
        num_val = value

    if operator == "==":
        return df[col == num_val]
    elif operator == "!=":
        return df[col != num_val]
    elif operator == ">":
        return df[col > num_val]
    elif operator == ">=":
        return df[col >= num_val]
    elif operator == "<":
        return df[col < num_val]
    elif operator == "<=":
        return df[col <= num_val]
    elif operator == "contains":
        return df[df[column].astype(str).str.contains(str(value), na=False)]
    elif operator == "not_contains":
        return df[~df[column].astype(str).str.contains(str(value), na=False)]
    return df


def convert_dtype(df: pd.DataFrame, column: str, target_type: str) -> pd.DataFrame:
    df = df.copy()
    if column not in df.columns:
        return df
    try:
        if target_type == "int":
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
        elif target_type == "float":
            df[column] = pd.to_numeric(df[column], errors="coerce")
        elif target_type == "str":
            df[column] = df[column].astype(str)
        elif target_type == "datetime":
            df[column] = pd.to_datetime(df[column], errors="coerce")
    except Exception:
        pass
    return df


def deduplicate_subset(df: pd.DataFrame, columns: list[str], keep: str = "first") -> pd.DataFrame:
    return df.drop_duplicates(subset=columns if columns else None, keep=keep)


def truncate_datetime(df: pd.DataFrame, columns: list[str] | None = None, fmt: str = "%Y-%m") -> pd.DataFrame:
    df = df.copy()
    cols = columns or df.select_dtypes(include=["datetime64"]).columns.tolist()
    for col in cols:
        if col in df.columns:
            df[col] = df[col].dt.strftime(fmt)
    return df
