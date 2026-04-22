# tool_browser_use.py

# Import necessary libraries
from langchain.tools import tool
import json
import os
import tempfile
from typing import Optional, List
from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Browser singleton
#
# A persistent Playwright browser + page is shared across all tool
# calls so that navigation history, cookies, and DOM state are
# preserved between agent steps.  Call _get_page() to lazily
# initialize, or use launch_browser() / close_browser() explicitly
# from your agent setup/teardown code.
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
    global _page_instance
    if _page_instance is None:
        launch_browser()
    return _page_instance


# ------------------------------------------------------------------
# Tool schema
# ------------------------------------------------------------------

class BrowserUseArgs(BaseModel):
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
            "The browser action to perform. One of: navigate, click, fill, type, "
            "key, scroll, hover, select, get_text, get_attribute, screenshot, "
            "wait, back, forward, terminate, fail."
        ),
    )
    url: Optional[str] = Field(
        None,
        description="URL to navigate to. Required when action='navigate'.",
    )
    selector: Optional[str] = Field(
        None,
        description=(
            "CSS selector identifying the target element. Required for: click, fill, "
            "hover, select, get_text, get_attribute. Optional for: type (types at "
            "current focus if omitted)."
        ),
    )
    coordinate: Optional[List[float]] = Field(
        None,
        description=(
            "[x, y] in viewport pixels. Alternative to 'selector' for click/hover "
            "when a CSS selector is not available."
        ),
    )
    text: Optional[str] = Field(
        None,
        description=(
            "Text to type or fill. Required when action='type' or action='fill'."
        ),
    )
    keys: Optional[List[str]] = Field(
        None,
        description=(
            "Keys to press as a chord (e.g. ['Control', 'c']). "
            "Required when action='key'."
        ),
    )
    pixels: Optional[float] = Field(
        None,
        description=(
            "Vertical scroll distance in pixels. Positive scrolls down, "
            "negative scrolls up. Required when action='scroll'."
        ),
    )
    value: Optional[str] = Field(
        None,
        description="Option value or label to select. Required when action='select'.",
    )
    attribute: Optional[str] = Field(
        None,
        description="HTML attribute name to read (e.g. 'href'). Required when action='get_attribute'.",
    )
    timeout: Optional[float] = Field(
        None,
        description=(
            "Maximum time in milliseconds to wait for element/navigation. "
            "Defaults to Playwright's built-in timeout (30 000 ms) when omitted."
        ),
    )
    time: Optional[float] = Field(
        None,
        description="Duration in seconds to pause. Required when action='wait'.",
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

@tool(args_schema=BrowserUseArgs)
def browser_use(
    thought: str,
    action: str,
    url: Optional[str] = None,
    selector: Optional[str] = None,
    coordinate: Optional[List[float]] = None,
    text: Optional[str] = None,
    keys: Optional[List[str]] = None,
    pixels: Optional[float] = None,
    value: Optional[str] = None,
    attribute: Optional[str] = None,
    timeout: Optional[float] = None,
    time: Optional[float] = None,
    status: Optional[str] = None,
    message: Optional[str] = None,
) -> str:
    """Control a web browser using Playwright.

    A persistent browser session is shared across calls so page state,
    cookies, and navigation history are preserved between agent steps.
    Use launch_browser() / close_browser() from your agent setup/teardown
    code to manage the session explicitly.

    Returns a JSON string:
        {"success": true, "result": "<description or extracted content>"}
        {"success": false, "error": "<error message>"}

    Terminal actions (terminate, fail) include an extra key:
        {"success": true, "result": "...", "terminal": true}

    Screenshot action saves a PNG and returns its file path:
        {"success": true, "result": "/tmp/.../screenshot_N.png"}
    """
    try:
        page = _get_page()
        pw_timeout = timeout if timeout is not None else 30_000

        # ------------------------------------------------------------------
        # Navigation
        # ------------------------------------------------------------------
        if action == "navigate":
            if not url:
                raise ValueError("Missing 'url' for action='navigate'")
            page.goto(url, timeout=pw_timeout)
            return json.dumps({"success": True, "result": f"Navigated to {url}"})

        elif action == "back":
            page.go_back(timeout=pw_timeout)
            return json.dumps({"success": True, "result": "Navigated back"})

        elif action == "forward":
            page.go_forward(timeout=pw_timeout)
            return json.dumps({"success": True, "result": "Navigated forward"})

        # ------------------------------------------------------------------
        # Mouse actions
        # ------------------------------------------------------------------
        elif action == "click":
            if selector:
                page.click(selector, timeout=pw_timeout)
                return json.dumps({"success": True, "result": f"Clicked '{selector}'"})
            elif coordinate:
                page.mouse.click(coordinate[0], coordinate[1])
                return json.dumps({"success": True, "result": f"Clicked at ({coordinate[0]}, {coordinate[1]})"})
            else:
                raise ValueError("'click' requires either 'selector' or 'coordinate'")

        elif action == "hover":
            if selector:
                page.hover(selector, timeout=pw_timeout)
                return json.dumps({"success": True, "result": f"Hovered over '{selector}'"})
            elif coordinate:
                page.mouse.move(coordinate[0], coordinate[1])
                return json.dumps({"success": True, "result": f"Hovered at ({coordinate[0]}, {coordinate[1]})"})
            else:
                raise ValueError("'hover' requires either 'selector' or 'coordinate'")

        # ------------------------------------------------------------------
        # Keyboard / text input
        # ------------------------------------------------------------------
        elif action == "fill":
            if not selector:
                raise ValueError("Missing 'selector' for action='fill'")
            if text is None:
                raise ValueError("Missing 'text' for action='fill'")
            page.fill(selector, text, timeout=pw_timeout)
            return json.dumps({"success": True, "result": f"Filled '{selector}' with: {text}"})

        elif action == "type":
            if text is None:
                raise ValueError("Missing 'text' for action='type'")
            if selector:
                page.click(selector, timeout=pw_timeout)
            page.keyboard.type(text, delay=50)
            return json.dumps({"success": True, "result": f"Typed: {text}"})

        elif action == "key":
            if not keys:
                raise ValueError("Missing 'keys' for action='key'")
            chord = "+".join(keys)
            page.keyboard.press(chord)
            return json.dumps({"success": True, "result": f"Pressed: {chord}"})

        # ------------------------------------------------------------------
        # Scroll
        # ------------------------------------------------------------------
        elif action == "scroll":
            if pixels is None:
                raise ValueError("Missing 'pixels' for action='scroll'")
            page.mouse.wheel(0, pixels)
            return json.dumps({"success": True, "result": f"Scrolled {pixels} pixels"})

        # ------------------------------------------------------------------
        # Form controls
        # ------------------------------------------------------------------
        elif action == "select":
            if not selector:
                raise ValueError("Missing 'selector' for action='select'")
            if not value:
                raise ValueError("Missing 'value' for action='select'")
            page.select_option(selector, value, timeout=pw_timeout)
            return json.dumps({"success": True, "result": f"Selected '{value}' in '{selector}'"})

        # ------------------------------------------------------------------
        # DOM inspection
        # ------------------------------------------------------------------
        elif action == "get_text":
            if not selector:
                raise ValueError("Missing 'selector' for action='get_text'")
            content = page.inner_text(selector, timeout=pw_timeout)
            return json.dumps({"success": True, "result": content})

        elif action == "get_attribute":
            if not selector:
                raise ValueError("Missing 'selector' for action='get_attribute'")
            if not attribute:
                raise ValueError("Missing 'attribute' for action='get_attribute'")
            attr_value = page.get_attribute(selector, attribute, timeout=pw_timeout)
            return json.dumps({"success": True, "result": attr_value})

        # ------------------------------------------------------------------
        # Screenshot
        # ------------------------------------------------------------------
        elif action == "screenshot":
            existing = [f for f in os.listdir(_screenshot_dir) if f.startswith("screenshot_")]
            index = len(existing) + 1
            filepath = os.path.join(_screenshot_dir, f"screenshot_{index}.png")
            page.screenshot(path=filepath, full_page=False)
            return json.dumps({"success": True, "result": filepath})

        # ------------------------------------------------------------------
        # Wait
        # ------------------------------------------------------------------
        elif action == "wait":
            import time as _time
            duration = time if time is not None else 1.0
            _time.sleep(duration)
            return json.dumps({"success": True, "result": f"Waited {duration} seconds"})

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
