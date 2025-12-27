from __future__ import annotations

import os
import base64
from pathlib import Path
from typing import Any, Dict, List

from app.config import settings
from app.utils.logger import logger
from app.utils.security import is_path_allowed
from app.utils.validators import normalize_path


def register_filesystem_tools(mcp) -> None:
    """Filesystem-related MCP tools (restricted to allowlisted directories)."""

    @mcp.tool()
    def search_files(
        query: str,
        root: str = ".",
        limit: int = settings.FILE_SEARCH_DEFAULT_LIMIT,
    ) -> Dict[str, Any]:
        """Search files by name under `root`.

        Security:
        - `root` must be within `ALLOWED_BASE_PATHS`.
        - scan is bounded by `limit` (capped at FILE_SEARCH_MAX_LIMIT).
        """
        try:
            root_path = normalize_path(root)

            if not is_path_allowed(root_path):
                return {
                    "status": "error",
                    "error": (
                        "root path is not allowed. Set ALLOWED_BASE_PATHS env var "
                        "to include the directories you want to scan."
                    ),
                }

            max_lim = max(1, int(settings.FILE_SEARCH_MAX_LIMIT))
            lim = max(1, min(int(limit), max_lim))

            matches: List[str] = []
            q = (query or "").lower()

            for dirpath, _, filenames in os.walk(str(root_path)):
                for filename in filenames:
                    if q in filename.lower():
                        matches.append(str(Path(dirpath) / filename))
                        if len(matches) >= lim:
                            logger.warning("Filesystem scan limit reached")
                            return {"files": matches, "truncated": True}

            return {"files": matches, "truncated": False}
        except Exception as e:
            logger.exception("search_files failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def list_dir(
        path: str = ".",
        limit: int = settings.FILE_LIST_MAX_LIMIT,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """List directory entries under an allowlisted path."""
        try:
            dir_path = normalize_path(path)

            if not is_path_allowed(dir_path):
                return {
                    "status": "error",
                    "error": (
                        "path is not allowed. Set ALLOWED_BASE_PATHS env var "
                        "to include the directories you want to access."
                    ),
                }

            if not dir_path.exists():
                return {"status": "error", "error": "path does not exist"}
            if not dir_path.is_dir():
                return {"status": "error", "error": "path is not a directory"}

            max_lim = max(1, int(settings.FILE_LIST_MAX_LIMIT))
            lim = max(1, min(int(limit), max_lim))

            entries: List[Dict[str, Any]] = []
            truncated = False
            with os.scandir(dir_path) as it:
                for entry in it:
                    if not include_hidden and entry.name.startswith("."):
                        continue
                    info = {
                        "name": entry.name,
                        "path": str(Path(entry.path)),
                        "type": "dir" if entry.is_dir(follow_symlinks=False) else "file",
                    }
                    if entry.is_file(follow_symlinks=False):
                        try:
                            info["size"] = entry.stat(follow_symlinks=False).st_size
                        except Exception:
                            info["size"] = None
                    entries.append(info)
                    if len(entries) >= lim:
                        truncated = True
                        break

            entries.sort(key=lambda item: (item["type"] != "dir", item["name"].lower()))
            return {"entries": entries, "count": len(entries), "truncated": truncated}
        except Exception as e:
            logger.exception("list_dir failed")
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def read_file(
        path: str,
        max_bytes: int = settings.FILE_READ_MAX_BYTES,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """Read a text file from an allowlisted path."""
        try:
            file_path = normalize_path(path)

            if not is_path_allowed(file_path):
                return {
                    "status": "error",
                    "error": (
                        "path is not allowed. Set ALLOWED_BASE_PATHS env var "
                        "to include the directories you want to access."
                    ),
                }

            if not file_path.exists():
                return {"status": "error", "error": "file does not exist"}
            if not file_path.is_file():
                return {"status": "error", "error": "path is not a file"}

            size = file_path.stat().st_size
            max_len = max(1, int(max_bytes))
            read_len = min(size, max_len)
            truncated = size > max_len

            with open(file_path, "rb") as handle:
                data = handle.read(read_len)

            if encoding.lower() == "base64":
                content = base64.b64encode(data).decode("ascii")
            else:
                content = data.decode(encoding, errors="replace")

            return {
                "path": str(file_path),
                "bytes_read": read_len,
                "truncated": truncated,
                "encoding": encoding,
                "content": content,
            }
        except Exception as e:
            logger.exception("read_file failed")
            return {"status": "error", "error": str(e)}
