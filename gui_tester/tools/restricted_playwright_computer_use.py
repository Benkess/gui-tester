"""Testing-specific Playwright computer-use tool for GUI testing."""

import json
import time as _time
from typing import List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


def build_tool(page) -> StructuredTool:
    """Build the restricted Playwright computer-use tool bound to a live page."""
    vp = page.viewport_size or {"width": 1280, "height": 720}
    width = vp["width"]
    height = vp["height"]

    class RestrictedPlaywrightArgs(BaseModel):
        thought: str = Field(
            ...,
            description="Your reasoning about the current GUI state and what you will do next.",
        )
        action: str = Field(
            ...,
            description=(
                "Action to perform. One of: navigate, click, double_click, scroll, type, "
                "keypress, move, drag, noop, wait. Finish the run by using "
                "gui_testing_report_tool submit_final_report, not this tool."
            ),
        )
        x: Optional[float] = Field(
            None,
            description=(
                f"Pixel x-coordinate in the browser viewport. Range: 0-{width}. "
                "Required for click, double_click, move, drag, and scroll."
            ),
        )
        y: Optional[float] = Field(
            None,
            description=(
                f"Pixel y-coordinate in the browser viewport. Range: 0-{height}. "
                "Required for click, double_click, move, drag, and scroll."
            ),
        )
        target_x: Optional[float] = Field(
            None,
            description=f"Pixel x-coordinate for the drag destination. Range: 0-{width}.",
        )
        target_y: Optional[float] = Field(
            None,
            description=f"Pixel y-coordinate for the drag destination. Range: 0-{height}.",
        )
        url: Optional[str] = Field(
            None,
            description="URL to navigate to. Required for navigate.",
        )
        text: Optional[str] = Field(
            None,
            description="Text to type into the focused element. Required for type.",
        )
        keys: Optional[List[str]] = Field(
            None,
            description="List of keys to press sequentially. Required for keypress.",
        )
        direction: Optional[str] = Field(
            None,
            description="Scroll direction: up or down. Required for scroll.",
        )
        pixels: Optional[float] = Field(
            None,
            description="Number of pixels to scroll. Required for scroll.",
        )
        ms: Optional[float] = Field(
            None,
            description="Duration in milliseconds. Required for wait.",
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
    ) -> str:
        params = {
            k: v
            for k, v in {
                "x": x,
                "y": y,
                "target_x": target_x,
                "target_y": target_y,
                "url": url,
                "text": text,
                "keys": keys,
                "direction": direction,
                "pixels": pixels,
                "ms": ms,
            }.items()
            if v is not None
        }
        print(f"  [restricted_playwright_tool] action={action} params={params}")

        try:
            if action == "navigate":
                if not url:
                    raise ValueError("url is required for navigate")
                page.goto(url)
                return json.dumps({"success": True, "result": f"Navigated to {url}"})

            if action == "click":
                if x is None or y is None:
                    raise ValueError("x and y are required for click")
                page.mouse.click(float(x), float(y))
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                page.evaluate("window.__flashCursor && window.__flashCursor()")
                return json.dumps({"success": True, "result": f"Clicked at ({x}, {y})"})

            if action == "double_click":
                if x is None or y is None:
                    raise ValueError("x and y are required for double_click")
                page.mouse.dblclick(float(x), float(y))
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                page.evaluate("window.__flashCursor && window.__flashCursor()")
                return json.dumps({"success": True, "result": f"Double-clicked at ({x}, {y})"})

            if action == "scroll":
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

            if action == "type":
                if text is None:
                    raise ValueError("text is required for type")
                page.keyboard.type(text, delay=50)
                return json.dumps({"success": True, "result": "Typed text"})

            if action == "keypress":
                if not keys:
                    raise ValueError("keys is required for keypress")
                for key in keys:
                    page.keyboard.press(key)
                return json.dumps({"success": True, "result": f"Pressed keys: {keys}"})

            if action == "move":
                if x is None or y is None:
                    raise ValueError("x and y are required for move")
                page.mouse.move(float(x), float(y))
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                return json.dumps({"success": True, "result": f"Moved mouse to ({x}, {y})"})

            if action == "drag":
                if x is None or y is None or target_x is None or target_y is None:
                    raise ValueError("x, y, target_x, and target_y are required for drag")
                page.mouse.move(float(x), float(y))
                page.evaluate(f"window.__setCursor && window.__setCursor({float(x)}, {float(y)})")
                page.mouse.down()
                page.mouse.move(float(target_x), float(target_y))
                page.mouse.up()
                page.evaluate(
                    f"window.__setCursor && window.__setCursor({float(target_x)}, {float(target_y)})"
                )
                return json.dumps(
                    {"success": True, "result": f"Dragged from ({x}, {y}) to ({target_x}, {target_y})"}
                )

            if action == "noop":
                return json.dumps(
                    {
                        "success": True,
                        "result": "No action taken. Continue to the next step for a fresh image. Use this sparingly.",
                    }
                )

            if action == "wait":
                duration_ms = float(ms or 1000)
                _time.sleep(duration_ms / 1000)
                return json.dumps({"success": True, "result": f"Waited {duration_ms}ms"})

            raise ValueError(
                "Unsupported action. Use gui_testing_report_tool submit_final_report to finish the run."
            )
        except Exception as exc:
            return json.dumps({"success": False, "error": str(exc)})

    return StructuredTool.from_function(
        func=computer_use,
        name="computer_use",
        description=(
            "Control the browser to test the GUI. "
            "Do not try to terminate with this tool. Finish by calling gui_testing_report_tool "
            "with action=submit_final_report."
        ),
        args_schema=RestrictedPlaywrightArgs,
    )
