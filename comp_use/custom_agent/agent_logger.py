# agent_logger.py
# Structured file logger for the custom computer use agent.
#
# Usage:
#   logger = AgentLogger("/path/to/output/run_20260409_143201.txt")
#   logger.log_run_start(task="...", model="...", env_type="playwright", ...)
#   logger.log_step_start(1)
#   logger.log_screenshot_message(mime_type="image/png")
#   logger.log_tool_call("computer_use", args={...}, result_raw="...")
#   logger.log_new_messages([ai_msg, tool_msg])
#   logger.log_run_end(all_messages)
#   logger.close()

import json
import os
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Message sanitization helpers
# ---------------------------------------------------------------------------

def _sanitize_human_message_content(content: Any) -> str:
    """Return a readable representation of a HumanMessage content block."""
    if isinstance(content, str):
        return f'"{content}"'
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(f'text: "{item}"')
            elif isinstance(item, dict):
                if item.get("type") == "image":
                    mime = item.get("mime_type", "image/?")
                    parts.append(f"<image_data_removed> ({mime})")
                elif item.get("type") == "text":
                    parts.append(f'text: "{item.get("text", "")}"')
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return " | ".join(parts)
    return str(content)


def _sanitize_tool_result(content: Any) -> str:
    """Strip screenshot base64 from tool result strings (mirrors format_tool_output_for_log)."""
    if not isinstance(content, str):
        return str(content)
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return content
    result = parsed.get("result")
    if isinstance(result, str) and result.startswith("data:image/png;base64,"):
        parsed["result"] = "<screenshot_data_removed>"
        return json.dumps(parsed, indent=2)
    # Pretty-print if it parsed cleanly
    return json.dumps(parsed, indent=2)


def _format_tool_args(args: dict) -> list[str]:
    """Return a list of lines describing tool args, with thought on its own line."""
    lines = []
    thought = args.get("thought")
    if thought:
        lines.append(f"  Thought : {thought}")
    for key, val in args.items():
        if key == "thought":
            continue
        if val is None:
            continue
        lines.append(f"  {key:8}: {val}")
    return lines


# ---------------------------------------------------------------------------
# AgentLogger
# ---------------------------------------------------------------------------

class AgentLogger:
    """
    Writes a structured plain-text log file for a computer use agent run.

    All methods are safe to call when disabled (log_path=None) — they become no-ops.
    """

    def __init__(self, log_path: str | None):
        self._enabled = log_path is not None
        self._file = None
        if self._enabled:
            os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
            self._file = open(log_path, "w", encoding="utf-8", buffering=1)  # line-buffered

    # ------------------------------------------------------------------
    # Internal write helpers
    # ------------------------------------------------------------------

    def _write(self, text: str):
        if self._file:
            self._file.write(text)

    def _writeln(self, text: str = ""):
        self._write(text + "\n")

    def _divider(self, char: str = "=", width: int = 80):
        self._writeln(char * width)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_run_start(
        self,
        task: str,
        model: str,
        env_type: str,
        log_path: str | None = None,
        start_url: str | None = None,
        headless: bool = False,
        starting_messages: list | None = None,
    ):
        if not self._enabled:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._divider()
        self._writeln("  COMPUTER USE AGENT LOG")
        self._writeln(f"  Run started : {now}")
        self._writeln(f"  Task        : {task}")
        self._writeln(f"  Model       : {model}")
        self._writeln(f"  Environment : {env_type}")
        if start_url:
            self._writeln(f"  Start URL   : {start_url}")
        if env_type == "playwright":
            self._writeln(f"  Headless    : {headless}")
        if log_path:
            self._writeln(f"  Log file    : {log_path}")
        self._divider()
        if starting_messages:
            self._writeln("\n  STARTING MESSAGES")
            self._divider("-")
            for i, msg in enumerate(starting_messages, 1):
                self._write(f"\n[{i}] ")
                self._log_single_message(msg)
            self._writeln()
        self._writeln()

    def log_step_start(self, step: int):
        if not self._enabled:
            return
        self._writeln(f"\n{'=' * 40}")
        self._writeln(f"  STEP {step}")
        self._writeln(f"{'=' * 40}")

    def log_screenshot(self, mime_type: str = "image/png"):
        """Log that a screenshot was captured (without the data)."""
        if not self._enabled:
            return
        self._writeln(f"\n[Screenshot captured]")
        self._writeln(f"  <image_data_removed> ({mime_type})")

    def log_tool_call(self, name: str, args: dict, result_raw: Any):
        """Log a tool call with its thought, arguments, and sanitized result."""
        if not self._enabled:
            return
        self._writeln(f"\n[Tool call: {name}]")
        for line in _format_tool_args(args):
            self._writeln(line)
        sanitized = _sanitize_tool_result(result_raw)
        self._writeln(f"\n  Result:")
        for line in sanitized.splitlines():
            self._writeln(f"    {line}")

    def log_new_messages(self, messages: list):
        """
        Log messages that were just added to the agent state this step.
        Images are replaced with a placeholder, large base64 data is stripped.
        """
        if not self._enabled or not messages:
            return
        self._writeln("\n[New messages this step]")
        for msg in messages:
            self._log_single_message(msg)

    def log_run_end(self, all_messages: list):
        """Dump the complete message history at the end of the run."""
        if not self._enabled:
            return
        self._writeln()
        self._divider()
        self._writeln("  COMPLETE MESSAGE HISTORY")
        self._divider()
        for i, msg in enumerate(all_messages, 1):
            self._write(f"\n[{i}] ")
            self._log_single_message(msg)
        self._writeln()
        self._divider()
        self._writeln(f"  Run ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._divider()

    def close(self):
        if self._file:
            self._file.flush()
            self._file.close()
            self._file = None

    # ------------------------------------------------------------------
    # Internal: single message formatting
    # ------------------------------------------------------------------

    def _log_single_message(self, msg):
        """Write one message's log representation."""
        # Import here to avoid circular imports — langchain is always available
        # when the agent is running.
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

        if isinstance(msg, SystemMessage):
            self._writeln(f"SystemMessage:")
            for line in str(msg.content).splitlines():
                self._writeln(f"  {line}")

        elif isinstance(msg, HumanMessage):
            summary = _sanitize_human_message_content(msg.content)
            self._writeln(f"HumanMessage: {summary}")

        elif isinstance(msg, AIMessage):
            # Show text content (if any)
            text = msg.content if isinstance(msg.content, str) else ""
            if text:
                self._writeln(f"AIMessage: {text}")
            else:
                self._writeln(f"AIMessage:")
            # Show tool calls
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    self._writeln(f"  [tool_call: {tc['name']}]  id={tc['id']}")
                    for line in _format_tool_args(tc.get("args", {})):
                        self._writeln(f"  {line}")

        elif isinstance(msg, ToolMessage):
            sanitized = _sanitize_tool_result(msg.content)
            self._writeln(f"ToolMessage [id={msg.tool_call_id}]:")
            for line in sanitized.splitlines():
                self._writeln(f"  {line}")

        else:
            self._writeln(f"{type(msg).__name__}: {msg}")
