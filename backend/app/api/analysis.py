from fastapi import APIRouter

from app.core.database import save_analysis
from app.core.logger import get_logger
from app.models.schemas import session_store, AnalysisRequest, AnalysisResponse
from app.services import analyzer, data_processor

logger = get_logger("api.analysis")
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(req: AnalysisRequest):
    session = session_store.get(req.session_id)
    df = session.get("df")
    if df is None:
        return AnalysisResponse(summary="请先上传数据")

    logger.info(f"执行分析: {req.analysis_type} (session={req.session_id})")

    result = {"summary": "", "metrics": {}, "charts": [], "tables": []}

    if req.analysis_type in ("auto", "basic_stats"):
        stats = analyzer.basic_stats(df, req.columns or None)
        result["metrics"]["basic_stats"] = stats

    if req.analysis_type in ("auto", "correlation"):
        corr = analyzer.correlation_analysis(df, req.columns or None)
        result["metrics"]["correlation"] = corr

    if req.analysis_type == "trend":
        time_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if time_cols and numeric_cols:
            trend = analyzer.trend_analysis(df, time_cols[0], req.columns[0] if req.columns else numeric_cols[0])
            result["metrics"]["trend"] = trend

    if req.analysis_type == "anomaly":
        anomalies = analyzer.anomaly_detection(df, req.columns or None)
        result["metrics"]["anomaly"] = anomalies

    summary_parts = []
    for key, val in result["metrics"].items():
        if isinstance(val, dict):
            summary_parts.append(f"【{key}】已完成分析")
    result["summary"] = "；".join(summary_parts) if summary_parts else "分析完成"

    await save_analysis(req.session_id, req.analysis_type, result["summary"], result["metrics"])
    logger.info(f"分析完成: {req.analysis_type}")

    return AnalysisResponse(**result)
