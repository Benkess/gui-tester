"""
Playwright computer use tool for Qwen3-VL models.

Exports build_tool(page) -> StructuredTool. All state is scoped to the closure
over the Playwright page object — no module-level singletons.

Coordinate system: Qwen3-VL normalized 0–1000 space.
[0, 0] is top-left, [1000, 1000] is bottom-right.
Coordinates are converted to viewport pixels before any Playwright call.
"""

import base64
import json
import time as _time
from typing import List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class PlaywrightQwenArgs(BaseModel):
    """Arguments for the computer_use tool (Qwen3-VL / normalized coordinate variant)."""

    thought: str = Field(
        ...,
        description="Your reasoning about the current state and what action to take next.",
    )
    action: str = Field(
        ...,
        description=(
            "Action to perform. One of: navigate, click, double_click, right_click, "
            "scroll, type, keypress, move, drag, fill, get_text, back, forward, "
            "screenshot, wait, terminate, fail."
        ),
    )
    x: Optional[float] = Field(
        None,
        description=(
            "Normalized coordinate in range 0–1000. [0,0] is top-left, [1000,1000] is "
            "bottom-right. Do NOT use pixel values. "
            "Required for: click, double_click, right_click, move, drag, scroll."
        ),
    )
    y: Optional[float] = Field(
        None,
        description=(
            "Normalized coordinate in range 0–1000. [0,0] is top-left, [1000,1000] is "
            "bottom-right. Do NOT use pixel values. "
            "Required for: click, double_click, right_click, move, drag, scroll."
        ),
    )
    target_x: Optional[float] = Field(
        None,
        description=(
            "Normalized x-coordinate (0–1000) of the drag destination. Required for: drag."
        ),
    )
    target_y: Optional[float] = Field(
        None,
        description=(
            "Normalized y-coordinate (0–1000) of the drag destination. Required for: drag."
        ),
    )
    url: Optional[str] = Field(
        None,
        description="URL to navigate to. Required for: navigate.",
    )
    text: Optional[str] = Field(
        None,
        description="Text to type or fill. Required for: type, fill.",
    )
    keys: Optional[List[str]] = Field(
        None,
        description=(
            "List of keys to press sequentially (not as a chord). "
            "Required for: keypress. Example: [\"ArrowDown\", \"Enter\"]."
        ),
    )
    direction: Optional[str] = Field(
        None,
        description="Scroll direction: 'up' or 'down'. Required for: scroll.",
    )
    pixels: Optional[float] = Field(
        None,
        description="Number of pixels to scroll. Required for: scroll.",
    )
    ms: Optional[float] = Field(
        None,
        description="Duration in milliseconds. Required for: wait.",
    )
    selector: Optional[str] = Field(
        None,
        description="CSS selector for the target element. Required for: fill, get_text.",
    )
    status: Optional[str] = Field(
        None,
        description="Completion status message. Optional for: terminate.",
    )
    message: Optional[str] = Field(
        None,
        description="Failure reason. Optional for: fail.",
    )


def _to_abs_coords(x: float, y: float, page) -> tuple:
    """Convert Qwen3-VL normalized 0–1000 coordinates to viewport pixel coordinates."""
    viewport = page.viewport_size  # {"width": W, "height": H}
    abs_x = max(0, min(int(x / 1000 * viewport["width"]),  viewport["width"]  - 1))
    abs_y = max(0, min(int(y / 1000 * viewport["height"]), viewport["height"] - 1))
    return abs_x, abs_y


def build_tool(page) -> StructuredTool:
    """
    Build a computer_use LangChain tool bound to the given Playwright page.

    Coordinates are in Qwen3-VL normalized space (0–1000) and are converted
    to viewport pixels before execution.

    Args:
        page: A Playwright sync Page object. The tool holds a reference to this
              page for the duration of the agent session.

    Returns:
        A StructuredTool with name "computer_use" that the agent can invoke.
    """

    def computer_use(
        thought: str,
        action: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        target_x: Optional[float] = None,
        target_y: Optional[float] = None,
        url: Optional[str] = None,
        text: Optional[str] = None,
        keys: Optional[List[str]] = None,
        direction: Optional[str] = None,
        pixels: Optional[float] = None,
        ms: Optional[float] = None,
        selector: Optional[str] = None,
        status: Optional[str] = None,
        message: Optional[str] = None,
    ) -> str:
        """Execute a computer use action in the browser."""
        try:
            if action == "navigate":
                if not url:
                    raise ValueError("url is required for navigate")
                page.goto(url)
                return json.dumps({"success": True, "result": f"Navigated to {url}"})

            elif action == "click":
                if x is None or y is None:
                    raise ValueError("x and y are required for click")
                abs_x, abs_y = _to_abs_coords(x, y, page)
                page.mouse.click(abs_x, abs_y)
                return json.dumps({"success": True, "result": f"Clicked at normalized ({x}, {y}) → pixel ({abs_x}, {abs_y})"})

            elif action == "double_click":
                if x is None or y is None:
                    raise ValueError("x and y are required for double_click")
                abs_x, abs_y = _to_abs_coords(x, y, page)
                page.mouse.dblclick(abs_x, abs_y)
                return json.dumps({"success": True, "result": f"Double-clicked at normalized ({x}, {y}) → pixel ({abs_x}, {abs_y})"})

            elif action == "right_click":
                if x is None or y is None:
                    raise ValueError("x and y are required for right_click")
                abs_x, abs_y = _to_abs_coords(x, y, page)
                page.mouse.click(abs_x, abs_y, button="right")
                return json.dumps({"success": True, "result": f"Right-clicked at normalized ({x}, {y}) → pixel ({abs_x}, {abs_y})"})

            elif action == "scroll":
                if x is None or y is None:
                    raise ValueError("x and y are required for scroll")
                if not direction:
                    raise ValueError("direction is required for scroll")
                abs_x, abs_y = _to_abs_coords(x, y, page)
                delta = float(pixels or 100)
                wheel_y = delta if direction == "down" else -delta
                page.mouse.move(abs_x, abs_y)
                page.mouse.wheel(0, wheel_y)
                return json.dumps({"success": True, "result": f"Scrolled {direction} {delta}px at normalized ({x}, {y})"})

            elif action == "type":
                if text is None:
                    raise ValueError("text is required for type")
                page.keyboard.type(text, delay=50)
                return json.dumps({"success": True, "result": "Typed text"})

            elif action == "keypress":
                if not keys:
                    raise ValueError("keys is required for keypress")
                for key in keys:
                    page.keyboard.press(key)
                return json.dumps({"success": True, "result": f"Pressed keys: {keys}"})

            elif action == "move":
                if x is None or y is None:
                    raise ValueError("x and y are required for move")
                abs_x, abs_y = _to_abs_coords(x, y, page)
                page.mouse.move(abs_x, abs_y)
                return json.dumps({"success": True, "result": f"Moved mouse to normalized ({x}, {y}) → pixel ({abs_x}, {abs_y})"})

            elif action == "drag":
                if x is None or y is None or target_x is None or target_y is None:
                    raise ValueError("x, y, target_x, and target_y are required for drag")
                abs_x, abs_y = _to_abs_coords(x, y, page)
                abs_tx, abs_ty = _to_abs_coords(target_x, target_y, page)
                page.mouse.move(abs_x, abs_y)
                page.mouse.down()
                page.mouse.move(abs_tx, abs_ty)
                page.mouse.up()
                return json.dumps({"success": True, "result": f"Dragged from ({x}, {y}) to ({target_x}, {target_y})"})

            elif action == "fill":
                if not selector:
                    raise ValueError("selector is required for fill")
                if text is None:
                    raise ValueError("text is required for fill")
                page.fill(selector, text)
                return json.dumps({"success": True, "result": f"Filled '{selector}' with text"})

            elif action == "get_text":
                if not selector:
                    raise ValueError("selector is required for get_text")
                content = page.inner_text(selector)
                return json.dumps({"success": True, "result": content})

            elif action == "back":
                page.go_back()
                return json.dumps({"success": True, "result": "Navigated back"})

            elif action == "forward":
                page.go_forward()
                return json.dumps({"success": True, "result": "Navigated forward"})

            elif action == "screenshot":
                png_bytes = page.screenshot(type="png")
                encoded = base64.b64encode(png_bytes).decode("utf-8")
                return json.dumps({"success": True, "result": f"data:image/png;base64,{encoded}"})

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

    return StructuredTool.from_function(
        func=computer_use,
        name="computer_use",
        description=(
            "Control the browser to complete tasks. Coordinates are normalized 0–1000 "
            "(do NOT use pixel values). Use screenshot to observe the current state. "
            "Use terminate when done, fail if the task cannot be completed."
        ),
        args_schema=PlaywrightQwenArgs,
    )
