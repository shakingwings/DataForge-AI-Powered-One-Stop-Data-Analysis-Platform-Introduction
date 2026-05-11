import json
import re

from fastapi import APIRouter

from app.core.llm_client import get_llm_client
from app.core.logger import get_logger
from app.models.schemas import session_store
from app.services.data_processor import (
    fill_missing, drop_duplicates, remove_outliers, auto_clean,
    trim_whitespace, standardize_case, rename_columns, drop_columns,
    fill_missing_value, fill_forward, fill_backward,
    drop_rows_by_condition, convert_dtype, deduplicate_subset,
    truncate_datetime, get_data_info, get_page,
)

logger = get_logger("api.cleaning")
router = APIRouter(prefix="/api/cleaning", tags=["cleaning"])


def _extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to find JSON in code blocks first
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return None


def _get_df(session_id: str):
    session = session_store.get(session_id)
    df = session.get("df")
    if df is None:
        return None, None, {"error": "请先上传数据"}
    return session, df, None


def _result(session: dict, df, message: str):
    session["df"] = df
    info = get_data_info(df)
    preview = get_page(df, page=1, page_size=50)
    return {"message": message, "info": info, "preview": preview["data"]}


@router.post("/auto")
async def clean_auto(session_id: str = "default"):
    session, df, err = _get_df(session_id)
    if err:
        return err
    logger.info(f"自动清洗 (session={session_id})")
    df, steps = auto_clean(df)
    return _result(session, df, "自动清洗完成: " + "；".join(steps))


@router.post("/fill-missing")
async def clean_fill_missing(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns")
    method = body.get("method", "mean")
    logger.info(f"填充缺失值 method={method} (session={session_id})")
    df = fill_missing(df, columns=columns, method=method)
    return _result(session, df, f"缺失值填充完成（方法: {method}）")


@router.post("/fill-value")
async def clean_fill_value(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns", [])
    value = body.get("value", "")
    logger.info(f"指定值填充 columns={columns} (session={session_id})")
    df = fill_missing_value(df, columns=columns, value=value)
    return _result(session, df, f"已用指定值 '{value}' 填充缺失值")


@router.post("/fill-forward")
async def clean_fill_forward(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns")
    logger.info(f"前向填充 (session={session_id})")
    df = fill_forward(df, columns=columns)
    return _result(session, df, "前向填充完成")


@router.post("/fill-backward")
async def clean_fill_backward(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns")
    logger.info(f"后向填充 (session={session_id})")
    df = fill_backward(df, columns=columns)
    return _result(session, df, "后向填充完成")


@router.post("/drop-duplicates")
async def clean_drop_duplicates(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    before = len(df)
    df = drop_duplicates(df)
    removed = before - len(df)
    logger.info(f"去重: 移除 {removed} 行 (session={session_id})")
    return _result(session, df, f"去重完成，移除 {removed} 行重复数据")


@router.post("/deduplicate-subset")
async def clean_deduplicate_subset(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns", [])
    keep = body.get("keep", "first")
    before = len(df)
    df = deduplicate_subset(df, columns=columns, keep=keep)
    removed = before - len(df)
    logger.info(f"子集去重 columns={columns} (session={session_id})")
    return _result(session, df, f"按列去重完成，移除 {removed} 行")


@router.post("/remove-outliers")
async def clean_remove_outliers(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns")
    method = body.get("method", "iqr")
    before = len(df)
    df = remove_outliers(df, columns=columns, method=method)
    removed = before - len(df)
    logger.info(f"异常值处理 method={method} (session={session_id})")
    return _result(session, df, f"异常值处理完成（方法: {method}），移除 {removed} 行")


@router.post("/trim-whitespace")
async def clean_trim(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns")
    logger.info(f"去除空白 (session={session_id})")
    df = trim_whitespace(df, columns=columns)
    return _result(session, df, "去除首尾空白完成")


@router.post("/standardize-case")
async def clean_case(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns")
    case = body.get("case", "lower")
    logger.info(f"大小写标准化 case={case} (session={session_id})")
    df = standardize_case(df, columns=columns, case=case)
    return _result(session, df, f"大小写标准化完成（{case}）")


@router.post("/rename-columns")
async def clean_rename(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    mapping = body.get("mapping", {})
    logger.info(f"重命名列 {mapping} (session={session_id})")
    df = rename_columns(df, mapping=mapping)
    return _result(session, df, f"列重命名完成")


@router.post("/drop-columns")
async def clean_drop_cols(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns", [])
    logger.info(f"删除列 {columns} (session={session_id})")
    df = drop_columns(df, columns=columns)
    return _result(session, df, f"已删除 {len(columns)} 列")


@router.post("/drop-rows")
async def clean_drop_rows(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    column = body.get("column", "")
    operator = body.get("operator", "==")
    value = body.get("value", "")
    before = len(df)
    df = drop_rows_by_condition(df, column=column, operator=operator, value=value)
    removed = before - len(df)
    logger.info(f"条件删除行 {column} {operator} {value} (session={session_id})")
    return _result(session, df, f"条件筛选完成，移除 {removed} 行")


@router.post("/convert-dtype")
async def clean_convert(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    column = body.get("column", "")
    target_type = body.get("target_type", "str")
    logger.info(f"类型转换 {column} -> {target_type} (session={session_id})")
    df = convert_dtype(df, column=column, target_type=target_type)
    return _result(session, df, f"列 '{column}' 已转换为 {target_type} 类型")


@router.post("/truncate-datetime")
async def clean_truncate_datetime(body: dict):
    session_id = body.get("session_id", "default")
    session, df, err = _get_df(session_id)
    if err:
        return err
    columns = body.get("columns")
    fmt = body.get("fmt", "%Y-%m")
    logger.info(f"时间截断 fmt={fmt} (session={session_id})")
    df = truncate_datetime(df, columns=columns, fmt=fmt)
    return _result(session, df, f"时间列已截断为 {fmt} 格式")


# ---------- AI-powered cleaning ----------

def _build_data_context(df) -> str:
    info = get_data_info(df)
    missing_summary = {k: v for k, v in info["missing"].items() if v > 0}
    sample = df.head(5).to_dict(orient="records")
    return (
        f"数据概况:\n"
        f"- 行数: {info['rows']}, 列数: {info['columns']}\n"
        f"- 列名及类型: {json.dumps(info['dtypes'], ensure_ascii=False)}\n"
        f"- 缺失值统计: {json.dumps(missing_summary, ensure_ascii=False)}\n"
        f"- 重复行数: {info['duplicates']}\n"
        f"- 前5行数据: {json.dumps(sample, ensure_ascii=False, default=str)}"
    )


@router.post("/recommend")
async def recommend_cleaning(session_id: str = "default"):
    session, df, err = _get_df(session_id)
    if err:
        return err

    logger.info(f"AI清洗推荐 (session={session_id})")

    data_context = _build_data_context(df)
    prompt = (
        f"你是一个数据清洗专家。根据以下数据信息，推荐最适合的清洗步骤。\n\n"
        f"{data_context}\n\n"
        f"请返回一个 JSON 数组，每个元素代表一个推荐的清洗步骤，格式如下:\n"
        f'{{"steps": [\n'
        f'  {{"action": "fill_missing", "label": "填充缺失值", "reason": "XX列有N个缺失值", '
        f'"params": {{"method": "mean", "columns": ["col1"]}}}},\n'
        f'  {{"action": "drop_duplicates", "label": "去除重复值", "reason": "有N行重复数据", '
        f'"params": {{}}}}\n'
        f']}}\n\n'
        f"可用的 action 包括:\n"
        f"- fill_missing: 填充缺失值 (params: method=mean/median/mode, columns)\n"
        f"- drop_duplicates: 去除重复值\n"
        f"- remove_outliers: 去除异常值 (params: method=iqr/zscore, columns)\n"
        f"- trim_whitespace: 去除首尾空白 (params: columns)\n"
        f"- standardize_case: 大小写标准化 (params: case=lower/upper/title, columns)\n"
        f"- convert_dtype: 类型转换 (params: column, target_type=int/float/str/datetime)\n"
        f"- rename_columns: 列重命名 (params: mapping)\n"
        f"- drop_columns: 删除无用列 (params: columns)\n\n"
        f"只返回 JSON，不要其他文字。只推荐确实有必要的步骤。"
    )

    llm = get_llm_client()
    messages = [{"role": "user", "content": prompt}]
    result = await llm.chat(messages)

    try:
        content = result.get("content", "")
        parsed = _extract_json(content)
        steps = parsed.get("steps", []) if parsed else []
    except Exception as e:
        logger.warning(f"AI推荐解析失败: {e}")
        steps = []

    return {"steps": steps, "data_context": _build_data_context(df)}


@router.post("/execute-steps")
async def execute_steps(body: dict):
    """Execute a list of cleaning steps sequentially."""
    session_id = body.get("session_id", "default")
    steps = body.get("steps", [])
    session, df, err = _get_df(session_id)
    if err:
        return err

    if not steps:
        return {"error": "没有可执行的步骤"}

    results = []
    for step in steps:
        action = step.get("action", "")
        params = step.get("params", {})
        label = step.get("label", action)
        try:
            if action == "fill_missing":
                df = fill_missing(df, columns=params.get("columns"), method=params.get("method", "mean"))
            elif action == "drop_duplicates":
                before = len(df)
                df = drop_duplicates(df)
                results.append(f"{label}: 移除 {before - len(df)} 行")
                continue
            elif action == "remove_outliers":
                before = len(df)
                df = remove_outliers(df, columns=params.get("columns"), method=params.get("method", "iqr"))
                results.append(f"{label}: 移除 {before - len(df)} 行")
                continue
            elif action == "trim_whitespace":
                df = trim_whitespace(df, columns=params.get("columns"))
            elif action == "standardize_case":
                df = standardize_case(df, columns=params.get("columns"), case=params.get("case", "lower"))
            elif action == "convert_dtype":
                df = convert_dtype(df, column=params.get("column", ""), target_type=params.get("target_type", "str"))
            elif action == "rename_columns":
                df = rename_columns(df, mapping=params.get("mapping", {}))
            elif action == "drop_columns":
                df = drop_columns(df, columns=params.get("columns", []))
            else:
                results.append(f"{label}: 未知操作，已跳过")
                continue
            results.append(f"{label}: 完成")
        except Exception as e:
            results.append(f"{label}: 失败 - {str(e)}")

    return _result(session, df, "；".join(results))


@router.post("/ai-clean")
async def ai_clean(body: dict):
    """Accept natural language cleaning instruction, use LLM to convert to steps, then execute."""
    session_id = body.get("session_id", "default")
    instruction = body.get("instruction", "")
    session, df, err = _get_df(session_id)
    if err:
        return err

    if not instruction.strip():
        return {"error": "请输入清洗指令"}

    logger.info(f"AI清洗指令: {instruction} (session={session_id})")

    data_context = _build_data_context(df)
    prompt = (
        f"你是一个数据清洗专家。用户想对数据进行清洗操作。\n\n"
        f"用户指令: {instruction}\n\n"
        f"{data_context}\n\n"
        f"请将用户的自然语言指令转换为清洗步骤的 JSON 数组:\n"
        f'{{"steps": [\n'
        f'  {{"action": "fill_missing", "params": {{"method": "mean", "columns": ["col1"]}}}}\n'
        f'], "explanation": "简要说明将执行的操作"}}\n\n'
        f"可用的 action:\n"
        f"- fill_missing (params: method=mean/median/mode/drop, columns)\n"
        f"- fill_forward (params: columns)\n"
        f"- fill_backward (params: columns)\n"
        f"- drop_duplicates\n"
        f"- deduplicate_subset (params: columns, keep=first/last)\n"
        f"- remove_outliers (params: method=iqr/zscore, columns)\n"
        f"- trim_whitespace (params: columns)\n"
        f"- standardize_case (params: case=lower/upper/title, columns)\n"
        f"- convert_dtype (params: column, target_type=int/float/str/datetime)\n"
        f"- rename_columns (params: mapping)\n"
        f"- drop_columns (params: columns)\n"
        f"- drop_rows (params: column, operator, value)\n"
        f"- fill_value (params: columns, value)\n\n"
        f"只返回 JSON，不要其他文字。"
    )

    llm = get_llm_client()
    llm_result = await llm.chat([{"role": "user", "content": prompt}])

    try:
        content = llm_result.get("content", "")
        parsed = _extract_json(content)
        if not parsed:
            return {"error": "无法理解清洗指令，请尝试更具体的描述"}
        steps = parsed.get("steps", [])
        explanation = parsed.get("explanation", "")
    except Exception as e:
        logger.warning(f"AI清洗指令解析失败: {e}")
        return {"error": f"无法理解清洗指令，请尝试更具体的描述"}

    if not steps:
        return {"error": "未能从指令中识别出有效的清洗操作"}

    # Execute steps
    exec_results = []
    for step in steps:
        action = step.get("action", "")
        params = step.get("params", {})
        try:
            if action == "fill_missing":
                df = fill_missing(df, columns=params.get("columns"), method=params.get("method", "mean"))
            elif action == "fill_forward":
                df = fill_forward(df, columns=params.get("columns"))
            elif action == "fill_backward":
                df = fill_backward(df, columns=params.get("columns"))
            elif action == "fill_value":
                df = fill_missing_value(df, columns=params.get("columns", []), value=params.get("value", ""))
            elif action == "drop_duplicates":
                before = len(df)
                df = drop_duplicates(df)
                exec_results.append(f"去重: 移除 {before - len(df)} 行")
                continue
            elif action == "deduplicate_subset":
                before = len(df)
                df = deduplicate_subset(df, columns=params.get("columns", []), keep=params.get("keep", "first"))
                exec_results.append(f"按列去重: 移除 {before - len(df)} 行")
                continue
            elif action == "remove_outliers":
                before = len(df)
                df = remove_outliers(df, columns=params.get("columns"), method=params.get("method", "iqr"))
                exec_results.append(f"异常值处理: 移除 {before - len(df)} 行")
                continue
            elif action == "trim_whitespace":
                df = trim_whitespace(df, columns=params.get("columns"))
            elif action == "standardize_case":
                df = standardize_case(df, columns=params.get("columns"), case=params.get("case", "lower"))
            elif action == "convert_dtype":
                df = convert_dtype(df, column=params.get("column", ""), target_type=params.get("target_type", "str"))
            elif action == "rename_columns":
                df = rename_columns(df, mapping=params.get("mapping", {}))
            elif action == "drop_columns":
                df = drop_columns(df, columns=params.get("columns", []))
            elif action == "drop_rows":
                before = len(df)
                df = drop_rows_by_condition(df, column=params.get("column", ""),
                                            operator=params.get("operator", "=="),
                                            value=params.get("value", ""))
                exec_results.append(f"条件筛选: 移除 {before - len(df)} 行")
                continue
            else:
                exec_results.append(f"未知操作 {action}，已跳过")
                continue
            exec_results.append(f"{action}: 完成")
        except Exception as e:
            exec_results.append(f"{action}: 失败 - {str(e)}")

    return _result(session, df, explanation or "；".join(exec_results))


# ---------- AI 高级数据处理（代码生成模式） ----------

# 沙箱允许的内置函数
_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "format": format,
    "frozenset": frozenset, "getattr": getattr, "hasattr": hasattr, "hash": hash,
    "int": int, "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
    "len": len, "list": list, "map": map, "max": max, "min": min, "next": next,
    "print": print, "range": range, "repr": repr, "reversed": reversed, "round": round,
    "set": set, "slice": slice, "sorted": sorted, "str": str, "sum": sum,
    "tuple": tuple, "type": type, "zip": zip, "True": True, "False": False, "None": None,
}

# 危险关键词黑名单
_DANGEROUS_KEYWORDS = [
    "import", "open(", "exec(", "eval(", "__import__", "compile(",
    "os.", "sys.", "subprocess", "shutil", "pathlib", "glob",
    "socket", "requests", "urllib", "http", "ftplib",
    "builtins", "globals(", "locals(", "vars(", "dir(",
    "getattr(", "setattr(", "delattr(", "breakpoint(", "input(",
    "exit(", "quit(", "help(",
]


def _validate_code(code: str) -> str | None:
    """检查代码安全性，返回错误信息或 None"""
    code_lower = code.lower()
    for kw in _DANGEROUS_KEYWORDS:
        if kw.lower() in code_lower:
            return f"代码包含不允许的操作: {kw}"
    return None


def _execute_pandas_code(code: str, df: "pd.DataFrame") -> tuple[dict, "pd.DataFrame"]:
    """在沙箱中执行 pandas 代码，返回 (结果信息, 新 DataFrame)"""
    import pandas as _pd
    import numpy as _np

    restricted_globals = {"__builtins__": _SAFE_BUILTINS}
    local_vars = {"pd": _pd, "np": _np, "df": df.copy()}

    try:
        exec(code, restricted_globals, local_vars)
    except Exception as e:
        return {"error": f"代码执行出错: {type(e).__name__}: {str(e)}"}, df

    result_df = local_vars.get("df")
    if result_df is None or not isinstance(result_df, _pd.DataFrame):
        return {"error": "代码执行后未产生有效的 DataFrame，请确保结果赋值给 df 变量"}, df

    return {"success": True}, result_df


@router.post("/ai-transform")
async def ai_transform(body: dict):
    """AI 高级数据处理：LLM 生成 pandas 代码，在沙箱中执行。"""
    session_id = body.get("session_id", "default")
    instruction = body.get("instruction", "")
    session, df, err = _get_df(session_id)
    if err:
        return err

    if not instruction.strip():
        return {"error": "请输入处理指令"}

    logger.info(f"AI高级处理: {instruction} (session={session_id})")

    data_context = _build_data_context(df)
    columns_info = ", ".join([f"{col}({dtype})" for col, dtype in df.dtypes.items()])

    prompt = (
        f"你是一个 pandas 数据处理专家。用户想对 DataFrame 进行处理。\n\n"
        f"用户指令: {instruction}\n\n"
        f"数据概况:\n"
        f"- 行数: {len(df)}, 列数: len(df.columns)\n"
        f"- 列名及类型: {columns_info}\n"
        f"- 前3行数据: {df.head(3).to_string()}\n\n"
        f"规则:\n"
        f"1. 只返回可执行的 Python/pandas 代码，不要任何解释\n"
        f"2. 变量 df 已存在，代表当前 DataFrame\n"
        f"3. 处理结果必须赋值给 df（如 df = df.xxx() 或 df['新列'] = ...）\n"
        f"4. 可以使用 pd 和 np\n"
        f"5. 不能 import、不能读写文件、不能使用 os/sys\n"
        f"6. 代码要简洁高效\n\n"
        f"示例:\n"
        f"用户: 新增利润率列\n"
        f"代码: df['利润率'] = df['利润'] / df['销售额']\n\n"
        f"用户: 按地区统计总销售额\n"
        f"代码: df = df.groupby('地区')['销售额'].sum().reset_index()\n\n"
        f"用户: 把销售额大于1000标记为高\n"
        f"代码: df['销售等级'] = df['销售额'].apply(lambda x: '高' if x > 1000 else '低')\n\n"
        f"只返回代码，不要其他任何文字。"
    )

    llm = get_llm_client()
    llm_result = await llm.chat([{"role": "user", "content": prompt}])

    code = (llm_result.get("content") or "").strip()
    # 去除 markdown 代码块包裹
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    code = code.strip()

    if not code:
        return {"error": "AI 未能生成有效的处理代码"}

    # 安全检查
    security_err = _validate_code(code)
    if security_err:
        logger.warning(f"AI代码安全检查失败: {security_err}")
        return {"error": security_err}

    logger.info(f"AI生成代码:\n{code}")

    # 执行
    exec_result, new_df = _execute_pandas_code(code, df)

    if "error" in exec_result:
        return {"error": exec_result["error"], "code": code}

    # 构建变更摘要
    old_cols = set(df.columns)
    new_cols = set(new_df.columns)
    added = new_cols - old_cols
    removed = old_cols - new_cols
    rows_before = len(df)
    rows_after = len(new_df)

    summary_parts = []
    if added:
        summary_parts.append(f"新增列: {', '.join(added)}")
    if removed:
        summary_parts.append(f"删除列: {', '.join(removed)}")
    if rows_before != rows_after:
        summary_parts.append(f"行数: {rows_before} → {rows_after}")
    if not summary_parts:
        summary_parts.append("数据已更新")

    return _result(session, new_df, "；".join(summary_parts) + f"\n\n执行代码:\n{code}")
