from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import aiosqlite

from app.config import settings
from app.utils.logger import logger

_db: Optional[aiosqlite.Connection] = None
_db_lock = asyncio.Lock()

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    pinned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at);
CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    "start" TEXT NOT NULL,
    "end" TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    all_day INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_start ON events("start");
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_updated_at ON events(updated_at);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 3,
    due_at TEXT,
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_at ON tasks(due_at);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at);
"""


def _resolve_db_path(raw_path: str) -> str:
    value = (raw_path or "").strip()
    if not value:
        value = "data/lifeos.db"

    if value == ":memory:":
        return value

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)
    except Exception as exc:
        logger.warning(f"Could not create sqlite directory {path.parent}: {exc}")

    fallback = Path.home() / ".lifeos" / "lifeos.db"
    try:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Falling back to {fallback}")
        return str(fallback)
    except Exception as exc:
        logger.warning(f"Falling back to in-memory SQLite: {exc}")
        return ":memory:"


async def _init_schema(conn: aiosqlite.Connection) -> None:
    await conn.executescript(_SCHEMA_SQL)
    await _run_migrations(conn)
    await conn.commit()


async def _table_exists(conn: aiosqlite.Connection, table: str) -> bool:
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ) as cursor:
        row = await cursor.fetchone()
    return row is not None


async def _ensure_columns(
    conn: aiosqlite.Connection, table: str, columns: dict[str, str]
) -> None:
    if not await _table_exists(conn, table):
        return

    async with conn.execute(f"PRAGMA table_info({table})") as cursor:
        rows = await cursor.fetchall()
    existing = {row["name"] for row in rows}

    for name, definition in columns.items():
        if name not in existing:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


async def _run_migrations(conn: aiosqlite.Connection) -> None:
    await _ensure_columns(
        conn,
        "notes",
        {
            "tags": "tags TEXT NOT NULL DEFAULT ''",
            "pinned": "pinned INTEGER NOT NULL DEFAULT 0",
            "updated_at": "updated_at TEXT",
        },
    )
    await _ensure_columns(
        conn,
        "events",
        {
            "location": "location TEXT NOT NULL DEFAULT ''",
            "description": "description TEXT NOT NULL DEFAULT ''",
            "all_day": "all_day INTEGER NOT NULL DEFAULT 0",
            "updated_at": "updated_at TEXT",
        },
    )
    await _ensure_columns(
        conn,
        "tasks",
        {
            "description": "description TEXT NOT NULL DEFAULT ''",
            "status": "status TEXT NOT NULL DEFAULT 'pending'",
            "priority": "priority INTEGER NOT NULL DEFAULT 3",
            "due_at": "due_at TEXT",
            "tags": "tags TEXT NOT NULL DEFAULT ''",
            "updated_at": "updated_at TEXT",
        },
    )

    await conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);
        CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at);
        CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned);

        CREATE INDEX IF NOT EXISTS idx_events_start ON events("start");
        CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
        CREATE INDEX IF NOT EXISTS idx_events_updated_at ON events(updated_at);

        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_due_at ON tasks(due_at);
        CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
        CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at);
        """
    )

    await conn.execute(
        "UPDATE notes SET updated_at = created_at WHERE updated_at IS NULL"
    )
    await conn.execute("UPDATE notes SET tags = '' WHERE tags IS NULL")
    await conn.execute("UPDATE notes SET pinned = 0 WHERE pinned IS NULL")

    await conn.execute(
        "UPDATE events SET updated_at = created_at WHERE updated_at IS NULL"
    )
    await conn.execute("UPDATE events SET location = '' WHERE location IS NULL")
    await conn.execute("UPDATE events SET description = '' WHERE description IS NULL")
    await conn.execute("UPDATE events SET all_day = 0 WHERE all_day IS NULL")

    if await _table_exists(conn, "tasks"):
        await conn.execute(
            "UPDATE tasks SET updated_at = created_at WHERE updated_at IS NULL"
        )
        await conn.execute("UPDATE tasks SET tags = '' WHERE tags IS NULL")
        await conn.execute("UPDATE tasks SET status = 'pending' WHERE status IS NULL")
        await conn.execute("UPDATE tasks SET priority = 3 WHERE priority IS NULL")


async def get_database() -> aiosqlite.Connection:
    """Return a shared SQLite connection, initializing schema on first use."""
    global _db

    if _db is not None:
        return _db

    async with _db_lock:
        if _db is not None:
            return _db

        db_path = _resolve_db_path(settings.SQLITE_DB_PATH)
        try:
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute("PRAGMA foreign_keys=ON;")
            await conn.execute("PRAGMA busy_timeout=5000;")
            await _init_schema(conn)
            _db = conn
            logger.info(f"SQLite ready at {db_path}")
            return _db
        except Exception:
            logger.exception("SQLite initialization failed")
            raise
