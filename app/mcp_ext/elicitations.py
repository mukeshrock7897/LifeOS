from __future__ import annotations


def register_elicitations(mcp) -> None:
    @mcp.resource("lifeos://elicitations/note")
    def note_elicitation():
        return {"questions": ["What is the main idea?", "Any follow-up actions?"]}

    @mcp.resource("lifeos://elicitations/task")
    def task_elicitation():
        return {
            "questions": [
                "What is the desired outcome?",
                "Is there a due date or priority?",
                "Any dependencies or blockers?",
            ]
        }

    @mcp.resource("lifeos://elicitations/event")
    def event_elicitation():
        return {
            "questions": [
                "Where is the event?",
                "Is it all-day or time-specific?",
                "Any preparation notes or agenda?",
            ]
        }
