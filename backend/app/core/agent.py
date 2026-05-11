from __future__ import annotations
import json
from typing import Any

import pandas as pd

from app.core.llm_client import get_llm_client
from app.core.prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS
from app.models.schemas import session_store
from app.services import data_processor, analyzer, visualizer, summarizer


async def process_message(message: str, session_id: str = "default") -> dict:
    session = session_store.get(session_id)
    df = session.get("df")
    if df is None:
        return {"reply": "请先上传数据文件再进行分析", "charts": [], "tables": [], "analysis": {}}
    llm = get_llm_client()

    data_context = ""
    info = data_processor.get_data_info(df)
    preview = info.get("preview", [])[:5]
    data_context = (
        f"\n当前数据信息：\n"
        f"- 文件名: {session.get('filename', '未知')}\n"
        f"- 行数: {info.get('rows', 0)}, 列数: {info.get('columns', 0)}\n"
        f"- 列名及类型: {json.dumps(info.get('dtypes', {}), ensure_ascii=False)}\n"
        f"- 前5行预览: {json.dumps(preview, ensure_ascii=False, default=str)}"
    )

    history = session.get("history", [])
    messages = [{"role": "system", "content": SYSTEM_PROMPT + data_context}]
    for h in history[-10:]:
        messages.append(h)
    messages.append({"role": "user", "content": message})

    result = await llm.chat(messages, tools=TOOL_DEFINITIONS if df is not None else None)
    session["history"].append({"role": "user", "content": message})

    tool_results = []
    charts = []
    tables = []
    analysis_data = {}

    if result.get("tool_calls"):
        for tc in result["tool_calls"]:
            tool_name = tc["function"]
            args = tc["arguments"]
            tool_output = await _execute_tool(tool_name, args, df)

            if "charts" in tool_output:
                charts.extend(tool_output["charts"])
            if "tables" in tool_output:
                tables.extend(tool_output["tables"])
            if "analysis" in tool_output:
                analysis_data.update(tool_output["analysis"])
            tool_results.append({"tool": tool_name, "output": tool_output})

        summary_msg = [
            {"role": "system", "content": SYSTEM_PROMPT + data_context},
            {"role": "user", "content": message},
            {"role": "assistant", "content": result["content"] or ""},
            {"role": "user", "content": f"工具执行结果：{json.dumps(tool_results, ensure_ascii=False, default=str)}\n\n请用简洁的中文总结分析结果，列出核心发现和建议。"},
        ]
        summary = await llm.chat(summary_msg)
        reply = summary.get("content", "分析完成")
    else:
        reply = result.get("content", "")

    session["history"].append({"role": "assistant", "content": reply})
    session["charts"] = charts
    session["analysis"] = analysis_data

    return {"reply": reply, "charts": charts, "tables": tables, "analysis": analysis_data}


async def process_message_stream(message: str, session_id: str = "default"):
    session = session_store.get(session_id)
    df = session.get("df")
    if df is None:
        yield {"type": "text", "content": "请先上传数据文件再进行分析"}
        yield {"type": "done", "content": ""}
        return
    llm = get_llm_client()

    data_context = ""
    info = data_processor.get_data_info(df)
    preview = info.get("preview", [])[:5]
    data_context = (
        f"\n当前数据信息：\n"
        f"- 文件名: {session.get('filename', '未知')}\n"
        f"- 行数: {info.get('rows', 0)}, 列数: {info.get('columns', 0)}\n"
        f"- 列名及类型: {json.dumps(info.get('dtypes', {}), ensure_ascii=False)}\n"
        f"- 前5行预览: {json.dumps(preview, ensure_ascii=False, default=str)}"
    )

    history = session.get("history", [])
    messages = [{"role": "system", "content": SYSTEM_PROMPT + data_context}]
    for h in history[-10:]:
        messages.append(h)
    messages.append({"role": "user", "content": message})

    session["history"].append({"role": "user", "content": message})

    result = await llm.chat(messages, tools=TOOL_DEFINITIONS if df is not None else None)

    charts = []
    tables = []
    analysis_data = {}

    if result.get("tool_calls"):
        yield {"type": "status", "content": "正在执行分析工具..."}
        tool_results = []
        for tc in result["tool_calls"]:
            tool_name = tc["function"]
            args = tc["arguments"]
            yield {"type": "status", "content": f"执行: {tool_name}"}
            tool_output = await _execute_tool(tool_name, args, df)
            if "charts" in tool_output:
                charts.extend(tool_output["charts"])
            if "tables" in tool_output:
                tables.extend(tool_output["tables"])
            if "analysis" in tool_output:
                analysis_data.update(tool_output["analysis"])
            tool_results.append({"tool": tool_name, "output": tool_output})

        summary_msg = [
            {"role": "system", "content": SYSTEM_PROMPT + data_context},
            {"role": "user", "content": message},
            {"role": "assistant", "content": result["content"] or ""},
            {"role": "user", "content": f"工具执行结果：{json.dumps(tool_results, ensure_ascii=False, default=str)}\n\n请用简洁的中文总结分析结果，列出核心发现和建议。"},
        ]
        async for chunk in llm.chat_stream(summary_msg):
            yield {"type": "text", "content": chunk}
        reply = ""
    else:
        async for chunk in llm.chat_stream(messages):
            yield {"type": "text", "content": chunk}
        reply = result.get("content", "")

    if charts:
        yield {"type": "charts", "content": charts}
    if tables:
        yield {"type": "tables", "content": tables}
    if analysis_data:
        yield {"type": "analysis", "content": analysis_data}

    session["history"].append({"role": "assistant", "content": reply or "(分析完成)"})
    session["charts"] = charts
    session["analysis"] = analysis_data
    yield {"type": "done", "content": ""}


async def _execute_tool(tool_name: str, args: dict, df: pd.DataFrame) -> dict:
    if df is None:
        return {"error": "请先上传数据文件"}

    if tool_name == "analyze_data":
        return _run_analysis(args, df)
    elif tool_name == "generate_chart":
        return _run_chart(args, df)
    elif tool_name == "summarize":
        return await _run_summary(args, df)
    elif tool_name == "preprocess_data":
        return _run_preprocess(args, df)
    return {"error": f"未知工具: {tool_name}"}


def _run_analysis(args: dict, df: pd.DataFrame) -> dict:
    analysis_type = args.get("analysis_type", "basic_stats")
    columns = args.get("columns", [])
    group_by = args.get("group_by", "")

    result: dict[str, Any] = {"analysis": {}, "charts": [], "tables": []}

    if analysis_type == "basic_stats":
        stats = analyzer.basic_stats(df, columns or None)
        result["analysis"]["basic_stats"] = stats
        result["tables"].append({"type": "stats", "data": stats})

    elif analysis_type == "trend":
        time_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if time_cols and numeric_cols:
            trend = analyzer.trend_analysis(df, time_cols[0], columns[0] if columns else numeric_cols[0])
            result["analysis"]["trend"] = trend
            result["charts"].append(visualizer.generate_line_chart(
                pd.DataFrame(trend["data"]), "date", "value", title="趋势分析"
            ))

    elif analysis_type == "compare":
        categorical = df.select_dtypes(include=["object", "category"]).columns.tolist()
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        gc = group_by or (categorical[0] if categorical else "")
        vc = columns[0] if columns else (numeric_cols[0] if numeric_cols else "")
        if gc and vc:
            comp = analyzer.compare_analysis(df, gc, vc)
            result["analysis"]["compare"] = comp
            comp_df = pd.DataFrame(comp["groups"])
            result["charts"].append(visualizer.generate_bar_chart(comp_df, "group", "sum", title="对比分析"))
            result["charts"].append(visualizer.generate_pie_chart(comp_df, "group", "sum", title="占比分析"))

    elif analysis_type == "correlation":
        corr = analyzer.correlation_analysis(df, columns or None)
        result["analysis"]["correlation"] = corr
        if corr.get("matrix"):
            result["charts"].append(visualizer.generate_heatmap(corr["matrix"]))

    elif analysis_type == "anomaly":
        anomalies = analyzer.anomaly_detection(df, columns or None)
        result["analysis"]["anomaly"] = anomalies

    elif analysis_type == "distribution":
        numeric_cols = columns or df.select_dtypes(include=["number"]).columns.tolist()
        for col in numeric_cols[:3]:
            dist = analyzer.distribution_analysis(df, col)
            result["analysis"][f"distribution_{col}"] = dist

    return result


def _run_chart(args: dict, df: pd.DataFrame) -> dict:
    chart_type = args.get("chart_type", "auto")
    x_col = args.get("x_column", "")
    y_col = args.get("y_column", "")
    group_by = args.get("group_by", "")
    title = args.get("title", "")

    if chart_type == "auto":
        chart_type = visualizer.recommend_chart_type(df, x_col, y_col)

    if not x_col:
        cols = df.columns.tolist()
        x_col = cols[0] if cols else ""
    if not y_col:
        numeric = df.select_dtypes(include=["number"]).columns.tolist()
        y_col = numeric[0] if numeric else (df.columns[1] if len(df.columns) > 1 else "")

    gen = visualizer.CHART_GENERATORS.get(chart_type)
    if gen:
        chart = gen(df, x=x_col, y=y_col, title=title, color=group_by)
        return {"charts": [chart]}
    return {"error": f"不支持的图表类型: {chart_type}"}


async def _run_summary(args: dict, df: pd.DataFrame) -> dict:
    focus = args.get("focus", "")
    info = data_processor.get_data_info(df)
    basic = summarizer.generate_basic_summary(df)
    try:
        llm_summary = await summarizer.summarize_with_llm(basic, info, focus)
        return {"analysis": {"summary": llm_summary.get("summary", basic["summary"]), "metrics": basic["metrics"]}}
    except Exception:
        return {"analysis": {"summary": basic["summary"], "metrics": basic["metrics"]}}


def _run_preprocess(args: dict, df: pd.DataFrame) -> dict:
    operation = args.get("operation", "auto_clean")
    columns = args.get("columns")
    method = args.get("method", "mean")
    session = session_store.get("default")

    if operation == "fill_missing":
        df_new = data_processor.fill_missing(df, columns, method)
        session["df"] = df_new
        return {"analysis": {"preprocess": "缺失值填充完成"}, "tables": [{"type": "preview", "data": df_new.head(10).to_dict(orient="records")}]}
    elif operation == "fill_forward":
        df_new = data_processor.fill_forward(df, columns)
        session["df"] = df_new
        return {"analysis": {"preprocess": "前向填充完成"}}
    elif operation == "fill_backward":
        df_new = data_processor.fill_backward(df, columns)
        session["df"] = df_new
        return {"analysis": {"preprocess": "后向填充完成"}}
    elif operation == "fill_value":
        df_new = data_processor.fill_missing_value(df, columns or [], args.get("value", ""))
        session["df"] = df_new
        return {"analysis": {"preprocess": f"已用指定值填充缺失值"}}
    elif operation == "drop_duplicates":
        before = len(df)
        df_new = data_processor.drop_duplicates(df)
        session["df"] = df_new
        return {"analysis": {"preprocess": f"去除了 {before - len(df_new)} 条重复记录"}}
    elif operation == "deduplicate_subset":
        before = len(df)
        df_new = data_processor.deduplicate_subset(df, columns or [], args.get("keep", "first"))
        session["df"] = df_new
        return {"analysis": {"preprocess": f"按列去重，移除 {before - len(df_new)} 条记录"}}
    elif operation == "remove_outliers":
        df_new = data_processor.remove_outliers(df, columns, method)
        removed = len(df) - len(df_new)
        session["df"] = df_new
        return {"analysis": {"preprocess": f"去除了 {removed} 条异常记录"}}
    elif operation == "trim_whitespace":
        df_new = data_processor.trim_whitespace(df, columns)
        session["df"] = df_new
        return {"analysis": {"preprocess": "去除首尾空白完成"}}
    elif operation == "standardize_case":
        df_new = data_processor.standardize_case(df, columns, method)
        session["df"] = df_new
        return {"analysis": {"preprocess": f"大小写标准化完成（{method}）"}}
    elif operation == "convert_dtype":
        col = args.get("column", "")
        df_new = data_processor.convert_dtype(df, col, args.get("target_type", "str"))
        session["df"] = df_new
        return {"analysis": {"preprocess": f"列 '{col}' 已转换为 {args.get('target_type', 'str')} 类型"}}
    elif operation == "rename_columns":
        mapping = args.get("mapping", {})
        df_new = data_processor.rename_columns(df, mapping)
        session["df"] = df_new
        return {"analysis": {"preprocess": f"列重命名完成: {mapping}"}}
    elif operation == "drop_columns":
        cols = args.get("columns", [])
        df_new = data_processor.drop_columns(df, cols)
        session["df"] = df_new
        return {"analysis": {"preprocess": f"已删除 {len(cols)} 列"}}
    elif operation == "drop_rows":
        before = len(df)
        df_new = data_processor.drop_rows_by_condition(
            df, args.get("column", ""), args.get("operator", "=="), args.get("value", ""))
        session["df"] = df_new
        return {"analysis": {"preprocess": f"条件筛选完成，移除 {before - len(df_new)} 行"}}
    elif operation == "truncate_datetime":
        fmt = args.get("fmt", "%Y-%m")
        df_new = data_processor.truncate_datetime(df, columns, fmt)
        session["df"] = df_new
        return {"analysis": {"preprocess": f"时间列已截断为 {fmt} 格式"}}
    elif operation == "auto_clean":
        df_new, steps = data_processor.auto_clean(df)
        session["df"] = df_new
        return {"analysis": {"preprocess": "自动清洗完成", "steps": steps}}
    return {"error": f"未知操作: {operation}"}
