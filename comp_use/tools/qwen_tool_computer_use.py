# qwen_tool_computer_use.py

# Import necessary libraries
from langchain.tools import tool
import json
import time
import pyautogui
from typing import Optional, List
from pydantic import BaseModel, Field


# Normalized coordinate space used by Qwen3-VL (0–1000 maps to full screen)
_NORM_RANGE = 1000


def _normalize_coordinates(norm_x: float, norm_y: float) -> tuple[int, int]:
    """Convert Qwen3-VL normalized (0–1000) coordinates to absolute screen pixels.

    Values outside 0–1000 are clamped after scaling and treated as a model
    formatting error — fix via prompting if this occurs frequently.
    """
    screen_width, screen_height = pyautogui.size()
    abs_x = int(norm_x / _NORM_RANGE * screen_width)
    abs_y = int(norm_y / _NORM_RANGE * screen_height)
    abs_x = max(0, min(abs_x, screen_width - 1))
    abs_y = max(0, min(abs_y, screen_height - 1))
    return abs_x, abs_y


class ComputerUseArgs(BaseModel):
    thought: str = Field(
        ...,
        description=(
            "Your reasoning: what you see on screen, what needs to be done next "
            "to accomplish the user goal, any mistakes from previous actions, or "
            "whether the goal is complete."
        ),
    )
    action: str = Field(
        ...,
        description=(
            "The action to perform. One of: mouse_move, left_click, right_click, "
            "double_click, type, key, scroll, wait, screenshot, terminate, fail."
        ),
    )
    coordinate: Optional[List[float]] = Field(
        None,
        description=(
            "[x, y] in Qwen3-VL normalized coordinate space (0–1000 inclusive). "
            "Required for: mouse_move, left_click, right_click, double_click. "
            "Optional for click actions (omit to act at current cursor position)."
        ),
    )
    text: Optional[str] = Field(
        None,
        description="Text to type. Required when action='type'.",
    )
    keys: Optional[List[str]] = Field(
        None,
        description="Keys to press as a hotkey combination. Required when action='key'.",
    )
    pixels: Optional[float] = Field(
        None,
        description="Scroll amount in pixels (positive = up, negative = down). Required when action='scroll'.",
    )
    time: Optional[float] = Field(
        None,
        description="Duration in seconds to wait. Required when action='wait'.",
    )
    status: Optional[str] = Field(
        None,
        description="Task completion status: 'success' or 'failure'. Required when action='terminate' or 'fail'.",
    )
    message: Optional[str] = Field(
        None,
        description="Explanation of why the task failed. Required when action='fail'.",
    )


@tool(args_schema=ComputerUseArgs)
def computer_use(
    thought: str,
    action: str,
    coordinate: Optional[List[float]] = None,
    text: Optional[str] = None,
    keys: Optional[List[str]] = None,
    pixels: Optional[float] = None,
    time: Optional[float] = None,
    status: Optional[str] = None,
    message: Optional[str] = None,
) -> str:
    """Control the computer with mouse and keyboard.

    Always include your reasoning in 'thought' before taking an action.
    Coordinates use Qwen3-VL normalized space (0–1000), where [0, 0] is the
    top-left of the screen and [1000, 1000] is the bottom-right.

    Returns a JSON string:
        {"success": true, "result": "<description of what happened>"}
        {"success": false, "error": "<error message>"}

    Terminal actions (terminate, fail) signal that the agent loop should stop.
    Check the 'terminal' key in the result to detect this:
        {"success": true, "result": "...", "terminal": true}
    """
    try:
        # ------------------------------------------------------------------
        # Mouse actions
        # ------------------------------------------------------------------
        if action == "mouse_move":
            coord = coordinate or [500, 500]
            abs_x, abs_y = _normalize_coordinates(coord[0], coord[1])
            pyautogui.moveTo(abs_x, abs_y, duration=0.3)
            return json.dumps({"success": True, "result": f"Moved mouse to ({abs_x}, {abs_y})"})

        elif action == "left_click":
            if coordinate:
                abs_x, abs_y = _normalize_coordinates(coordinate[0], coordinate[1])
                pyautogui.click(abs_x, abs_y)
                return json.dumps({"success": True, "result": f"Left-clicked at ({abs_x}, {abs_y})"})
            else:
                pyautogui.click()
                return json.dumps({"success": True, "result": "Left-clicked at current position"})

        elif action == "right_click":
            if coordinate:
                abs_x, abs_y = _normalize_coordinates(coordinate[0], coordinate[1])
                pyautogui.rightClick(abs_x, abs_y)
                return json.dumps({"success": True, "result": f"Right-clicked at ({abs_x}, {abs_y})"})
            else:
                pyautogui.rightClick()
                return json.dumps({"success": True, "result": "Right-clicked at current position"})

        elif action == "double_click":
            if coordinate:
                abs_x, abs_y = _normalize_coordinates(coordinate[0], coordinate[1])
                pyautogui.doubleClick(abs_x, abs_y)
                return json.dumps({"success": True, "result": f"Double-clicked at ({abs_x}, {abs_y})"})
            else:
                pyautogui.doubleClick()
                return json.dumps({"success": True, "result": "Double-clicked at current position"})

        # ------------------------------------------------------------------
        # Keyboard actions
        # ------------------------------------------------------------------
        elif action == "type":
            if not text:
                raise ValueError("Missing 'text' for action='type'")
            pyautogui.write(text, interval=0.05)
            return json.dumps({"success": True, "result": f"Typed: {text}"})

        elif action == "key":
            if not keys:
                raise ValueError("Missing 'keys' for action='key'")
            pyautogui.hotkey(*keys)
            return json.dumps({"success": True, "result": f"Pressed: {'+'.join(keys)}"})

        # ------------------------------------------------------------------
        # Scroll / wait / screenshot
        # ------------------------------------------------------------------
        elif action == "scroll":
            if pixels is None:
                raise ValueError("Missing 'pixels' for action='scroll'")
            pyautogui.scroll(int(pixels))
            return json.dumps({"success": True, "result": f"Scrolled {pixels} pixels"})

        elif action == "wait":
            duration = time if time is not None else 1.0
            import time as _time
            _time.sleep(duration)
            return json.dumps({"success": True, "result": f"Waited {duration} seconds"})

        elif action == "screenshot":
            # Screenshot is captured externally by the agent loop;
            # this action is a no-op signal that the next observation will be used.
            return json.dumps({"success": True, "result": "Screenshot requested"})

        # ------------------------------------------------------------------
        # Terminal actions
        # ------------------------------------------------------------------
        elif action == "terminate":
            task_status = status or "success"
            return json.dumps({
                "success": True,
                "result": f"Task {task_status}",
                "terminal": True,
            })

        elif action == "fail":
            fail_message = message or "Unknown error"
            return json.dumps({
                "success": True,
                "result": f"Task failed: {fail_message}",
                "terminal": True,
            })

        else:
            raise ValueError(f"Unsupported action: '{action}'")

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
