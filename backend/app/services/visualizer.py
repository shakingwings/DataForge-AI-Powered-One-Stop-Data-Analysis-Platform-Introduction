from __future__ import annotations
import json
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder


def _to_json(fig) -> dict:
    return json.loads(json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder))


def recommend_chart_type(df: pd.DataFrame, x_col: str = "", y_col: str = "") -> str:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    if datetime_cols and numeric_cols:
        return "line"
    if categorical_cols and numeric_cols:
        n_categories = df[categorical_cols[0]].nunique() if categorical_cols else 0
        if n_categories <= 8:
            return "bar"
        return "bar"
    if len(numeric_cols) >= 2:
        return "scatter"
    return "bar"


def generate_line_chart(df: pd.DataFrame, x: str, y: str, title: str = "", color: str = "") -> dict:
    kwargs = {"x": x, "y": y, "title": title or f"{y} 趋势", "markers": True}
    if color and color in df.columns:
        kwargs["color"] = color
    fig = px.line(df, **kwargs)
    fig.update_layout(template="plotly_white", font=dict(family="Microsoft YaHei, sans-serif"))
    return _to_json(fig)


def generate_bar_chart(df: pd.DataFrame, x: str, y: str, title: str = "", color: str = "") -> dict:
    kwargs = {"x": x, "y": y, "title": title or f"{y} 对比", "text_auto": ".2s"}
    if color and color in df.columns:
        kwargs["color"] = color
    fig = px.bar(df, **kwargs)
    fig.update_layout(template="plotly_white", font=dict(family="Microsoft YaHei, sans-serif"))
    return _to_json(fig)


def generate_pie_chart(df: pd.DataFrame, names: str, values: str, title: str = "") -> dict:
    fig = px.pie(df, names=names, values=values, title=title or f"{values} 占比")
    fig.update_layout(template="plotly_white", font=dict(family="Microsoft YaHei, sans-serif"))
    return _to_json(fig)


def generate_scatter_chart(df: pd.DataFrame, x: str, y: str, title: str = "", color: str = "") -> dict:
    kwargs = {"x": x, "y": y, "title": title or f"{x} vs {y}"}
    if color and color in df.columns:
        kwargs["color"] = color
    fig = px.scatter(df, **kwargs)
    fig.update_layout(template="plotly_white", font=dict(family="Microsoft YaHei, sans-serif"))
    return _to_json(fig)


def generate_heatmap(corr_matrix: dict, title: str = "相关性热力图") -> dict:
    labels = list(corr_matrix.keys())
    z = [[corr_matrix[c1].get(c2, 0) for c2 in labels] for c1 in labels]
    fig = go.Figure(data=go.Heatmap(z=z, x=labels, y=labels, colorscale="RdBu_r", zmin=-1, zmax=1))
    fig.update_layout(title=title, template="plotly_white", font=dict(family="Microsoft YaHei, sans-serif"))
    return _to_json(fig)


def generate_box_chart(df: pd.DataFrame, x: str, y: str, title: str = "") -> dict:
    fig = px.box(df, x=x, y=y, title=title or f"{y} 分布")
    fig.update_layout(template="plotly_white", font=dict(family="Microsoft YaHei, sans-serif"))
    return _to_json(fig)


def generate_area_chart(df: pd.DataFrame, x: str, y: str, title: str = "", color: str = "") -> dict:
    kwargs = {"x": x, "y": y, "title": title or f"{y} 面积图"}
    if color and color in df.columns:
        kwargs["color"] = color
    fig = px.area(df, **kwargs)
    fig.update_layout(template="plotly_white", font=dict(family="Microsoft YaHei, sans-serif"))
    return _to_json(fig)


def generate_radar_chart(categories: list[str], values: list[float], title: str = "雷达图") -> dict:
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill="toself"))
    fig.update_layout(title=title, template="plotly_white", font=dict(family="Microsoft YaHei, sans-serif"))
    return _to_json(fig)


CHART_GENERATORS = {
    "line": lambda df, **kw: generate_line_chart(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", ""), kw.get("color", "")),
    "bar": lambda df, **kw: generate_bar_chart(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", ""), kw.get("color", "")),
    "pie": lambda df, **kw: generate_pie_chart(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", "")),
    "scatter": lambda df, **kw: generate_scatter_chart(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", ""), kw.get("color", "")),
    "box": lambda df, **kw: generate_box_chart(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", "")),
    "area": lambda df, **kw: generate_area_chart(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", ""), kw.get("color", "")),
    "heatmap": lambda df, **kw: generate_heatmap_from_df(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", "")),
    "radar": lambda df, **kw: generate_radar_from_df(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", "")),
    "china_map": lambda df, **kw: generate_china_map(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", "")),
    "world_map": lambda df, **kw: generate_world_map(df, kw.get("x", ""), kw.get("y", ""), kw.get("title", "")),
}


def generate_heatmap_from_df(df: pd.DataFrame, x: str, y: str, title: str = "") -> dict:
    numeric_df = df.select_dtypes(include=[np.number])
    corr = numeric_df.corr()
    return generate_heatmap(corr.to_dict(), title=title or "相关性热力图")


def generate_radar_from_df(df: pd.DataFrame, category_col: str, value_col: str, title: str = "") -> dict:
    if category_col and category_col in df.columns and value_col and value_col in df.columns:
        cats = df[category_col].astype(str).tolist()[:10]
        vals = pd.to_numeric(df[value_col], errors="coerce").fillna(0).tolist()[:10]
    else:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            return generate_radar_chart(["无数据"], [0])
        vals = df[numeric_cols[0]].tolist()[:10]
        cats = [f"项{i+1}" for i in range(len(vals))]
    return generate_radar_chart(cats, vals, title=title or "雷达图")


# ---------- 地理地图 ----------

CHINA_PROVINCES = {
    "北京", "天津", "上海", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "海南",
    "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆",
    "香港", "澳门",
}

# 短名称 -> GeoJSON 全称 映射
_TO_GEOJSON_NAME = {
    "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
    "河北省": "河北省", "山西": "山西省", "辽宁": "辽宁省", "吉林": "吉林省",
    "黑龙江": "黑龙江省", "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
    "福建": "福建省", "江西": "江西省", "山东": "山东省", "河南": "河南省",
    "湖北": "湖北省", "湖南": "湖南省", "广东": "广东省", "海南": "海南省",
    "四川": "四川省", "贵州": "贵州省", "云南": "云南省", "陕西": "陕西省",
    "甘肃": "甘肃省", "青海": "青海省", "台湾": "台湾省",
    "内蒙古": "内蒙古自治区", "广西": "广西壮族自治区", "西藏": "西藏自治区",
    "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
    "香港": "香港特别行政区", "澳门": "澳门特别行政区",
}
# 反向映射：全称 -> 短名
_FROM_GEOJSON_NAME = {v: k for k, v in _TO_GEOJSON_NAME.items()}

# 用户输入可能的各种格式 -> GeoJSON 全称
CHINA_PROVINCES_FULL = {}
for short, full in _TO_GEOJSON_NAME.items():
    CHINA_PROVINCES_FULL[short] = full
    CHINA_PROVINCES_FULL[full] = full
    CHINA_PROVINCES_FULL[short + "省"] = full
    CHINA_PROVINCES_FULL[short + "市"] = full
    CHINA_PROVINCES_FULL[short + "自治区"] = full
    CHINA_PROVINCES_FULL[short + "特别行政区"] = full

WORLD_COUNTRIES = {
    "中国": "China", "美国": "United States of America", "日本": "Japan", "韩国": "South Korea",
    "英国": "United Kingdom", "法国": "France", "德国": "Germany", "俄罗斯": "Russia",
    "加拿大": "Canada", "澳大利亚": "Australia", "巴西": "Brazil", "印度": "India",
    "意大利": "Italy", "西班牙": "Spain", "墨西哥": "Mexico", "印度尼西亚": "Indonesia",
    "荷兰": "Netherlands", "沙特阿拉伯": "Saudi Arabia", "土耳其": "Turkey", "瑞士": "Switzerland",
    "波兰": "Poland", "阿根廷": "Argentina", "瑞典": "Sweden", "挪威": "Norway",
    "奥地利": "Austria", "泰国": "Thailand", "越南": "Vietnam", "马来西亚": "Malaysia",
    "新加坡": "Singapore", "菲律宾": "Philippines", "埃及": "Egypt", "南非": "South Africa",
    "尼日利亚": "Nigeria", "肯尼亚": "Kenya", "以色列": "Israel", "阿联酋": "United Arab Emirates",
    "新西兰": "New Zealand", "智利": "Chile", "哥伦比亚": "Colombia", "秘鲁": "Peru",
    "巴基斯坦": "Pakistan", "孟加拉国": "Bangladesh", "缅甸": "Myanmar", "柬埔寨": "Cambodia",
    "朝鲜": "North Korea", "蒙古": "Mongolia", "伊朗": "Iran", "伊拉克": "Iraq",
    "阿富汗": "Afghanistan", "乌克兰": "Ukraine", "波兰": "Poland", "芬兰": "Finland",
    "丹麦": "Denmark", "比利时": "Belgium", "葡萄牙": "Portugal", "希腊": "Greece",
    "捷克": "Czech Republic", "罗马尼亚": "Romania", "匈牙利": "Hungary",
    "斯里兰卡": "Sri Lanka", "尼泊尔": "Nepal", "老挝": "Laos",
}


# Add English names as pass-through mappings
_EN_TO_EN = {v: v for v in WORLD_COUNTRIES.values()}
WORLD_COUNTRIES.update(_EN_TO_EN)

def _detect_region_col(df: pd.DataFrame) -> str | None:
    """检测哪一列包含中国省份或世界国家名称"""
    for col in df.select_dtypes(include=["object"]).columns:
        values = set(df[col].dropna().astype(str).str.strip())
        if not values:
            continue
        china_match = len(values & CHINA_PROVINCES) / len(values)
        if china_match > 0.5:
            return col
        full_match = 0
        for v in values:
            if v in CHINA_PROVINCES_FULL or v in WORLD_COUNTRIES:
                full_match += 1
        if full_match / len(values) > 0.5:
            return col
    return None


def generate_china_map(df: pd.DataFrame, region_col: str, value_col: str, title: str = "") -> dict:
    if not region_col or region_col not in df.columns:
        region_col = _detect_region_col(df) or df.columns[0]
    if not value_col or value_col not in df.columns:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        value_col = numeric_cols[0] if numeric_cols else df.columns[-1]

    map_df = df[[region_col, value_col]].copy()
    map_df[region_col] = map_df[region_col].astype(str).str.strip()
    map_df[region_col] = map_df[region_col].map(lambda x: CHINA_PROVINCES_FULL.get(x, x))
    map_df[value_col] = pd.to_numeric(map_df[value_col], errors="coerce").fillna(0)

    agg = map_df.groupby(region_col)[value_col].sum().reset_index()
    data = [{"name": row[region_col], "value": row[value_col]} for _, row in agg.iterrows()]

    return {
        "chart_type": "china_map",
        "title": title or f"{value_col} 中国地图",
        "echarts_option": {
            "title": {"text": title or f"{value_col} 中国地图", "left": "center"},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c}"},
            "visualMap": {
                "min": int(agg[value_col].min()),
                "max": int(agg[value_col].max()),
                "left": "left", "top": "bottom",
                "text": ["高", "低"],
                "calculable": True,
                "inRange": {"color": ["#e0f3f8", "#abd9e9", "#74add1", "#4575b4", "#313695"]},
            },
            "series": [{
                "type": "map", "map": "china", "roam": True,
                "data": data,
                "label": {"show": True, "fontSize": 10},
            }],
        },
    }


def generate_world_map(df: pd.DataFrame, region_col: str, value_col: str, title: str = "") -> dict:
    if not region_col or region_col not in df.columns:
        region_col = _detect_region_col(df) or df.columns[0]
    if not value_col or value_col not in df.columns:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        value_col = numeric_cols[0] if numeric_cols else df.columns[-1]

    map_df = df[[region_col, value_col]].copy()
    map_df[region_col] = map_df[region_col].astype(str).str.strip()
    map_df[region_col] = map_df[region_col].map(lambda x: WORLD_COUNTRIES.get(x, x))
    map_df[value_col] = pd.to_numeric(map_df[value_col], errors="coerce").fillna(0)

    agg = map_df.groupby(region_col)[value_col].sum().reset_index()
    data = [{"name": row[region_col], "value": row[value_col]} for _, row in agg.iterrows()]

    return {
        "chart_type": "world_map",
        "title": title or f"{value_col} 世界地图",
        "echarts_option": {
            "title": {"text": title or f"{value_col} 世界地图", "left": "center"},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c}"},
            "visualMap": {
                "min": int(agg[value_col].min()),
                "max": int(agg[value_col].max()),
                "left": "left", "top": "bottom",
                "text": ["高", "低"],
                "calculable": True,
                "inRange": {"color": ["#e0f3f8", "#abd9e9", "#74add1", "#4575b4", "#313695"]},
            },
            "series": [{
                "type": "map", "map": "world", "roam": True,
                "data": data,
                "label": {"show": False},
            }],
        },
    }


def auto_generate_charts(df: pd.DataFrame, max_charts: int = 3) -> list[dict]:
    charts = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # 检测地理数据
    region_col = _detect_region_col(df)
    if region_col and numeric_cols:
        val_col = numeric_cols[0]
        # 判断是中国还是世界
        values = set(df[region_col].dropna().astype(str).str.strip())
        is_china = len(values & CHINA_PROVINCES) / len(values) > 0.3 if values else False
        if is_china:
            charts.append(generate_china_map(df, region_col, val_col))
        else:
            charts.append(generate_world_map(df, region_col, val_col))

    if datetime_cols and numeric_cols:
        for y_col in numeric_cols[:2]:
            charts.append(generate_line_chart(df, datetime_cols[0], y_col))

    if categorical_cols and numeric_cols:
        for y_col in numeric_cols[:1]:
            n_cat = df[categorical_cols[0]].nunique()
            if n_cat <= 8:
                charts.append(generate_bar_chart(df, categorical_cols[0], y_col))
                charts.append(generate_pie_chart(df, categorical_cols[0], y_col))

    if len(numeric_cols) >= 2 and len(charts) < max_charts:
        charts.append(generate_scatter_chart(df, numeric_cols[0], numeric_cols[1]))

    return charts[:max_charts]
