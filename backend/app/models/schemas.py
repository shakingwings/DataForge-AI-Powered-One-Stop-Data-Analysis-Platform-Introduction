from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    charts: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}


class DataUploadResponse(BaseModel):
    filename: str
    rows: int
    columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    preview: list[dict[str, Any]]


class AnalysisRequest(BaseModel):
    session_id: str = "default"
    analysis_type: str = "auto"  # auto, trend, compare, correlation, distribution
    columns: list[str] = []


class AnalysisResponse(BaseModel):
    summary: str
    metrics: dict[str, Any] = {}
    charts: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []


class VisualizationRequest(BaseModel):
    session_id: str = "default"
    chart_type: str = "auto"
    x_column: str = ""
    y_column: str = ""
    group_by: str = ""
    title: str = ""


class ExportRequest(BaseModel):
    session_id: str = "default"
    format: str = "png"  # png, pdf, html, xlsx
    content: str = "all"  # all, chart, data


class LLMConfig(BaseModel):
    provider: str = "openai"
    api_key: str = ""
    base_url: str = ""
    model: str = ""


class SessionData:
    """In-memory session store for uploaded data and analysis results."""

    def __init__(self):
        self.sessions: dict[str, dict] = {}

    def get(self, session_id: str) -> dict:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "df": None,
                "filename": "",
                "history": [],
                "charts": [],
                "analysis": {},
            }
        return self.sessions[session_id]

    def clear(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]


session_store = SessionData()
