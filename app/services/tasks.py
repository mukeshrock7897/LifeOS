from __future__ import annotations

from typing import Any, Dict, Optional

from app.db.sqlite import get_database
from app.utils.logger import logger
from app.utils.tags import normalize_tags, tags_to_list

_VALID_STATUSES = {"pending", "in_progress", "done", "canceled"}


def _normalize_status(value: str) -> Optional[str]:
    status = value.strip().lower().replace(" ", "_")
    if status in _VALID_STATUSES:
        return status
    return None


def _row_to_task(row) -> Dict[str, Any]:
    updated_at = row["updated_at"] or row["created_at"]
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "priority": row["priority"],
        "due_at": row["due_at"],
        "tags": tags_to_list(row["tags"]),
        "created_at": row["created_at"],
        "updated_at": updated_at,
    }


async def _fetch_task(db, task_id: int) -> Optional[Dict[str, Any]]:
    async with db.execute("SELECT * FROM tasks WHERE id = ?", (int(task_id),)) as cursor:
        row = await cursor.fetchone()
    return _row_to_task(row) if row else None


def register_tasks_tools(mcp) -> None:
    """Task and to-do related MCP tools."""

    @mcp.tool()
    async def create_task(
        title: str,
        description: str = "",
        due_at: Optional[str] = None,
        priority: int = 3,
        tags: Optional[list[str] | str] = None,
        status: str = "pending",
    ) -> Dict[str, Any]:
        """Create a new task."""
        if not title.strip():
            return {"status": "error", "error": "title cannot be empty"}
        normalized_status = _normalize_status(status)
        if not normalized_status:
            return {
                "status": "error",
                "error": f"invalid status: {status}. Use {sorted(_VALID_STATUSES)}",
            }
        try:
            db = await get_database()
            clamped_priority = max(1, min(int(priority), 5))
            cursor = await db.execute(
                "INSERT INTO tasks (title, description, due_at, priority, tags, status, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    title,
                    description,
                    due_at if (due_at and due_at.strip()) else None,
                    clamped_priority,
                    normalize_tags(tags),
                    normalized_status,
                ),
            )
            await db.commit()
            task = await _fetch_task(db, cursor.lastrowid)
            return {"status": "ok", "task": task}
        except Exception as e:
            logger.exception("create_task failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def get_task(task_id: int) -> Dict[str, Any]:
        """Get a task by ID."""
        try:
            db = await get_database()
            task = await _fetch_task(db, task_id)
            if not task:
                return {"status": "error", "error": "task not found"}
            return {"task": task}
        except Exception as e:
            logger.exception("get_task failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def list_tasks(
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List tasks, optionally filtered by status."""
        try:
            db = await get_database()
            lim = max(1, min(int(limit), 200))
            off = max(0, int(offset))

            where_sql = ""
            params: list[Any] = []
            if status:
                normalized_status = _normalize_status(status)
                if not normalized_status:
                    return {
                        "status": "error",
                        "error": f"invalid status: {status}. Use {sorted(_VALID_STATUSES)}",
                    }
                where_sql = "WHERE status = ?"
                params.append(normalized_status)

            async with db.execute(
                "SELECT * FROM tasks "
                f"{where_sql} "
                "ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, "
                "due_at, priority DESC, updated_at DESC "
                "LIMIT ? OFFSET ?",
                (*params, lim, off),
            ) as cursor:
                rows = await cursor.fetchall()
            tasks = [_row_to_task(row) for row in rows]
            return {"tasks": tasks, "count": len(tasks), "next_offset": off + len(tasks)}
        except Exception as e:
            logger.exception("list_tasks failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def search_tasks(query: str, limit: int = 50) -> Dict[str, Any]:
        """Search tasks by title or description."""
        if not query.strip():
            return {"status": "error", "error": "query cannot be empty"}
        try:
            db = await get_database()
            lim = max(1, min(int(limit), 200))
            pattern = f"%{query}%"
            async with db.execute(
                "SELECT * FROM tasks WHERE "
                "(title LIKE ? COLLATE NOCASE OR description LIKE ? COLLATE NOCASE) "
                "ORDER BY updated_at DESC LIMIT ?",
                (pattern, pattern, lim),
            ) as cursor:
                rows = await cursor.fetchall()
            tasks = [_row_to_task(row) for row in rows]
            return {"results": tasks}
        except Exception as e:
            logger.exception("search_tasks failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def update_task(
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_at: Optional[str] = None,
        priority: Optional[int] = None,
        tags: Optional[list[str] | str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update fields on a task."""
        try:
            db = await get_database()
            fields = []
            params: list[Any] = []

            if title is not None:
                if not title.strip():
                    return {"status": "error", "error": "title cannot be empty"}
                fields.append("title = ?")
                params.append(title)
            if description is not None:
                fields.append("description = ?")
                params.append(description)
            if due_at is not None:
                due = due_at.strip()
                fields.append("due_at = ?")
                params.append(due if due else None)
            if priority is not None:
                fields.append("priority = ?")
                params.append(max(1, min(int(priority), 5)))
            if tags is not None:
                fields.append("tags = ?")
                params.append(normalize_tags(tags))
            if status is not None:
                normalized_status = _normalize_status(status)
                if not normalized_status:
                    return {
                        "status": "error",
                        "error": f"invalid status: {status}. Use {sorted(_VALID_STATUSES)}",
                    }
                fields.append("status = ?")
                params.append(normalized_status)

            if not fields:
                return {"status": "error", "error": "no fields to update"}

            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(int(task_id))

            cursor = await db.execute(
                f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?",
                params,
            )
            await db.commit()
            if cursor.rowcount == 0:
                return {"status": "error", "error": "task not found"}
            task = await _fetch_task(db, task_id)
            return {"status": "ok", "task": task}
        except Exception as e:
            logger.exception("update_task failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def complete_task(task_id: int) -> Dict[str, Any]:
        """Mark a task as done."""
        try:
            db = await get_database()
            cursor = await db.execute(
                "UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (int(task_id),),
            )
            await db.commit()
            if cursor.rowcount == 0:
                return {"status": "error", "error": "task not found"}
            task = await _fetch_task(db, task_id)
            return {"status": "ok", "task": task}
        except Exception as e:
            logger.exception("complete_task failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def delete_task(task_id: int) -> Dict[str, Any]:
        """Delete a task by ID."""
        try:
            db = await get_database()
            cursor = await db.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))
            await db.commit()
            if cursor.rowcount == 0:
                return {"status": "error", "error": "task not found"}
            return {"status": "ok", "deleted": int(task_id)}
        except Exception as e:
            logger.exception("delete_task failed")
            return {"status": "error", "error": str(e)}
