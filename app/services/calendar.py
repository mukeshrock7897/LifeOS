from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db.sqlite import get_database
from app.utils.logger import logger


def _row_to_event(row) -> Dict[str, Any]:
    updated_at = row["updated_at"] or row["created_at"]
    return {
        "id": row["id"],
        "title": row["title"],
        "start": row["start"],
        "end": row["end"],
        "location": row["location"],
        "description": row["description"],
        "all_day": bool(row["all_day"]),
        "created_at": row["created_at"],
        "updated_at": updated_at,
    }


async def _fetch_event(db, event_id: int) -> Optional[Dict[str, Any]]:
    async with db.execute(
        "SELECT * FROM events WHERE id = ?", (int(event_id),)
    ) as cursor:
        row = await cursor.fetchone()
    return _row_to_event(row) if row else None


def register_calendar_tools(mcp) -> None:
    """Calendar/Event related MCP tools."""

    @mcp.tool()
    async def create_event(
        title: str,
        start: str,
        end: str,
        location: str = "",
        description: str = "",
        all_day: bool = False,
    ) -> Dict[str, Any]:
        """Create a calendar event.

        NOTE: `start` and `end` are stored as strings (ISO-8601 recommended).
        """
        if not title.strip():
            return {"status": "error", "error": "title cannot be empty"}
        try:
            db = await get_database()
            cursor = await db.execute(
                'INSERT INTO events (title, "start", "end", location, description, all_day, updated_at) '
                "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (title, start, end, location, description, int(bool(all_day))),
            )
            await db.commit()
            logger.info(f"Event created: {title}")
            event = await _fetch_event(db, cursor.lastrowid)
            return {"status": "ok", "event": event}
        except Exception as e:
            logger.exception("create_event failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def get_event(event_id: int) -> Dict[str, Any]:
        """Get a calendar event by ID."""
        try:
            db = await get_database()
            event = await _fetch_event(db, event_id)
            if not event:
                return {"status": "error", "error": "event not found"}
            return {"event": event}
        except Exception as e:
            logger.exception("get_event failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def list_events(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List calendar events."""
        try:
            db = await get_database()
            lim = max(1, min(int(limit), 500))
            off = max(0, int(offset))
            async with db.execute(
                'SELECT * FROM events ORDER BY "start" LIMIT ? OFFSET ?',
                (lim, off),
            ) as cursor:
                rows = await cursor.fetchall()
            events = [_row_to_event(row) for row in rows]
            return {"events": events, "count": len(events), "next_offset": off + len(events)}
        except Exception as e:
            logger.exception("list_events failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def search_events(query: str, limit: int = 50) -> Dict[str, Any]:
        """Search events by title, location, or description."""
        if not query.strip():
            return {"status": "error", "error": "query cannot be empty"}
        try:
            db = await get_database()
            lim = max(1, min(int(limit), 200))
            pattern = f"%{query}%"
            async with db.execute(
                "SELECT * FROM events WHERE "
                "(title LIKE ? COLLATE NOCASE OR location LIKE ? COLLATE NOCASE "
                "OR description LIKE ? COLLATE NOCASE) "
                'ORDER BY "start" LIMIT ?',
                (pattern, pattern, pattern, lim),
            ) as cursor:
                rows = await cursor.fetchall()
            events = [_row_to_event(row) for row in rows]
            return {"results": events}
        except Exception as e:
            logger.exception("search_events failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def list_upcoming_events(
        limit: int = 20, from_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """List upcoming events from a date (ISO-8601 recommended)."""
        try:
            db = await get_database()
            lim = max(1, min(int(limit), 200))
            if not from_date:
                from_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            async with db.execute(
                'SELECT * FROM events WHERE "start" >= ? ORDER BY "start" LIMIT ?',
                (from_date, lim),
            ) as cursor:
                rows = await cursor.fetchall()
            events = [_row_to_event(row) for row in rows]
            return {"events": events, "count": len(events)}
        except Exception as e:
            logger.exception("list_upcoming_events failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def update_event(
        event_id: int,
        title: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        all_day: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update fields on an event."""
        try:
            db = await get_database()
            fields = []
            params: list[Any] = []

            if title is not None:
                if not title.strip():
                    return {"status": "error", "error": "title cannot be empty"}
                fields.append("title = ?")
                params.append(title)
            if start is not None:
                fields.append('"start" = ?')
                params.append(start)
            if end is not None:
                fields.append('"end" = ?')
                params.append(end)
            if location is not None:
                fields.append("location = ?")
                params.append(location)
            if description is not None:
                fields.append("description = ?")
                params.append(description)
            if all_day is not None:
                fields.append("all_day = ?")
                params.append(int(bool(all_day)))

            if not fields:
                return {"status": "error", "error": "no fields to update"}

            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(int(event_id))

            cursor = await db.execute(
                f"UPDATE events SET {', '.join(fields)} WHERE id = ?",
                params,
            )
            await db.commit()
            if cursor.rowcount == 0:
                return {"status": "error", "error": "event not found"}
            event = await _fetch_event(db, event_id)
            return {"status": "ok", "event": event}
        except Exception as e:
            logger.exception("update_event failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def delete_event(event_id: int) -> Dict[str, Any]:
        """Delete an event by ID."""
        try:
            db = await get_database()
            cursor = await db.execute("DELETE FROM events WHERE id = ?", (int(event_id),))
            await db.commit()
            if cursor.rowcount == 0:
                return {"status": "error", "error": "event not found"}
            return {"status": "ok", "deleted": int(event_id)}
        except Exception as e:
            logger.exception("delete_event failed")
            return {"status": "error", "error": str(e)}
