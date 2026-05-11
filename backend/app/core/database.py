from __future__ import annotations

import json
from datetime import datetime

import aiosqlite

DB_PATH = None


def set_db_path(path: str):
    global DB_PATH
    DB_PATH = path


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                filename TEXT,
                rows INTEGER,
                columns INTEGER,
                column_names TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS analysis_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                summary TEXT,
                metrics TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_analysis_session ON analysis_records(session_id);
        """)
        await db.commit()
    finally:
        await db.close()


async def save_session(session_id: str, filename: str, rows: int, columns: int, column_names: list):
    db = await get_db()
    try:
        now = datetime.now().isoformat()
        await db.execute(
            """INSERT INTO sessions (id, filename, rows, columns, column_names, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
               filename=excluded.filename, rows=excluded.rows, columns=excluded.columns,
               column_names=excluded.column_names, updated_at=excluded.updated_at""",
            (session_id, filename, rows, columns, json.dumps(column_names, ensure_ascii=False), now, now),
        )
        await db.commit()
    finally:
        await db.close()


async def save_message(session_id: str, role: str, content: str):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        await db.commit()
    finally:
        await db.close()


async def save_analysis(session_id: str, analysis_type: str, summary: str, metrics: dict):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO analysis_records (session_id, analysis_type, summary, metrics) VALUES (?, ?, ?, ?)",
            (session_id, analysis_type, summary, json.dumps(metrics, ensure_ascii=False, default=str)),
        )
        await db.commit()
    finally:
        await db.close()


async def get_sessions(limit: int = 50) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, filename, rows, columns, column_names, created_at, updated_at "
            "FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "filename": r["filename"],
                "rows": r["rows"],
                "columns": r["columns"],
                "column_names": json.loads(r["column_names"]) if r["column_names"] else [],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        return result
    finally:
        await db.close()


async def get_session_detail(session_id: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = await cursor.fetchone()
        if not session:
            return None

        cursor = await db.execute(
            "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        messages = [{"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT analysis_type, summary, metrics, created_at FROM analysis_records WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        analyses = []
        for r in await cursor.fetchall():
            analyses.append({
                "analysis_type": r["analysis_type"],
                "summary": r["summary"],
                "metrics": json.loads(r["metrics"]) if r["metrics"] else {},
                "created_at": r["created_at"],
            })

        return {
            "id": session["id"],
            "filename": session["filename"],
            "rows": session["rows"],
            "columns": session["columns"],
            "column_names": json.loads(session["column_names"]) if session["column_names"] else [],
            "created_at": session["created_at"],
            "messages": messages,
            "analyses": analyses,
        }
    finally:
        await db.close()


async def delete_session(session_id: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()
