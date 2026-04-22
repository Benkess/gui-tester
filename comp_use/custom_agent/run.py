# run.py
# CLI entry point for the computer use agent.
#
# Required args:
#   --env     Path to environment config JSON
#   --agent   Path to agent config JSON
#
# Optional overrides (take precedence over values in the config files):
#   --task        Override user_prompt without editing the agent config
#   --start-url   Override start_url without editing the environment config
#   --allow-local-files  Allow Chromium local file access
#   --allow-extensions   Allow Chromium extensions
#   --headless    Run the browser in headless mode
#   --record      Record a Playwright video for this run (headed only)
#   --verbose     Enable verbose agent output
#
# Examples:
#   python run.py --env config/environment/playwright_gpt.json --agent config/agent/gpt_agent.json
#
#   python run.py \
#       --env config/environment/playwright_gpt.json \
#       --agent config/agent/gpt_agent.json \
#       --task "Fill in the contact form and submit it" \
#       --start-url "file:///C:/path/to/local/form.html" \
#       --allow-local-files \
#       --headless \
#       --verbose

import argparse
import json
import os
import sys
from datetime import datetime

# Ensure custom_agent/ is importable when run.py is invoked from other directories
sys.path.insert(0, os.path.dirname(__file__))


def load_json(path: str) -> dict:
    """Load a JSON config file and return it as a dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: dict) -> None:
    """Write a JSON file with stable formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def build_env(env_config: dict):
    """Instantiate the correct ComputerUseEnv subclass from a config dict."""
    env_type = env_config.get("type")
    env_params = env_config.get("params", {})

    if env_type == "playwright":
        from playwright_env import PlaywrightComputerUseEnv
        return PlaywrightComputerUseEnv(**env_params)
    if env_type == "pyautogui":
        from pyautogui_env import PyAutoGUIComputerUseEnv
        return PyAutoGUIComputerUseEnv(**env_params)
    raise ValueError(f"Unsupported environment type: '{env_type}'")


def build_agent(agent_config: dict, env):
    """Instantiate a ComputerUseAgent from a config dict and a live env."""
    from custom_comp_use_agent import ComputerUseAgent
    return ComputerUseAgent(computer_use_env=env, **agent_config)


def main():
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Launch the computer use agent with a given environment and agent config.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Basic launch
  python run.py --env config/environment/playwright_gpt.json --agent config/agent/gpt_agent.json

  # Override task and starting URL inline
  python run.py \\
      --env config/environment/playwright_gpt.json \\
      --agent config/agent/gpt_agent.json \\
      --task "Click the login button" \\
      --start-url "http://localhost:3000"

  # Run headless with verbose logging
  python run.py \\
      --env config/environment/playwright_qwen.json \\
      --agent config/agent/qwen_agent.json \\
      --headless --verbose

  # Record a headed Playwright browser run
  python run.py \\
      --env config/environment/playwright_gpt.json \\
      --agent config/agent/gpt_agent.json \\
      --record
        """,
    )

    # Required
    parser.add_argument(
        "--env",
        required=True,
        metavar="PATH",
        help="Path to the environment config JSON (e.g. config/environment/playwright_gpt.json)",
    )
    parser.add_argument(
        "--agent",
        required=True,
        metavar="PATH",
        help="Path to the agent config JSON (e.g. config/agent/gpt_agent.json)",
    )

    # Overrides
    parser.add_argument(
        "--task",
        default=None,
        metavar="TEXT",
        help="Override the user_prompt in the agent config. Wrap in quotes for multi-word tasks.",
    )
    parser.add_argument(
        "--start-url",
        default=None,
        metavar="URL",
        help=(
            "Override start_url in the environment config. "
            "Accepts http://, https://, or file:// paths. "
            "Only applies to Playwright environments."
        ),
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run the browser in headless mode. Only applies to Playwright environments.",
    )
    parser.add_argument(
        "--allow-local-files",
        action="store_true",
        default=False,
        help=(
            "Allow Chromium to access local files. Applied automatically when "
            "--start-url begins with file://, but can also be forced explicitly. "
            "Only applies to Playwright environments."
        ),
    )
    parser.add_argument(
        "--allow-extensions",
        action="store_true",
        default=False,
        help="Allow browser extensions to run in Chromium. Only applies to Playwright environments.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output from the agent.",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        default=False,
        help="Record a Playwright video for this run. Only supported for visible Playwright runs.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        metavar="PATH",
        help=(
            "Path for the run log file. "
            "Defaults to output/run_<timestamp>/run.log next to run.py. "
            "Use --no-log to disable logging entirely."
        ),
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        default=False,
        help="Disable automatic file logging.",
    )

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Load configs
    # ------------------------------------------------------------------
    try:
        env_config = load_json(args.env)
    except FileNotFoundError:
        parser.error(f"Environment config not found: {args.env}")

    try:
        raw_agent_config = load_json(args.agent)
    except FileNotFoundError:
        parser.error(f"Agent config not found: {args.agent}")

    # The config file has the shape {"name": "...", "agent": {...}}.
    # ComputerUseAgent only accepts the inner "agent" dict.
    agent_config = raw_agent_config.get("agent", raw_agent_config)

    # "implementation" is a config-file convention (e.g. "openai"), not a
    # ComputerUseAgent parameter - drop it before unpacking.
    agent_config.pop("implementation", None)

    # ------------------------------------------------------------------
    # Apply CLI overrides (mutate in-memory, never touch the files)
    # ------------------------------------------------------------------
    if args.task:
        agent_config["user_prompt"] = args.task

    if args.start_url:
        if env_config.get("type") != "playwright":
            print("[Warning] --start-url has no effect on non-Playwright environments.")
        else:
            env_config.setdefault("params", {})["start_url"] = args.start_url

    if args.headless:
        if env_config.get("type") != "playwright":
            print("[Warning] --headless has no effect on non-Playwright environments.")
        else:
            env_config.setdefault("params", {})["headless"] = True

    if args.allow_local_files:
        if env_config.get("type") != "playwright":
            print("[Warning] --allow-local-files has no effect on non-Playwright environments.")
        else:
            env_config.setdefault("params", {})["allow_local_files"] = True

    if args.allow_extensions:
        if env_config.get("type") != "playwright":
            print("[Warning] --allow-extensions has no effect on non-Playwright environments.")
        else:
            env_config.setdefault("params", {})["allow_extensions"] = True

    if args.verbose:
        agent_config["verbose"] = True

    # ------------------------------------------------------------------
    # Resolve per-run artifact directory and recording policy
    # ------------------------------------------------------------------
    output_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_root, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(output_root, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    manifest_path = os.path.join(run_dir, "run_manifest.json")
    video_dir = os.path.join(run_dir, "video")

    record_requested = args.record
    recording_enabled = False
    recording_disabled_reason = None

    env_type = env_config.get("type", "unknown")
    env_params = env_config.setdefault("params", {})
    headless = env_params.get("headless", False)

    if record_requested:
        if env_type != "playwright":
            recording_disabled_reason = "Recording is currently only supported for Playwright environments."
            print(f"[Warning] {recording_disabled_reason}")
        elif headless:
            recording_disabled_reason = "Recording is disabled for headless Playwright runs in v1."
            print(f"[Warning] {recording_disabled_reason}")
        else:
            recording_enabled = True
            os.makedirs(video_dir, exist_ok=True)
            env_params["record_video"] = True
            env_params["record_video_dir"] = video_dir

    # ------------------------------------------------------------------
    # Resolve log file path
    # ------------------------------------------------------------------
    if args.no_log:
        log_file = None
    elif args.log_file:
        log_file = args.log_file
    else:
        log_file = os.path.join(run_dir, "run.log")

    agent_config["log_file"] = log_file

    # ------------------------------------------------------------------
    # Write initial run manifest
    # ------------------------------------------------------------------
    manifest = {
        "timestamp": timestamp,
        "env_config_path": args.env,
        "agent_config_path": args.agent,
        "task": agent_config.get("user_prompt"),
        "env_type": env_type,
        "headless": headless,
        "run_dir": run_dir,
        "log_path": log_file,
        "recording_requested": record_requested,
        "recording_enabled": recording_enabled,
        "recording_disabled_reason": recording_disabled_reason,
        "video_dir": video_dir if recording_enabled else None,
        "video_path": None,
    }
    write_json(manifest_path, manifest)

    # ------------------------------------------------------------------
    # Print effective config so you always know what's running
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  COMPUTER USE AGENT")
    print("=" * 60)
    print(f"  Env config  : {args.env}")
    print(f"  Agent config: {args.agent}")
    print(f"  Task        : {agent_config.get('user_prompt', '(not set)')}")
    if env_type == "playwright":
        print(f"  Start URL   : {env_params.get('start_url') or '(none)'}")
        print(f"  Headless    : {headless}")
        print(f"  Local Files : {env_params.get('allow_local_files', False)}")
        print(f"  Extensions  : {env_params.get('allow_extensions', False)}")
    print(f"  Recording   : {'enabled' if recording_enabled else 'disabled'}")
    if record_requested and not recording_enabled and recording_disabled_reason:
        print(f"  Record Note : {recording_disabled_reason}")
    print(f"  Verbose     : {agent_config.get('verbose', False)}")
    print(f"  Run dir     : {run_dir}")
    print(f"  Log file    : {log_file if log_file else '(disabled)'}")
    print(f"  Manifest    : {manifest_path}")
    print("=" * 60 + "\n")

    # ------------------------------------------------------------------
    # Build and run
    # ------------------------------------------------------------------
    env = build_env(env_config)
    video_path = None
    run_error = None
    try:
        env.start_env()
        agent = build_agent(agent_config, env)
        agent.run(
            env_type=env_type,
            start_url=env_params.get("start_url"),
            headless=headless,
            log_path=log_file,
        )
    except Exception as exc:
        run_error = str(exc)
        raise
    finally:
        env.stop_env()
        if hasattr(env, "get_recorded_video_path"):
            video_path = env.get_recorded_video_path()
        if video_path:
            manifest["video_path"] = video_path
            print(f"Recorded video saved to: {video_path}")
        if run_error:
            manifest["run_error"] = run_error
        write_json(manifest_path, manifest)


if __name__ == "__main__":
    main()
