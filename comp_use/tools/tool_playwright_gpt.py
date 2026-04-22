"""
Playwright computer use tool for GPT models.

Exports build_tool(page) -> StructuredTool. All state is scoped to the closure
over the Playwright page object — no module-level singletons.

Coordinate system: raw viewport pixel coordinates.
"""

import base64
import json
import time as _time
from typing import List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


def build_tool(page) -> StructuredTool:
    """
    Build a computer_use LangChain tool bound to the given Playwright page.

    Args:
        page: A Playwright sync Page object. The tool holds a reference to this
              page for the duration of the agent session.

    Returns:
        A StructuredTool with name "computer_use" that the agent can invoke.
    """
    vp = page.viewport_size or {"width": 1280, "height": 720}
    width = vp["width"]
    height = vp["height"]

    class PlaywrightGPTArgs(BaseModel):
        """Arguments for the computer_use tool (GPT / pixel coordinate variant)."""

        thought: str = Field(
            ...,
            description="Your reasoning about the current state and what action to take next.",
        )
        action: str = Field(
            ...,
            description=(
                "Action to perform. One of: navigate, click, double_click, scroll, type, "
                "keypress, move, drag, screenshot, wait, terminate, fail."
            ),
        )
        x: Optional[float] = Field(
            None,
            description=(
                f"Pixel x-coordinate in the browser viewport. "
                f"Range: 0–{width}, where 0 is the left edge and {width} is the right edge. "
                "Required for: click, double_click, move, drag, scroll."
            ),
        )
        y: Optional[float] = Field(
            None,
            description=(
                f"Pixel y-coordinate in the browser viewport. "
                f"Range: 0–{height}, where 0 is the top edge and {height} is the bottom edge. "
                "Required for: click, double_click, move, drag, scroll."
            ),
        )
        target_x: Optional[float] = Field(
            None,
            description=(
                f"Pixel x-coordinate of the drag destination. "
                f"Range: 0–{width}. Required for: drag."
            ),
        )
        target_y: Optional[float] = Field(
            None,
            description=(
                f"Pixel y-coordinate of the drag destination. "
                f"Range: 0–{height}. Required for: drag."
            ),
        )
        url: Optional[str] = Field(
            None,
            description="URL to navigate to. Required for: navigate.",
        )
        text: Optional[str] = Field(
            None,
            description="Text to type into the focused element. Required for: type.",
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
        status: Optional[str] = Field(
            None,
            description="Completion status message. Optional for: terminate.",
        )
        message: Optional[str] = Field(
            None,
            description="Failure reason. Optional for: fail.",
        )

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
        status: Optional[str] = None,
        message: Optional[str] = None,
    ) -> str:
        """Execute a computer use action in the browser."""
        # Log all non-None parameters for debugging
        params = {k: v for k, v in {
            "x": x, "y": y, "target_x": target_x, "target_y": target_y,
            "url": url, "text": text, "keys": keys, "direction": direction,
            "pixels": pixels, "ms": ms, "status": status, "message": message,
        }.items() if v is not None}
        print(f"  [tool_playwright_gpt] action={action} params={params}")

        try:
            if action == "navigate":
                if not url:
                    raise ValueError("url is required for navigate")
                page.goto(url)
                return json.dumps({"success": True, "result": f"Navigated to {url}"})

            elif action == "click":
                if x is None or y is None:
                    raise ValueError("x and y are required for click")
                page.mouse.click(float(x), float(y))
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                page.evaluate("window.__flashCursor && window.__flashCursor()")
                return json.dumps({"success": True, "result": f"Clicked at ({x}, {y})"})

            elif action == "double_click":
                if x is None or y is None:
                    raise ValueError("x and y are required for double_click")
                page.mouse.dblclick(float(x), float(y))
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                page.evaluate("window.__flashCursor && window.__flashCursor()")
                return json.dumps({"success": True, "result": f"Double-clicked at ({x}, {y})"})

            elif action == "scroll":
                if x is None or y is None:
                    raise ValueError("x and y are required for scroll")
                if not direction:
                    raise ValueError("direction is required for scroll")
                delta = float(pixels or 100)
                wheel_y = delta if direction == "down" else -delta
                page.mouse.move(float(x), float(y))
                page.mouse.wheel(0, wheel_y)
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                return json.dumps({"success": True, "result": f"Scrolled {direction} {delta}px at ({x}, {y})"})

            elif action == "type":
                if text is None:
                    raise ValueError("text is required for type")
                page.keyboard.type(text, delay=50)
                return json.dumps({"success": True, "result": f"Typed text"})

            elif action == "keypress":
                if not keys:
                    raise ValueError("keys is required for keypress")
                for key in keys:
                    page.keyboard.press(key)
                return json.dumps({"success": True, "result": f"Pressed keys: {keys}"})

            elif action == "move":
                if x is None or y is None:
                    raise ValueError("x and y are required for move")
                page.mouse.move(float(x), float(y))
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                return json.dumps({"success": True, "result": f"Moved mouse to ({x}, {y})"})

            elif action == "drag":
                if x is None or y is None or target_x is None or target_y is None:
                    raise ValueError("x, y, target_x, and target_y are required for drag")
                page.mouse.move(float(x), float(y))
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                page.mouse.down()
                page.mouse.move(float(target_x), float(target_y))
                page.mouse.up()
                page.evaluate(f"window.__setCursor && window.__setCursor({float(target_x)}, {float(target_y)})")
                return json.dumps({"success": True, "result": f"Dragged from ({x}, {y}) to ({target_x}, {target_y})"})

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
            "Control the browser to complete tasks. Use screenshot to observe the current "
            "state. Use terminate when done, fail if the task cannot be completed."
        ),
        args_schema=PlaywrightGPTArgs,
    )
