from __future__ import annotations

from typing import Any, Dict, Optional

from app.db.sqlite import get_database
from app.utils.logger import logger
from app.utils.tags import merge_tags, normalize_tags, remove_tags, tags_to_list


def _row_to_note(row) -> Dict[str, Any]:
    updated_at = row["updated_at"] or row["created_at"]
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "tags": tags_to_list(row["tags"]),
        "pinned": bool(row["pinned"]),
        "created_at": row["created_at"],
        "updated_at": updated_at,
    }


async def _fetch_note(db, note_id: int) -> Optional[Dict[str, Any]]:
    async with db.execute("SELECT * FROM notes WHERE id = ?", (int(note_id),)) as cursor:
        row = await cursor.fetchone()
    return _row_to_note(row) if row else None


def register_notes_tools(mcp) -> None:
    """Notes-related MCP tools."""

    @mcp.tool()
    async def create_note(
        title: str,
        content: str = "",
        tags: Optional[list[str] | str] = None,
        pinned: bool = False,
    ) -> Dict[str, Any]:
        """Create a new note."""
        if not title.strip():
            return {"status": "error", "error": "title cannot be empty"}
        try:
            db = await get_database()
            normalized_tags = normalize_tags(tags)
            cursor = await db.execute(
                "INSERT INTO notes (title, content, tags, pinned, updated_at) "
                "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (title, content, normalized_tags, int(bool(pinned))),
            )
            await db.commit()
            note = await _fetch_note(db, cursor.lastrowid)
            logger.info(f"Note created: {title}")
            return {"status": "ok", "note": note}
        except Exception as e:
            logger.exception("create_note failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def get_note(note_id: int) -> Dict[str, Any]:
        """Get a note by ID."""
        try:
            db = await get_database()
            note = await _fetch_note(db, note_id)
            if not note:
                return {"status": "error", "error": "note not found"}
            return {"note": note}
        except Exception as e:
            logger.exception("get_note failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def list_notes(
        limit: int = 50,
        offset: int = 0,
        tag: Optional[str] = None,
        pinned_only: bool = False,
    ) -> Dict[str, Any]:
        """List notes, optionally filtered by tag or pinned status."""
        try:
            db = await get_database()
            lim = max(1, min(int(limit), 200))
            off = max(0, int(offset))

            where_clauses = []
            params: list[Any] = []

            if pinned_only:
                where_clauses.append("pinned = 1")
            if tag:
                where_clauses.append("',' || tags || ',' LIKE ?")
                params.append(f"%,{tag.strip().lower()},%")

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            async with db.execute(
                "SELECT * FROM notes "
                f"{where_sql} "
                "ORDER BY pinned DESC, updated_at DESC, created_at DESC "
                "LIMIT ? OFFSET ?",
                (*params, lim, off),
            ) as cursor:
                rows = await cursor.fetchall()
            notes = [_row_to_note(row) for row in rows]
            return {"notes": notes, "count": len(notes), "next_offset": off + len(notes)}
        except Exception as e:
            logger.exception("list_notes failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def search_notes(
        query: str, limit: int = 20, in_content: bool = True
    ) -> Dict[str, Any]:
        """Search notes by title (and optionally content)."""
        if not query.strip():
            return {"status": "error", "error": "query cannot be empty"}
        try:
            db = await get_database()
            lim = max(1, min(int(limit), 100))
            pattern = f"%{query}%"
            if in_content:
                sql = (
                    "SELECT * FROM notes WHERE "
                    "(title LIKE ? COLLATE NOCASE OR content LIKE ? COLLATE NOCASE) "
                    "ORDER BY updated_at DESC LIMIT ?"
                )
                params = (pattern, pattern, lim)
            else:
                sql = (
                    "SELECT * FROM notes WHERE "
                    "title LIKE ? COLLATE NOCASE "
                    "ORDER BY updated_at DESC LIMIT ?"
                )
                params = (pattern, lim)
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
            notes = [_row_to_note(row) for row in rows]
            return {"results": notes}
        except Exception as e:
            logger.exception("search_notes failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def update_note(
        note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[list[str] | str] = None,
        pinned: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update fields on a note."""
        try:
            db = await get_database()
            fields = []
            params: list[Any] = []

            if title is not None:
                if not title.strip():
                    return {"status": "error", "error": "title cannot be empty"}
                fields.append("title = ?")
                params.append(title)
            if content is not None:
                fields.append("content = ?")
                params.append(content)
            if tags is not None:
                fields.append("tags = ?")
                params.append(normalize_tags(tags))
            if pinned is not None:
                fields.append("pinned = ?")
                params.append(int(bool(pinned)))

            if not fields:
                return {"status": "error", "error": "no fields to update"}

            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(int(note_id))

            cursor = await db.execute(
                f"UPDATE notes SET {', '.join(fields)} WHERE id = ?",
                params,
            )
            await db.commit()
            if cursor.rowcount == 0:
                return {"status": "error", "error": "note not found"}
            note = await _fetch_note(db, note_id)
            return {"status": "ok", "note": note}
        except Exception as e:
            logger.exception("update_note failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def delete_note(note_id: int) -> Dict[str, Any]:
        """Delete a note by ID."""
        try:
            db = await get_database()
            cursor = await db.execute("DELETE FROM notes WHERE id = ?", (int(note_id),))
            await db.commit()
            if cursor.rowcount == 0:
                return {"status": "error", "error": "note not found"}
            return {"status": "ok", "deleted": int(note_id)}
        except Exception as e:
            logger.exception("delete_note failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def add_note_tags(note_id: int, tags: list[str] | str) -> Dict[str, Any]:
        """Add tags to a note."""
        try:
            db = await get_database()
            note = await _fetch_note(db, note_id)
            if not note:
                return {"status": "error", "error": "note not found"}
            merged = merge_tags(",".join(note["tags"]), tags)
            await db.execute(
                "UPDATE notes SET tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (merged, int(note_id)),
            )
            await db.commit()
            updated = await _fetch_note(db, note_id)
            return {"status": "ok", "note": updated}
        except Exception as e:
            logger.exception("add_note_tags failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def remove_note_tags(note_id: int, tags: list[str] | str) -> Dict[str, Any]:
        """Remove tags from a note."""
        try:
            db = await get_database()
            note = await _fetch_note(db, note_id)
            if not note:
                return {"status": "error", "error": "note not found"}
            updated_tags = remove_tags(",".join(note["tags"]), tags)
            await db.execute(
                "UPDATE notes SET tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (updated_tags, int(note_id)),
            )
            await db.commit()
            updated = await _fetch_note(db, note_id)
            return {"status": "ok", "note": updated}
        except Exception as e:
            logger.exception("remove_note_tags failed")
            return {"status": "error", "error": str(e)}
