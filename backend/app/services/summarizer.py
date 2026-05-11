from __future__ import annotations
import json

import pandas as pd

from app.core.llm_client import get_llm_client
from app.core.prompts import TOOL_RESULT_PROMPT


async def summarize_with_llm(analysis_result: dict, data_info: dict, focus: str = "") -> dict:
    llm = get_llm_client()
    prompt = TOOL_RESULT_PROMPT.format(
        tool_name="数据分析",
        result=json.dumps(analysis_result, ensure_ascii=False, default=str),
    )
    messages = [
        {"role": "system", "content": "你是一个专业的数据分析师，擅长用简洁直白的中文总结数据洞察。"},
        {"role": "user", "content": f"数据基本信息：{json.dumps(data_info, ensure_ascii=False, default=str)}\n\n{prompt}"},
    ]
    if focus:
        messages.append({"role": "user", "content": f"请特别关注：{focus}"})

    result = await llm.chat(messages)
    return {"summary": result.get("content", "")}


def generate_basic_summary(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    summary_lines = []
    metrics = {}

    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        avg = s.mean()
        total = s.sum()
        max_val = s.max()
        min_val = s.min()
        metrics[col] = {"avg": round(avg, 2), "total": round(total, 2), "max": round(max_val, 2), "min": round(min_val, 2)}
        summary_lines.append(f"【{col}】均值 {avg:,.2f}，总计 {total:,.2f}，最大 {max_val:,.2f}，最小 {min_val:,.2f}")

    missing_info = df.isnull().sum()
    missing_cols = missing_info[missing_info > 0]
    if len(missing_cols) > 0:
        summary_lines.append(f"数据存在缺失值，涉及列：{', '.join(missing_cols.index.tolist())}")

    dup_count = df.duplicated().sum()
    if dup_count > 0:
        summary_lines.append(f"数据存在 {dup_count} 条重复记录")

    return {
        "summary": "\n".join(summary_lines) if summary_lines else "暂无数值型数据可分析",
        "metrics": metrics,
    }
