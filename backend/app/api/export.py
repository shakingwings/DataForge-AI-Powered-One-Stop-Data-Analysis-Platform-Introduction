import io
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import session_store, ExportRequest
from app.services import analyzer, data_processor, visualizer

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/data")
async def export_data(req: ExportRequest):
    session = session_store.get(req.session_id)
    df = session.get("df")
    if df is None:
        return {"error": "请先上传数据"}

    if req.format == "xlsx":
        output = io.BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)
        filename = f"{session.get('filename', 'data')}_export.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    elif req.format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        filename = f"{session.get('filename', 'data')}_export.csv"
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    return {"error": f"不支持的导出格式: {req.format}"}


@router.post("/chart")
async def export_chart(req: ExportRequest):
    session = session_store.get(req.session_id)
    df = session.get("df")
    if df is None:
        return {"error": "请先上传数据"}

    try:
        import plotly.io as pio
        charts = visualizer.auto_generate_charts(df)
        if not charts:
            return {"error": "没有可导出的图表"}
        chart_data = charts[0]
        fig = pio.from_dict(chart_data)

        if req.format == "png":
            img_bytes = fig.to_image(format="png", width=1200, height=600, scale=2)
            return StreamingResponse(
                io.BytesIO(img_bytes),
                media_type="image/png",
                headers={"Content-Disposition": "attachment; filename=chart.png"},
            )
        elif req.format == "html":
            html_str = fig.to_html(include_plotlyjs="cdn")
            return StreamingResponse(
                io.BytesIO(html_str.encode("utf-8")),
                media_type="text/html",
                headers={"Content-Disposition": "attachment; filename=chart.html"},
            )
    except Exception as e:
        return {"error": f"导出失败: {str(e)}"}

    return {"error": f"不支持的导出格式: {req.format}"}


@router.post("/report")
async def export_report(req: ExportRequest):
    session = session_store.get(req.session_id)
    df = session.get("df")
    analysis = session.get("analysis", {})
    chat_history = session.get("history", [])

    if df is None:
        return {"error": "请先上传数据"}

    if req.format == "html":
        import plotly.io as pio

        # Generate charts fresh from data
        charts = visualizer.auto_generate_charts(df)
        chart_htmls = []
        for c in charts:
            try:
                fig = pio.from_dict(c)
                chart_htmls.append(pio.to_html(fig, include_plotlyjs="cdn", full_html=False))
            except Exception:
                pass

        # Generate analysis data
        info = data_processor.get_data_info(df)
        stats = analyzer.basic_stats(df)

        # Build stats table rows
        stats_rows = ""
        for col, vals in stats.items():
            stats_rows += f"""<tr>
                <td class="col-name">{col}</td>
                <td>{vals.get('count', '-')}</td>
                <td>{_fmt(vals.get('mean'))}</td>
                <td>{_fmt(vals.get('median'))}</td>
                <td>{_fmt(vals.get('std'))}</td>
                <td>{_fmt(vals.get('min'))}</td>
                <td>{_fmt(vals.get('max'))}</td>
                <td>{_fmt(vals.get('sum'))}</td>
            </tr>"""

        # Build data preview table
        preview = info.get("preview", [])
        col_names = info.get("column_names", [])
        preview_header = "".join(f"<th>{c}</th>" for c in col_names)
        preview_rows = ""
        for row in preview[:10]:
            cells = "".join(f"<td>{row.get(c, '')}</td>" for c in col_names)
            preview_rows += f"<tr>{cells}</tr>"

        # Chat summary
        chat_section = ""
        if chat_history:
            chat_items = ""
            for h in chat_history[-10:]:
                role = "用户" if h.get("role") == "user" else "助手"
                cls = "user" if h.get("role") == "user" else "assistant"
                chat_items += f'<div class="chat-msg {cls}"><b>{role}：</b>{h.get("content", "")}</div>'
            chat_section = f'<h2>对话分析记录</h2><div class="chat-box">{chat_items}</div>'

        # Analysis summary from chat
        summary_text = analysis.get("summary", "")
        if not summary_text and chat_history:
            for h in reversed(chat_history):
                if h.get("role") == "assistant":
                    summary_text = h.get("content", "")
                    break
        if not summary_text:
            summary_text = "暂无分析结论，请在对话框中输入分析指令生成结论。"

        filename = session.get("filename", "data")
        charts_section = "".join(
            f'<div class="chart-wrapper"><h3>图 {i + 1}</h3>{h}</div>'
            for i, h in enumerate(chart_htmls)
        ) if chart_htmls else "<p>暂无图表</p>"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>数据分析报告 - {filename}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #f5f7fa; color: #333; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 24px; }}
  h1 {{ font-size: 28px; color: #1a1a2e; margin-bottom: 8px; }}
  .subtitle {{ color: #909399; font-size: 14px; margin-bottom: 32px; }}
  h2 {{ font-size: 18px; color: #16213e; border-left: 4px solid #409eff; padding-left: 12px;
       margin: 28px 0 16px; }}
  h3 {{ font-size: 15px; color: #303133; margin: 16px 0 8px; }}
  .overview {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
  .overview-card {{ background: #fff; border-radius: 8px; padding: 16px; text-align: center;
                    border: 1px solid #e4e7ed; }}
  .overview-card .value {{ font-size: 24px; font-weight: 700; color: #409eff; }}
  .overview-card .label {{ font-size: 12px; color: #909399; margin-top: 4px; }}
  .summary-box {{ background: linear-gradient(135deg, #f0f7ff, #e8f4fd); border-radius: 8px;
                  padding: 20px; border-left: 4px solid #409eff; line-height: 1.8; font-size: 15px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
  th, td {{ padding: 8px 12px; border: 1px solid #ebeef5; text-align: right; }}
  th {{ background: #409eff; color: #fff; font-weight: 600; text-align: center; }}
  td.col-name {{ text-align: left; font-weight: 600; background: #f5f7fa; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  tr:hover {{ background: #ecf5ff; }}
  .chart-wrapper {{ background: #fff; border-radius: 8px; padding: 16px; margin: 16px 0;
                    border: 1px solid #e4e7ed; }}
  .chat-box {{ background: #fff; border-radius: 8px; padding: 16px; border: 1px solid #e4e7ed;
               max-height: 400px; overflow-y: auto; }}
  .chat-msg {{ padding: 8px 12px; margin-bottom: 8px; border-radius: 6px; font-size: 14px; line-height: 1.6; }}
  .chat-msg.user {{ background: #ecf5ff; }}
  .chat-msg.assistant {{ background: #f4f4f5; }}
  .footer {{ text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 40px; padding-top: 20px;
             border-top: 1px solid #ebeef5; }}
</style></head><body>
<div class="container">
  <h1>数据分析报告</h1>
  <div class="subtitle">文件：{filename} &nbsp;|&nbsp; 生成时间：{_now()}</div>

  <h2>数据概况</h2>
  <div class="overview">
    <div class="overview-card"><div class="value">{info['rows']}</div><div class="label">数据行数</div></div>
    <div class="overview-card"><div class="value">{info['columns']}</div><div class="label">数据列数</div></div>
    <div class="overview-card"><div class="value">{info.get('duplicates', 0)}</div><div class="label">重复记录</div></div>
    <div class="overview-card"><div class="value">{sum(info.get('missing', {}).values())}</div><div class="label">缺失值总数</div></div>
  </div>

  <h2>核心结论</h2>
  <div class="summary-box">{summary_text.replace(chr(10), '<br>')}</div>

  <h2>关键统计指标</h2>
  <table>
    <thead><tr><th>字段</th><th>数量</th><th>均值</th><th>中位数</th><th>标准差</th><th>最小值</th><th>最大值</th><th>总和</th></tr></thead>
    <tbody>{stats_rows}</tbody>
  </table>

  <h2>数据预览（前10行）</h2>
  <table>
    <thead><tr><th>#</th>{preview_header}</tr></thead>
    <tbody>{"".join(f'<tr><td>{i+1}</td>{"".join(f"<td>{row.get(c, "")}</td>" for c in col_names)}</tr>' for i, row in enumerate(preview[:10]))}</tbody>
  </table>

  <h2>可视化图表</h2>
  {charts_section}

  {chat_section}

  <div class="footer">由DataForge-AI-Powered-One-Stop-Data-Analysis-Platform-Introduction自动生成</div>
</div>
</body></html>"""

        return StreamingResponse(
            io.BytesIO(html.encode("utf-8")),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=report_{filename}.html"},
        )

    return {"error": f"不支持的报告格式: {req.format}"}


def _fmt(v):
    if v is None:
        return "-"
    try:
        n = float(v)
        if abs(n) >= 1000:
            return f"{n:,.2f}"
        return f"{n:.4f}"
    except (ValueError, TypeError):
        return str(v)


def _now():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")
