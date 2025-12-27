from __future__ import annotations


def _note_writer_text() -> str:
    return "Write clear, concise, searchable personal notes."


def _task_planner_text() -> str:
    return (
        "Turn goals into actionable tasks with priorities, due dates, and tags. "
        "Keep tasks small and well-scoped."
    )


def _meeting_summary_text() -> str:
    return (
        "Summarize a meeting into key decisions, action items, and follow-ups. "
        "Create tasks for each action item."
    )


def register_prompts(mcp) -> None:
    @mcp.resource("lifeos://prompts/note_writer")
    def note_writer_prompt():
        return {"prompt": _note_writer_text()}

    @mcp.resource("lifeos://prompts/task_planner")
    def task_planner_prompt():
        return {"prompt": _task_planner_text()}

    @mcp.resource("lifeos://prompts/meeting_summary")
    def meeting_summary_prompt():
        return {"prompt": _meeting_summary_text()}

    @mcp.prompt(name="note_writer", title="Note Writer", description=_note_writer_text())
    def note_writer(notes: str = "", audience: str = "self"):
        details = ""
        if notes.strip():
            details = f"\nNotes:\n{notes.strip()}"
        return [
            {"role": "system", "content": "You are a LifeOS writing assistant."},
            {
                "role": "user",
                "content": f"{_note_writer_text()}\nAudience: {audience}{details}",
            },
        ]

    @mcp.prompt(name="task_planner", title="Task Planner", description=_task_planner_text())
    def task_planner(goals: str = "", constraints: str = ""):
        goal_text = goals.strip() or "No specific goals provided."
        constraint_text = constraints.strip()
        if constraint_text:
            constraint_text = f"\nConstraints: {constraint_text}"
        return [
            {"role": "system", "content": "You are a LifeOS planning assistant."},
            {
                "role": "user",
                "content": f"{_task_planner_text()}\nGoals: {goal_text}{constraint_text}",
            },
        ]

    @mcp.prompt(
        name="meeting_summary",
        title="Meeting Summary",
        description=_meeting_summary_text(),
    )
    def meeting_summary(transcript: str = "", attendees: str = ""):
        transcript_text = transcript.strip() or "No transcript provided."
        attendee_text = attendees.strip()
        if attendee_text:
            attendee_text = f"\nAttendees: {attendee_text}"
        return [
            {"role": "system", "content": "You are a LifeOS meeting assistant."},
            {
                "role": "user",
                "content": (
                    f"{_meeting_summary_text()}{attendee_text}\nTranscript:\n{transcript_text}"
                ),
            },
        ]
