"""
PyAutoGUI-based computer use environment.

Wraps a PyAutoGUI computer use tool to provide a ComputerUseEnv
implementation that operates directly against the host desktop.
No browser or external process is needed — start_env() is a no-op.
"""

import io
import os
import sys
from typing import Tuple

# Resolve tools/ imports regardless of working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from comp_use_env import ComputerUseEnv, LangChainToolLike


class PyAutoGUIComputerUseEnv(ComputerUseEnv):
    """
    Computer use environment backed by PyAutoGUI for direct desktop control.

    Supports two model variants:
    - "qwen": Qwen3-VL normalized 0–1000 coordinates (qwen_tool_computer_use)
    - "gpt": raw screen pixel coordinates (tool_pyautogui_gpt)

    Lifecycle::

        env = PyAutoGUIComputerUseEnv(model_variant="gpt")
        env.start_env()
        tool = env.get_computer_use_tool()
        # ... run agent ...
        env.stop_env()
    """

    def __init__(self, model_variant: str = "qwen") -> None:
        self._model_variant = model_variant
        self._started = False

    def start_env(self) -> None:
        """
        Mark the environment as started.

        PyAutoGUI operates directly against the running desktop and requires
        no setup beyond this flag.
        """
        self._started = True

    def stop_env(self) -> None:
        """Mark the environment as stopped."""
        self._started = False

    def get_computer_use_tool(self) -> LangChainToolLike:
        """
        Return the PyAutoGUI computer use tool for the configured model variant.

        Raises:
            RuntimeError: If start_env() has not been called.
            ValueError: If model_variant is not "qwen" or "gpt".
        """
        if not self._started:
            raise RuntimeError(
                "Environment is not started. Call start_env() before get_computer_use_tool()."
            )
        if self._model_variant == "qwen":
            from qwen_tool_computer_use import computer_use
        elif self._model_variant == "gpt":
            from tool_pyautogui_gpt import computer_use
        else:
            raise ValueError(
                f"Unknown model_variant: {self._model_variant!r}. Expected 'qwen' or 'gpt'."
            )
        return computer_use

    def capture_screenshot(self) -> Tuple[bytes, str]:
        """
        Capture a PNG screenshot of the entire desktop.

        Returns:
            A tuple of (png_bytes, "image/png").

        Raises:
            RuntimeError: If start_env() has not been called.
        """
        if not self._started:
            raise RuntimeError(
                "Environment is not started. Call start_env() before capture_screenshot()."
            )
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return (buf.getvalue(), "image/png")
