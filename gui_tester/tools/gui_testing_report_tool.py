"""Tooling for GUI tester note-taking and final report submission."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


def _utc_timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class NoteRecord:
    note_number: int
    note_path: Path
    screenshot_path: Path | None
    note: str
    created_at: str


class _GuiTestingReportState:
    def __init__(self, env, run_dir: Path):
        self.env = env
        self.run_dir = run_dir
        self.tool_calls_dir = run_dir / "tool_calls"
        self.notes_dir = run_dir / "notes"
        self.screenshots_dir = run_dir / "screenshots"
        self.tool_calls_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self.tool_call_counter = 0
        self.note_counter = 0
        self.notes: list[NoteRecord] = []
        self.final_report_path: Path | None = None

    def next_tool_call_path(self, action: str) -> Path:
        self.tool_call_counter += 1
        return self.tool_calls_dir / f"{self.tool_call_counter:03d}_{action}.json"

    def save_tool_call_record(self, action: str, payload: dict) -> Path:
        record_path = self.next_tool_call_path(action)
        payload_to_write = {
            "timestamp": _utc_timestamp(),
            "action": action,
            **payload,
        }
        record_path.write_text(json.dumps(payload_to_write, indent=2), encoding="utf-8")
        return record_path

    def save_note(self, note: str, include_screenshot: bool) -> NoteRecord:
        self.note_counter += 1
        note_number = self.note_counter
        timestamp = _utc_timestamp()

        screenshot_path: Path | None = None
        if include_screenshot:
            image_bytes, _mime_type = self.env.capture_screenshot()
            screenshot_path = self.screenshots_dir / f"screenshot_{note_number:03d}.png"
            screenshot_path.write_bytes(image_bytes)

        note_path = self.notes_dir / f"note_{note_number:03d}.md"
        screenshot_section = ""
        if screenshot_path is not None:
            rel_screenshot = Path(os.path.relpath(screenshot_path, start=note_path.parent))
            screenshot_section = f"\n## Screenshot\n\n![Screenshot]({rel_screenshot.as_posix()})\n"

        note_body = (
            f"# Note {note_number:03d}\n\n"
            f"- Created: {timestamp}\n"
            f"- Screenshot attached: {'yes' if screenshot_path else 'no'}\n\n"
            f"## Observation\n\n{note.strip()}\n"
            f"{screenshot_section}"
        )
        note_path.write_text(note_body, encoding="utf-8")

        record = NoteRecord(
            note_number=note_number,
            note_path=note_path,
            screenshot_path=screenshot_path,
            note=note.strip(),
            created_at=timestamp,
        )
        self.notes.append(record)
        return record

    def save_final_report(
        self,
        summary_of_task: str,
        results: str,
        important_findings: str | None,
        suggestions: str | None,
        other_notes: str | None,
    ) -> Path:
        report_path = self.run_dir / "final_report.md"
        note_links = []
        for note in self.notes:
            rel_note = note.note_path.relative_to(report_path.parent)
            note_links.append(f"- [Note {note.note_number:03d}]({rel_note.as_posix()})")

        important_findings_text = important_findings.strip() if important_findings else "None provided."
        suggestions_text = suggestions.strip() if suggestions else "None provided."
        other_notes_text = other_notes.strip() if other_notes else "None provided."
        linked_notes_text = "\n".join(note_links) if note_links else "- No notes were saved during this run."

        report_body = (
            "# GUI Testing Report\n\n"
            f"- Generated: {_utc_timestamp()}\n"
            f"- Run directory: `{self.run_dir}`\n\n"
            "## Summary Of Task\n\n"
            f"{summary_of_task.strip()}\n\n"
            "## Results\n\n"
            f"{results.strip()}\n\n"
            "## Important Findings\n\n"
            f"{important_findings_text}\n\n"
            "## Suggestions\n\n"
            f"{suggestions_text}\n\n"
            "## Other Notes\n\n"
            f"{other_notes_text}\n\n"
            "## Linked Notes\n\n"
            f"{linked_notes_text}\n"
        )
        report_path.write_text(report_body, encoding="utf-8")
        self.final_report_path = report_path
        return report_path


class GuiTestingReportArgs(BaseModel):
    action: str = Field(
        ...,
        description="Action to perform. One of: log_note, submit_final_report.",
    )
    note: Optional[str] = Field(
        None,
        description="The note text to save when action is log_note.",
    )
    include_screenshot: bool = Field(
        False,
        description="When true and action is log_note, capture and attach a screenshot.",
    )
    summary_of_task: Optional[str] = Field(
        None,
        description="Summary of the assigned GUI testing task for submit_final_report.",
    )
    results: Optional[str] = Field(
        None,
        description="Observed testing results for submit_final_report.",
    )
    important_findings: Optional[str] = Field(
        None,
        description="Important bugs, issues, or findings for submit_final_report.",
    )
    suggestions: Optional[str] = Field(
        None,
        description="Optional follow-up suggestions for submit_final_report.",
    )
    other_notes: Optional[str] = Field(
        None,
        description="Optional additional notes or blockers for submit_final_report.",
    )


def build_tool(env, run_dir: Path) -> tuple[StructuredTool, _GuiTestingReportState]:
    """Create the report tool and expose state for the wrapper to inspect."""
    state = _GuiTestingReportState(env=env, run_dir=run_dir)

    def gui_testing_report_tool(
        action: str,
        note: Optional[str] = None,
        include_screenshot: bool = False,
        summary_of_task: Optional[str] = None,
        results: Optional[str] = None,
        important_findings: Optional[str] = None,
        suggestions: Optional[str] = None,
        other_notes: Optional[str] = None,
    ) -> str:
        if action == "log_note":
            if not note or not note.strip():
                return json.dumps({"success": False, "error": "note is required for log_note"})

            note_record = state.save_note(note=note, include_screenshot=include_screenshot)
            tool_record_path = state.save_tool_call_record(
                "log_note",
                {
                    "note_path": str(note_record.note_path),
                    "screenshot_path": str(note_record.screenshot_path) if note_record.screenshot_path else None,
                    "include_screenshot": include_screenshot,
                    "note_preview": note_record.note,
                },
            )
            return json.dumps(
                {
                    "success": True,
                    "result": f"Saved note {note_record.note_number:03d}",
                    "note_path": str(note_record.note_path),
                    "screenshot_path": str(note_record.screenshot_path) if note_record.screenshot_path else None,
                    "tool_call_record_path": str(tool_record_path),
                }
            )

        if action == "submit_final_report":
            if not summary_of_task or not summary_of_task.strip():
                return json.dumps({"success": False, "error": "summary_of_task is required for submit_final_report"})
            if not results or not results.strip():
                return json.dumps({"success": False, "error": "results is required for submit_final_report"})

            report_path = state.save_final_report(
                summary_of_task=summary_of_task,
                results=results,
                important_findings=important_findings,
                suggestions=suggestions,
                other_notes=other_notes,
            )
            tool_record_path = state.save_tool_call_record(
                "submit_final_report",
                {
                    "report_path": str(report_path),
                    "summary_of_task": summary_of_task,
                    "results": results,
                    "important_findings": important_findings,
                    "suggestions": suggestions,
                    "other_notes": other_notes,
                },
            )
            return json.dumps(
                {
                    "success": True,
                    "result": f"Submitted final report at {report_path}",
                    "report_path": str(report_path),
                    "tool_call_record_path": str(tool_record_path),
                    "terminal": True,
                }
            )

        return json.dumps(
            {
                "success": False,
                "error": "Unsupported action. Use log_note or submit_final_report.",
            }
        )

    tool = StructuredTool.from_function(
        func=gui_testing_report_tool,
        name="gui_testing_report_tool",
        description=(
            "Save important testing notes and submit the final GUI testing report. Use "
            "action=log_note to log meaningful findings, blockers, visual evidence, or "
            "important page-level conclusions. Do not use notes for routine step-by-step "
            "narration. Finish every run with action=submit_final_report. Even if blocked, "
            "submit a report describing what you tested and what stopped further progress."
        ),
        args_schema=GuiTestingReportArgs,
    )
    return tool, state
