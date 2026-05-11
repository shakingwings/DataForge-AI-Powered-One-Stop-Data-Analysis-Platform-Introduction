from fastapi import APIRouter

from app.models.schemas import session_store, VisualizationRequest
from app.services import visualizer

router = APIRouter(prefix="/api/visualization", tags=["visualization"])


@router.post("/generate")
async def generate_chart(req: VisualizationRequest):
    session = session_store.get(req.session_id)
    df = session.get("df")
    if df is None:
        return {"error": "请先上传数据"}

    chart_type = req.chart_type
    if chart_type == "auto":
        chart_type = visualizer.recommend_chart_type(df, req.x_column, req.y_column)

    x = req.x_column or df.columns[0]
    y = req.y_column or ""
    if not y:
        numeric = df.select_dtypes(include=["number"]).columns.tolist()
        y = numeric[0] if numeric else (df.columns[1] if len(df.columns) > 1 else "")

    # 地图类型走专用路径
    if chart_type in ("china_map", "world_map"):
        gen = visualizer.CHART_GENERATORS.get(chart_type)
        if gen:
            chart = gen(df, x=x, y=y, title=req.title)
            return {"chart": chart, "chart_type": chart_type}
        return {"error": f"不支持的图表类型: {chart_type}"}

    gen = visualizer.CHART_GENERATORS.get(chart_type)
    if gen:
        chart = gen(df, x=x, y=y, color=req.group_by, title=req.title)
        return {"chart": chart, "chart_type": chart_type}
    return {"error": f"不支持的图表类型: {chart_type}"}


@router.get("/auto")
async def auto_charts(session_id: str = "default"):
    session = session_store.get(session_id)
    df = session.get("df")
    if df is None:
        return {"error": "请先上传数据"}
    charts = visualizer.auto_generate_charts(df)
    return {"charts": charts}
