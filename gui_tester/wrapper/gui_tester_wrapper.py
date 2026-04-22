"""Wrapper that assembles and runs the GUI tester using the bundled comp_use code."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from gui_tester.tools.gui_testing_report_tool import build_tool as build_report_tool
from gui_tester.tools.restricted_playwright_computer_use import build_tool as build_computer_use_tool

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent
COMP_USE_CUSTOM_AGENT_DIR = PROJECT_ROOT / "comp_use" / "custom_agent"

if str(COMP_USE_CUSTOM_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(COMP_USE_CUSTOM_AGENT_DIR))

from custom_comp_use_agent import ComputerUseAgent  # noqa: E402
from playwright_env import PlaywrightComputerUseEnv  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _resolve_config_path(base_dir: Path, path_text: str) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def _build_runtime_prompt(url: str, gui_description: str, test_instructions: str) -> str:
    return (
        # "You are testing a GUI in the browser.\n\n"
        # "The browser is already open on the correct starting page.\n"
        # "Use the current page as your starting point. Do not reopen the starting page unless "
        # "there is a specific testing reason.\n\n"
        # Starting URL intentionally omitted from the model-facing prompt.
        # The wrapper still uses it internally to open the correct page and
        # logs it for debugging, but the tester does not need to see it.
        "GUI Description:\n"
        f"{gui_description.strip()}\n\n"
        "Testing Instructions:\n"
        f"{test_instructions.strip()}\n\n"
        # "Only save notes for meaningful findings, blockers, useful evidence, or important "
        # "page-level conclusions. When you have enough evidence, submit the final report."
    )


def _normalize_start_url(url_or_path: str) -> str:
    parsed = urlparse(url_or_path)
    if parsed.scheme in {"http", "https", "file"}:
        return url_or_path

    candidate = Path(url_or_path).expanduser()
    if candidate.exists():
        return candidate.resolve().as_uri()
    return url_or_path


def _create_run_dir(report_dir: str) -> Path:
    report_root = Path(report_dir).expanduser().resolve()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = report_root / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


class TestingPlaywrightEnvAdapter:
    """Delegate screenshots to the real env but supply the restricted computer-use tool."""

    def __init__(self, base_env: PlaywrightComputerUseEnv):
        self._base_env = base_env
        self._computer_use_tool = None

    def start_env(self):
        return self._base_env.start_env()

    def stop_env(self):
        return self._base_env.stop_env()

    def capture_screenshot(self):
        return self._base_env.capture_screenshot()

    def get_computer_use_tool(self):
        if self._computer_use_tool is None:
            page = getattr(self._base_env, "_page", None)
            if page is None:
                raise RuntimeError("Playwright page is not available. Ensure the env is started first.")
            self._computer_use_tool = build_computer_use_tool(page)
        return self._computer_use_tool


def run_gui_tester_session(
    url: str,
    gui_description: str,
    test_instructions: str,
    report_dir: str,
    config_path: str | None = None,
) -> dict[str, str]:
    """Run the GUI tester and return paths useful for debugging or follow-up tools."""
    normalized_url = _normalize_start_url(url)
    config_file = (
        Path(config_path).expanduser().resolve()
        if config_path
        else PACKAGE_ROOT / "config" / "default_tester_config.json"
    )
    config = _load_json(config_file)
    config_base_dir = config_file.parent

    if config.get("environment", {}).get("type") != "playwright":
        raise ValueError("This v1 GUI tester only supports Playwright environments.")

    if not report_dir:
        raise ValueError("report_dir is required for GUI tester runs.")
    run_dir = _create_run_dir(report_dir=report_dir)
    log_path = run_dir / "gui_tester_run.log"

    prompt_path_text = config.get("prompt", {}).get("system_prompt_path")
    if not prompt_path_text:
        raise ValueError("system_prompt_path is missing from the tester config.")
    system_prompt = _read_text(_resolve_config_path(config_base_dir, prompt_path_text))

    env_config = deepcopy(config["environment"])
    env_params = env_config.setdefault("params", {})
    env_params["start_url"] = normalized_url

    base_env = PlaywrightComputerUseEnv(**env_params)
    env_adapter = TestingPlaywrightEnvAdapter(base_env)
    report_tool_state = None

    runtime_prompt = _build_runtime_prompt(
        url=normalized_url,
        gui_description=gui_description,
        test_instructions=test_instructions,
    )

    try:
        env_adapter.start_env()
        report_tool, report_tool_state = build_report_tool(env=env_adapter, run_dir=run_dir)

        agent_config = deepcopy(config["agent"])
        agent_config["system_prompt"] = system_prompt
        agent_config["user_prompt"] = runtime_prompt
        agent_config["log_file"] = str(log_path)

        agent = ComputerUseAgent(
            computer_use_env=env_adapter,
            tools=[report_tool],
            **agent_config,
        )
        agent.run(
            env_type="playwright",
            start_url=normalized_url,
            headless=bool(env_params.get("headless", False)),
            log_path=str(log_path),
        )
    finally:
        env_adapter.stop_env()

    if report_tool_state is None or report_tool_state.final_report_path is None:
        raise RuntimeError(
            "The GUI tester run finished without submitting a final report. "
            "Check the agent log for details."
        )

    return {
        "report_path": str(report_tool_state.final_report_path.resolve()),
        "run_dir": str(run_dir.resolve()),
        "log_path": str(log_path.resolve()),
    }


def launch_gui_tester_subagent(
    url: str,
    gui_description: str,
    test_instructions: str,
    report_dir: str,
) -> str:
    """Parent-facing launcher that returns only the main report path."""
    result = run_gui_tester_session(
        url=url,
        gui_description=gui_description,
        test_instructions=test_instructions,
        report_dir=report_dir,
        config_path=None,
    )
    return result["report_path"]
