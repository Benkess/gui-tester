# tool_browser_use_minimal.py

# Import necessary libraries
from langchain.tools import tool
import json
import os
import time
import tempfile
from typing import Optional, List
from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Browser singleton — persistent session across tool calls
# ------------------------------------------------------------------

_playwright_instance = None
_browser_instance = None
_page_instance = None
_screenshot_dir = tempfile.mkdtemp()


def launch_browser(headless: bool = False) -> None:
    """Explicitly launch the shared browser. Called automatically on first tool use."""
    global _playwright_instance, _browser_instance, _page_instance
    from playwright.sync_api import sync_playwright

    _playwright_instance = sync_playwright().start()
    _browser_instance = _playwright_instance.chromium.launch(headless=headless)
    _page_instance = _browser_instance.new_page()


def close_browser() -> None:
    """Shut down the shared browser. Call from agent teardown."""
    global _playwright_instance, _browser_instance, _page_instance
    try:
        if _page_instance:
            _page_instance.close()
        if _browser_instance:
            _browser_instance.close()
        if _playwright_instance:
            _playwright_instance.stop()
    finally:
        _playwright_instance = None
        _browser_instance = None
        _page_instance = None


def _get_page():
    """Return the shared page, launching the browser if needed."""
    if _page_instance is None:
        launch_browser()
    return _page_instance


# ------------------------------------------------------------------
# Tool schema
# ------------------------------------------------------------------

class BrowserUseMinimalArgs(BaseModel):
    thought: str = Field(
        ...,
        description=(
            "Your reasoning: what you see on the page, what needs to be done next "
            "to accomplish the user goal, any mistakes from previous actions, or "
            "whether the goal is complete."
        ),
    )
    action: str = Field(
        ...,
        description=(
            "The browser action to perform. One of: navigate, click, double_click, "
            "scroll, type, keypress, move, drag, screenshot, wait, terminate, fail."
        ),
    )
    url: Optional[str] = Field(
        None,
        description="URL to navigate to. Required when action='navigate'.",
    )
    x: Optional[float] = Field(
        None,
        description="Viewport X coordinate in pixels. Required for: click, double_click, scroll, move, drag.",
    )
    y: Optional[float] = Field(
        None,
        description="Viewport Y coordinate in pixels. Required for: click, double_click, scroll, move, drag.",
    )
    button: Optional[str] = Field(
        "left",
        description="Mouse button to use: 'left', 'right', or 'middle'. Used by click and double_click.",
    )
    scroll_x: Optional[float] = Field(
        None,
        description="Horizontal scroll distance in pixels. Used when action='scroll'.",
    )
    scroll_y: Optional[float] = Field(
        None,
        description="Vertical scroll distance in pixels. Positive scrolls down. Used when action='scroll'.",
    )
    text: Optional[str] = Field(
        None,
        description="Text to type via keyboard. Required when action='type'.",
    )
    keys: Optional[List[str]] = Field(
        None,
        description=(
            "List of keys to press sequentially (e.g. ['Enter'], ['Control', 'c']). "
            "Required when action='keypress'. Use 'SPACE' for the space bar."
        ),
    )
    target_x: Optional[float] = Field(
        None,
        description="Drag destination X coordinate in pixels. Required when action='drag'.",
    )
    target_y: Optional[float] = Field(
        None,
        description="Drag destination Y coordinate in pixels. Required when action='drag'.",
    )
    status: Optional[str] = Field(
        None,
        description="Task completion status: 'success' or 'failure'. Required when action='terminate' or 'fail'.",
    )
    message: Optional[str] = Field(
        None,
        description="Explanation of why the task failed. Required when action='fail'.",
    )


# ------------------------------------------------------------------
# Tool implementation
# ------------------------------------------------------------------

@tool(args_schema=BrowserUseMinimalArgs)
def browser_use_minimal(
    thought: str,
    action: str,
    url: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    button: Optional[str] = "left",
    scroll_x: Optional[float] = None,
    scroll_y: Optional[float] = None,
    text: Optional[str] = None,
    keys: Optional[List[str]] = None,
    target_x: Optional[float] = None,
    target_y: Optional[float] = None,
    status: Optional[str] = None,
    message: Optional[str] = None,
) -> str:
    """Control a web browser with raw mouse and keyboard actions.

    Coordinate-based control using viewport pixels — no CSS selectors.
    A persistent browser session is shared across calls so page state and
    navigation history are preserved between agent steps.

    Returns a JSON string:
        {"success": true, "result": "<description>"}
        {"success": false, "error": "<error message>"}

    Terminal actions include an extra key:
        {"success": true, "result": "...", "terminal": true}

    Screenshot action saves a PNG and returns its file path:
        {"success": true, "result": "/tmp/.../screenshot_N.png"}
    """
    try:
        page = _get_page()

        if action == "navigate":
            if not url:
                raise ValueError("Missing 'url' for action='navigate'")
            page.goto(url)
            return json.dumps({"success": True, "result": f"Navigated to {url}"})

        elif action == "click":
            if x is None or y is None:
                raise ValueError("Missing 'x'/'y' for action='click'")
            page.mouse.click(x, y, button=button or "left")
            return json.dumps({"success": True, "result": f"Clicked ({x}, {y}) with {button} button"})

        elif action == "double_click":
            if x is None or y is None:
                raise ValueError("Missing 'x'/'y' for action='double_click'")
            page.mouse.dblclick(x, y, button=button or "left")
            return json.dumps({"success": True, "result": f"Double-clicked ({x}, {y})"})

        elif action == "scroll":
            if x is None or y is None:
                raise ValueError("Missing 'x'/'y' for action='scroll'")
            page.mouse.move(x, y)
            page.mouse.wheel(scroll_x or 0, scroll_y or 0)
            return json.dumps({"success": True, "result": f"Scrolled ({scroll_x or 0}, {scroll_y or 0}) at ({x}, {y})"})

        elif action == "move":
            if x is None or y is None:
                raise ValueError("Missing 'x'/'y' for action='move'")
            page.mouse.move(x, y)
            return json.dumps({"success": True, "result": f"Moved mouse to ({x}, {y})"})

        elif action == "drag":
            if x is None or y is None or target_x is None or target_y is None:
                raise ValueError("Missing 'x'/'y'/'target_x'/'target_y' for action='drag'")
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(target_x, target_y)
            page.mouse.up()
            return json.dumps({"success": True, "result": f"Dragged ({x}, {y}) → ({target_x}, {target_y})"})

        elif action == "type":
            if text is None:
                raise ValueError("Missing 'text' for action='type'")
            page.keyboard.type(text)
            return json.dumps({"success": True, "result": f"Typed: {text}"})

        elif action == "keypress":
            if not keys:
                raise ValueError("Missing 'keys' for action='keypress'")
            for key in keys:
                page.keyboard.press(" " if key == "SPACE" else key)
            return json.dumps({"success": True, "result": f"Pressed: {keys}"})

        elif action == "screenshot":
            existing = [f for f in os.listdir(_screenshot_dir) if f.startswith("screenshot_")]
            index = len(existing) + 1
            filepath = os.path.join(_screenshot_dir, f"screenshot_{index}.png")
            page.screenshot(path=filepath, full_page=False)
            return json.dumps({"success": True, "result": filepath})

        elif action == "wait":
            time.sleep(2)
            return json.dumps({"success": True, "result": "Waited 2 seconds"})

        elif action == "terminate":
            task_status = status or "success"
            return json.dumps({"success": True, "result": f"Task {task_status}", "terminal": True})

        elif action == "fail":
            fail_message = message or "Unknown error"
            return json.dumps({"success": True, "result": f"Task failed: {fail_message}", "terminal": True})

        else:
            raise ValueError(f"Unsupported action: '{action}'")

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
