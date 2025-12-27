from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.db.sqlite import get_database
from app.utils.logger import logger
from app.utils.tags import tags_to_list

_MAX_TEMPLATE_RESULTS = 100
_VALID_TASK_STATUSES = {"pending", "in_progress", "done", "canceled"}


def _row_to_note(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "tags": tags_to_list(row["tags"]),
        "pinned": bool(row["pinned"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"] or row["created_at"],
    }


def _row_to_event(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "start": row["start"],
        "end": row["end"],
        "location": row["location"],
        "description": row["description"],
        "all_day": bool(row["all_day"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"] or row["created_at"],
    }


def _row_to_task(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "priority": row["priority"],
        "due_at": row["due_at"],
        "tags": tags_to_list(row["tags"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"] or row["created_at"],
    }


def register_resources(mcp) -> None:
    @mcp.resource("lifeos://notes/recent")
    async def recent_notes() -> Dict[str, Any]:
        """Return 5 most recent notes.

        If SQLite is not available, returns an error payload (does not crash server).
        """
        try:
            db = await get_database()
            async with db.execute(
                "SELECT * FROM notes "
                "ORDER BY created_at DESC "
                "LIMIT 5"
            ) as cursor:
                rows = await cursor.fetchall()
            notes = [_row_to_note(row) for row in rows]
            return {"notes": notes}
        except Exception as e:
            logger.exception("recent_notes failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://events/upcoming")
    async def upcoming_events() -> Dict[str, Any]:
        """Return upcoming events (next 5)."""
        try:
            db = await get_database()
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            async with db.execute(
                'SELECT * FROM events WHERE "start" >= ? ORDER BY "start" LIMIT 5',
                (today,),
            ) as cursor:
                rows = await cursor.fetchall()
            events = [_row_to_event(row) for row in rows]
            return {"events": events}
        except Exception as e:
            logger.exception("upcoming_events failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://tasks/summary")
    async def tasks_summary() -> Dict[str, Any]:
        """Return task counts and next due tasks."""
        try:
            db = await get_database()
            async with db.execute(
                "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"
            ) as cursor:
                rows = await cursor.fetchall()
            counts = {row["status"]: row["count"] for row in rows}

            async with db.execute(
                "SELECT * FROM tasks "
                "WHERE due_at IS NOT NULL "
                "ORDER BY due_at LIMIT 5"
            ) as cursor:
                due_rows = await cursor.fetchall()
            due_tasks = [_row_to_task(row) for row in due_rows]

            return {"counts": counts, "due_soon": due_tasks}
        except Exception as e:
            logger.exception("tasks_summary failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://stats/summary")
    async def stats_summary() -> Dict[str, Any]:
        """Return basic counts for notes, events, and tasks."""
        try:
            db = await get_database()
            async with db.execute("SELECT COUNT(*) as count FROM notes") as cursor:
                note_count = (await cursor.fetchone())["count"]
            async with db.execute("SELECT COUNT(*) as count FROM events") as cursor:
                event_count = (await cursor.fetchone())["count"]
            async with db.execute("SELECT COUNT(*) as count FROM tasks") as cursor:
                task_count = (await cursor.fetchone())["count"]
            return {
                "notes": note_count,
                "events": event_count,
                "tasks": task_count,
            }
        except Exception as e:
            logger.exception("stats_summary failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://notes/{note_id}")
    async def note_by_id(note_id: str) -> Dict[str, Any]:
        """Return a single note by ID."""
        try:
            note_int = int(note_id)
        except ValueError:
            return {"error": "note_id must be an integer"}
        try:
            db = await get_database()
            async with db.execute("SELECT * FROM notes WHERE id = ?", (note_int,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return {"error": "note not found"}
            return {"note": _row_to_note(row)}
        except Exception as e:
            logger.exception("note_by_id failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://events/{event_id}")
    async def event_by_id(event_id: str) -> Dict[str, Any]:
        """Return a single event by ID."""
        try:
            event_int = int(event_id)
        except ValueError:
            return {"error": "event_id must be an integer"}
        try:
            db = await get_database()
            async with db.execute("SELECT * FROM events WHERE id = ?", (event_int,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return {"error": "event not found"}
            return {"event": _row_to_event(row)}
        except Exception as e:
            logger.exception("event_by_id failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://tasks/{task_id}")
    async def task_by_id(task_id: str) -> Dict[str, Any]:
        """Return a single task by ID."""
        try:
            task_int = int(task_id)
        except ValueError:
            return {"error": "task_id must be an integer"}
        try:
            db = await get_database()
            async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_int,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return {"error": "task not found"}
            return {"task": _row_to_task(row)}
        except Exception as e:
            logger.exception("task_by_id failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://notes/tag/{tag}")
    async def notes_by_tag(tag: str) -> Dict[str, Any]:
        """Return notes with a tag."""
        try:
            db = await get_database()
            tag_value = tag.strip().lower()
            async with db.execute(
                "SELECT * FROM notes WHERE ',' || tags || ',' LIKE ? "
                "ORDER BY updated_at DESC LIMIT ?",
                (f"%,{tag_value},%", _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            notes = [_row_to_note(row) for row in rows]
            return {"notes": notes, "count": len(notes)}
        except Exception as e:
            logger.exception("notes_by_tag failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://notes/search/{query}")
    async def notes_search(query: str) -> Dict[str, Any]:
        """Search notes by title or content."""
        if not query.strip():
            return {"error": "query cannot be empty"}
        try:
            db = await get_database()
            pattern = f"%{query}%"
            async with db.execute(
                "SELECT * FROM notes WHERE "
                "(title LIKE ? COLLATE NOCASE OR content LIKE ? COLLATE NOCASE) "
                "ORDER BY updated_at DESC LIMIT ?",
                (pattern, pattern, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            notes = [_row_to_note(row) for row in rows]
            return {"notes": notes, "count": len(notes)}
        except Exception as e:
            logger.exception("notes_search failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://notes/range/{start}/{end}")
    async def notes_range(start: str, end: str) -> Dict[str, Any]:
        """Return notes created within a date/time range."""
        try:
            db = await get_database()
            async with db.execute(
                "SELECT * FROM notes WHERE created_at >= ? AND created_at <= ? "
                "ORDER BY created_at DESC LIMIT ?",
                (start, end, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            notes = [_row_to_note(row) for row in rows]
            return {"notes": notes, "count": len(notes)}
        except Exception as e:
            logger.exception("notes_range failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://events/range/{start}/{end}")
    async def events_range(start: str, end: str) -> Dict[str, Any]:
        """Return events overlapping a date/time range."""
        try:
            db = await get_database()
            async with db.execute(
                'SELECT * FROM events WHERE "start" <= ? AND "end" >= ? '
                'ORDER BY "start" LIMIT ?',
                (end, start, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            events = [_row_to_event(row) for row in rows]
            return {"events": events, "count": len(events)}
        except Exception as e:
            logger.exception("events_range failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://events/on/{date}")
    async def events_on(date: str) -> Dict[str, Any]:
        """Return events that start on a specific date."""
        try:
            db = await get_database()
            pattern = f"{date}%"
            async with db.execute(
                'SELECT * FROM events WHERE "start" LIKE ? ORDER BY "start" LIMIT ?',
                (pattern, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            events = [_row_to_event(row) for row in rows]
            return {"events": events, "count": len(events)}
        except Exception as e:
            logger.exception("events_on failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://events/search/{query}")
    async def events_search(query: str) -> Dict[str, Any]:
        """Search events by title, location, or description."""
        if not query.strip():
            return {"error": "query cannot be empty"}
        try:
            db = await get_database()
            pattern = f"%{query}%"
            async with db.execute(
                "SELECT * FROM events WHERE "
                "(title LIKE ? COLLATE NOCASE OR location LIKE ? COLLATE NOCASE "
                "OR description LIKE ? COLLATE NOCASE) "
                'ORDER BY "start" LIMIT ?',
                (pattern, pattern, pattern, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            events = [_row_to_event(row) for row in rows]
            return {"events": events, "count": len(events)}
        except Exception as e:
            logger.exception("events_search failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://tasks/status/{status}")
    async def tasks_by_status(status: str) -> Dict[str, Any]:
        """Return tasks by status."""
        normalized = status.strip().lower().replace(" ", "_")
        if normalized not in _VALID_TASK_STATUSES:
            return {"error": f"invalid status: {status}"}
        try:
            db = await get_database()
            async with db.execute(
                "SELECT * FROM tasks WHERE status = ? "
                "ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, "
                "due_at, priority DESC, updated_at DESC LIMIT ?",
                (normalized, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            tasks = [_row_to_task(row) for row in rows]
            return {"tasks": tasks, "count": len(tasks)}
        except Exception as e:
            logger.exception("tasks_by_status failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://tasks/tag/{tag}")
    async def tasks_by_tag(tag: str) -> Dict[str, Any]:
        """Return tasks with a tag."""
        try:
            db = await get_database()
            tag_value = tag.strip().lower()
            async with db.execute(
                "SELECT * FROM tasks WHERE ',' || tags || ',' LIKE ? "
                "ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, "
                "due_at, priority DESC, updated_at DESC LIMIT ?",
                (f"%,{tag_value},%", _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            tasks = [_row_to_task(row) for row in rows]
            return {"tasks": tasks, "count": len(tasks)}
        except Exception as e:
            logger.exception("tasks_by_tag failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://tasks/search/{query}")
    async def tasks_search(query: str) -> Dict[str, Any]:
        """Search tasks by title or description."""
        if not query.strip():
            return {"error": "query cannot be empty"}
        try:
            db = await get_database()
            pattern = f"%{query}%"
            async with db.execute(
                "SELECT * FROM tasks WHERE "
                "(title LIKE ? COLLATE NOCASE OR description LIKE ? COLLATE NOCASE) "
                "ORDER BY updated_at DESC LIMIT ?",
                (pattern, pattern, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            tasks = [_row_to_task(row) for row in rows]
            return {"tasks": tasks, "count": len(tasks)}
        except Exception as e:
            logger.exception("tasks_search failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://tasks/due/{start}/{end}")
    async def tasks_due_range(start: str, end: str) -> Dict[str, Any]:
        """Return tasks due within a date/time range."""
        try:
            db = await get_database()
            async with db.execute(
                "SELECT * FROM tasks WHERE due_at IS NOT NULL "
                "AND due_at >= ? AND due_at <= ? "
                "ORDER BY due_at LIMIT ?",
                (start, end, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            tasks = [_row_to_task(row) for row in rows]
            return {"tasks": tasks, "count": len(tasks)}
        except Exception as e:
            logger.exception("tasks_due_range failed")
            return {"error": str(e)}

    @mcp.resource("lifeos://tasks/priority/{priority}")
    async def tasks_by_priority(priority: str) -> Dict[str, Any]:
        """Return tasks by priority (1-5)."""
        try:
            priority_int = int(priority)
        except ValueError:
            return {"error": "priority must be an integer"}
        clamped = max(1, min(priority_int, 5))
        try:
            db = await get_database()
            async with db.execute(
                "SELECT * FROM tasks WHERE priority = ? "
                "ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, "
                "due_at, updated_at DESC LIMIT ?",
                (clamped, _MAX_TEMPLATE_RESULTS),
            ) as cursor:
                rows = await cursor.fetchall()
            tasks = [_row_to_task(row) for row in rows]
            return {"tasks": tasks, "count": len(tasks)}
        except Exception as e:
            logger.exception("tasks_by_priority failed")
            return {"error": str(e)}
