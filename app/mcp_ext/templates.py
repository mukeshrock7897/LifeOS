from __future__ import annotations


def register_templates(mcp) -> None:
    @mcp.resource("lifeos://templates/note")
    def note_template():
        return {
            "title": "<title>",
            "content": "<content>",
            "tags": ["tag1", "tag2"],
            "pinned": False,
        }

    @mcp.resource("lifeos://templates/event")
    def event_template():
        return {
            "title": "<title>",
            "start": "<ISO-8601>",
            "end": "<ISO-8601>",
            "location": "<location>",
            "description": "<details>",
            "all_day": False,
        }

    @mcp.resource("lifeos://templates/task")
    def task_template():
        return {
            "title": "<title>",
            "description": "<details>",
            "due_at": "<ISO-8601 or YYYY-MM-DD>",
            "priority": 3,
            "status": "pending",
            "tags": ["tag1", "tag2"],
        }
