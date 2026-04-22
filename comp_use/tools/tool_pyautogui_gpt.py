"""
PyAutoGUI computer use tool for GPT models.

Exports a module-level computer_use tool.

Coordinate system: raw screen pixel coordinates.
GPT outputs pixel coordinates directly from the screenshot, which is a
full-screen capture — so coordinates map 1:1 to screen pixels.
"""

import json
import time as _time
from typing import List, Optional

import pyautogui
from langchain.tools import tool
from pydantic import BaseModel, Field


class PyAutoGUIGPTArgs(BaseModel):
    """Arguments for the computer_use tool (GPT / pixel coordinate variant)."""

    thought: str = Field(
        ...,
        description="Your reasoning about the current state and what action to take next.",
    )
    action: str = Field(
        ...,
        description=(
            "Action to perform. One of: click, double_click, right_click, scroll, "
            "type, keypress, move, drag, wait, terminate, fail."
        ),
    )
    x: Optional[float] = Field(
        None,
        description=(
            "Screen pixel x-coordinate. These are raw screen pixels matching the "
            "screenshot dimensions. Required for: click, double_click, right_click, "
            "move, drag, scroll."
        ),
    )
    y: Optional[float] = Field(
        None,
        description=(
            "Screen pixel y-coordinate. These are raw screen pixels matching the "
            "screenshot dimensions. Required for: click, double_click, right_click, "
            "move, drag, scroll."
        ),
    )
    target_x: Optional[float] = Field(
        None,
        description="Pixel x-coordinate of the drag destination. Required for: drag.",
    )
    target_y: Optional[float] = Field(
        None,
        description="Pixel y-coordinate of the drag destination. Required for: drag.",
    )
    text: Optional[str] = Field(
        None,
        description="Text to type. Required for: type.",
    )
    keys: Optional[List[str]] = Field(
        None,
        description=(
            "List of keys to press sequentially (not as a chord). "
            "Required for: keypress. Example: [\"ctrl\", \"c\"] or [\"enter\"]."
        ),
    )
    direction: Optional[str] = Field(
        None,
        description="Scroll direction: 'up' or 'down'. Required for: scroll.",
    )
    clicks: Optional[int] = Field(
        None,
        description="Number of scroll clicks. Defaults to 3 if omitted. Used by: scroll.",
    )
    ms: Optional[float] = Field(
        None,
        description="Duration in milliseconds to wait. Required for: wait.",
    )
    status: Optional[str] = Field(
        None,
        description="Completion status message. Optional for: terminate.",
    )
    message: Optional[str] = Field(
        None,
        description="Failure reason. Optional for: fail.",
    )


@tool(args_schema=PyAutoGUIGPTArgs)
def computer_use(
    thought: str,
    action: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    target_x: Optional[float] = None,
    target_y: Optional[float] = None,
    text: Optional[str] = None,
    keys: Optional[List[str]] = None,
    direction: Optional[str] = None,
    clicks: Optional[int] = None,
    ms: Optional[float] = None,
    status: Optional[str] = None,
    message: Optional[str] = None,
) -> str:
    """Control the desktop with mouse and keyboard using raw screen pixel coordinates.

    Coordinates are raw screen pixels that map directly to the screenshot dimensions.
    GPT outputs pixel coordinates from the screenshot image — pass them through unchanged.

    Returns a JSON string:
        {"success": true, "result": "<description>"}
        {"success": false, "error": "<error message>"}

    Terminal actions include "terminal": true so the agent loop can detect completion:
        {"success": true, "result": "...", "terminal": true}
    """
    # Log all non-None parameters for debugging
    params = {k: v for k, v in {
        "x": x, "y": y, "target_x": target_x, "target_y": target_y,
        "text": text, "keys": keys, "direction": direction,
        "clicks": clicks, "ms": ms, "status": status, "message": message,
    }.items() if v is not None}
    print(f"  [tool_pyautogui_gpt] action={action} params={params}")

    try:
        if action == "click":
            if x is None or y is None:
                raise ValueError("x and y are required for click")
            pyautogui.click(int(x), int(y))
            return json.dumps({"success": True, "result": f"Clicked at ({x}, {y})"})

        elif action == "double_click":
            if x is None or y is None:
                raise ValueError("x and y are required for double_click")
            pyautogui.doubleClick(int(x), int(y))
            return json.dumps({"success": True, "result": f"Double-clicked at ({x}, {y})"})

        elif action == "right_click":
            if x is None or y is None:
                raise ValueError("x and y are required for right_click")
            pyautogui.rightClick(int(x), int(y))
            return json.dumps({"success": True, "result": f"Right-clicked at ({x}, {y})"})

        elif action == "scroll":
            if x is None or y is None:
                raise ValueError("x and y are required for scroll")
            if not direction:
                raise ValueError("direction is required for scroll")
            n = int(clicks or 3)
            amount = n if direction == "up" else -n
            pyautogui.scroll(amount, x=int(x), y=int(y))
            return json.dumps({"success": True, "result": f"Scrolled {direction} {n} clicks at ({x}, {y})"})

        elif action == "move":
            if x is None or y is None:
                raise ValueError("x and y are required for move")
            pyautogui.moveTo(int(x), int(y), duration=0.2)
            return json.dumps({"success": True, "result": f"Moved mouse to ({x}, {y})"})

        elif action == "drag":
            if x is None or y is None or target_x is None or target_y is None:
                raise ValueError("x, y, target_x, and target_y are required for drag")
            pyautogui.moveTo(int(x), int(y), duration=0.2)
            pyautogui.dragTo(int(target_x), int(target_y), duration=0.3, button="left")
            return json.dumps({"success": True, "result": f"Dragged from ({x}, {y}) to ({target_x}, {target_y})"})

        elif action == "type":
            if text is None:
                raise ValueError("text is required for type")
            pyautogui.write(text, interval=0.05)
            return json.dumps({"success": True, "result": f"Typed text"})

        elif action == "keypress":
            if not keys:
                raise ValueError("keys is required for keypress")
            for key in keys:
                pyautogui.press(key)
            return json.dumps({"success": True, "result": f"Pressed keys: {keys}"})

        elif action == "wait":
            duration_ms = float(ms or 1000)
            _time.sleep(duration_ms / 1000)
            return json.dumps({"success": True, "result": f"Waited {duration_ms}ms"})

        elif action == "terminate":
            return json.dumps({
                "success": True,
                "result": f"Task complete: {status or 'done'}",
                "terminal": True,
            })

        elif action == "fail":
            return json.dumps({
                "success": False,
                "result": f"Task failed: {message or 'unknown error'}",
                "terminal": True,
            })

        else:
            raise ValueError(f"Unsupported action: '{action}'")

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
