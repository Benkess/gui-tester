# Custom Computer Use Agent

## Overview

This system is a modular computer-use agent that pairs any OpenAI-compatible language model with a pluggable execution environment. The agent runs a LangGraph loop: it captures a screenshot, sends it to the model, receives a tool call, executes the action, and repeats until the model signals task completion. 


All configuration parameters (including model endpoints, task instructions, and environment parameters) are defined in JSON files. This allows different model and environment combinations to be launched without changing any code.

## Architecture

The system has three layers:

**Agent:** `custom_comp_use_agent.py` implements the LangGraph state machine. It takes a screenshot, sends it (along with message history) to the LLM, executes the returned tool call against the environment, and loops until the tool returns `"terminal": true` or the model makes no tool call.

**Environment:** `ComputerUseEnv` (defined in `comp_use_env.py`) is the abstract base class for all environments. It owns the lifecycle (`start_env` / `stop_env`), wires the tool to the agent via `get_computer_use_tool()`, and provides `capture_screenshot()`. Two concrete implementations are provided:
- `PlaywrightComputerUseEnv` (`playwright_env.py`): launches and manages a Chromium browser.
- `PyAutoGUIComputerUseEnv` (`pyautogui_env.py`): wraps the host desktop via PyAutoGUI.

**Tools:** Tools implement the actual browser or desktop actions. Playwright tools use a `build_tool(page)` factory pattern so each tool instance is freshly bound to the live page object with no module-level state. The PyAutoGUI tool is a module-level singleton created by the `@tool` decorator in `qwen_tool_computer_use.py`.

## Supported Configurations

| Model | Environment | Tool File | Coordinate System | Agent Config | Env Config |
|---|---|---|---|---|---|
| GPT-5.4 | Playwright | `tools/tool_playwright_gpt.py` | Raw viewport pixels | `config/agent/gpt_agent.json` | `config/environment/playwright_gpt.json` |
| Qwen3-VL | Playwright | `tools/tool_playwright_qwen.py` | Normalized 0-1000 | `config/agent/qwen_agent.json` | `config/environment/playwright_qwen.json` |
| Qwen3-VL | PyAutoGUI | `tools/qwen_tool_computer_use.py` | Normalized 0-1000 | `config/agent/qwen_agent.json` | `config/environment/pyautogui.json` |

## Prerequisites

Install Python packages:

```bash
pip install langchain langchain-openai langgraph playwright pyautogui pillow pydantic
```

Install the Playwright Chromium browser:

```bash
playwright install chromium
```

Set the `OPENAI_API_KEY` environment variable when using GPT:

```bash
export OPENAI_API_KEY=sk-...
```

For Qwen, start Ollama and pull the model:

```bash
ollama pull qwen3-vl:4b
```

## How to Run

### CLI (recommended)

`run.py` is the main entry point. Run it from the `custom_agent/` directory:

```bash
python run.py --env <env-config> --agent <agent-config> [options]
```

**Basic launch:**

```bash
python run.py --env config/environment/playwright_gpt.json --agent config/agent/gpt_agent.json
```

**Qwen3-VL + Playwright:**

```bash
python run.py --env config/environment/playwright_qwen.json --agent config/agent/qwen_agent.json
```

**Qwen3-VL + PyAutoGUI (desktop control):**

```bash
python run.py --env config/environment/pyautogui.json --agent config/agent/qwen_agent.json
```

**CLI options:** 

All options override the corresponding config file values.

| Flag | Description |
|---|---|
| `--task "TEXT"` | Override the task instruction (`user_prompt` in the agent config) |
| `--start-url URL` | Override `start_url` in the environment config (Playwright only) |
| `--headless` | Run the browser without a visible window (Playwright only) |
| `--allow-local-files` | Allow Chromium to access local files (Playwright only) |
| `--allow-extensions` | Allow browser extensions to run in Chromium (Playwright only) |
| `--verbose` | Enable verbose agent output |
| `--record` | Record a Playwright browser video for the run (headed Playwright only) |
| `--log-file PATH` | Write the run log to this path instead of the default `output/run_<timestamp>/run.log` |
| `--no-log` | Disable automatic file logging |

**Example with overrides:**

```bash
python run.py \
    --env config/environment/playwright_gpt.json \
    --agent config/agent/gpt_agent.json \
    --task "Fill in the contact form and submit it" \
    --start-url "file:///C:/path/to/local/form.html" \
    --allow-local-files \
    --headless \
    --verbose
```

**Example with recording:**

```bash
python run.py \
    --env config/environment/playwright_gpt.json \
    --agent config/agent/gpt_agent.json \
    --record
```

## Logging

Every run creates a run directory at `output/run_<timestamp>/` in the same directory as `run.py`. The `output/` folder is created if it does not already exist.

**Artifacts in the run directory:**
- `run.log` - structured plain-text agent log (unless `--no-log` is used)
- `run_manifest.json` - run metadata including task, config paths, logging path, and recording status
- `video/` - Playwright-recorded browser video files when `--record` succeeds

**What the log contains:**
- Run metadata such as timestamp, task, model, environment, and start URL.
- Per-step data including a screenshot placeholder (`<image_data_removed>`), each tool call with its action parameters, and the sanitized tool result.
- Complete message history at the end of the run with all fields included. Image base64 data is replaced with `<image_data_removed (image/png)>` to keep the file readable.

**Verbose mode** (`--verbose`): Prints the exact resolved messages sent to the model at each step. The log file will show message history but not the exact context seen by the model. The agent uses a sliding-window trimming behavior for context management, causing older messages to be dropped.

**Log file options:**

```bash
# Default: auto-created run directory with run.log
python run.py --env ... --agent ...

# Custom path
python run.py --env ... --agent ... --log-file /tmp/myrun.txt

# Disable logging
python run.py --env ... --agent ... --no-log

# Record a headed Playwright run
python run.py --env ... --agent ... --record
```

**Recording notes:**
- Recording is currently supported only for Playwright environments.
- Recording is currently disabled for headless Playwright runs in v1.
- When recording succeeds, the finalized video path is printed after the run ends and saved in `run_manifest.json`.

### Python API

You can also launch the agent directly from Python:

```python
from comp_agent_launch import launch_computer_use_agent

launch_computer_use_agent(
    env_config_path="config/environment/playwright_gpt.json",
    agent_config_path="config/agent/gpt_agent.json",
)
```

To open a specific page on launch, set `start_url` in the environment config. It accepts `http://`, `https://`, and `file://` paths:

```json
{
  "type": "playwright",
  "params": {
    "model_variant": "gpt",
    "headless": false,
    "viewport_width": 1280,
    "viewport_height": 720,
    "start_url": "file:///path/to/local/page.html",
    "show_cursor_overlay": true
  }
}
```

`file://` URLs work natively, but serving the page over localhost is more reliable for pages that load external scripts, stylesheets, or images. From the directory containing your HTML file:

```bash
python -m http.server 8000
```

Then use `http://127.0.0.1:8000/index.html` as the `start_url`.

## Configuring the Agent

The task the agent should complete is set via `user_prompt` in the agent config (e.g., `config/agent/gpt_agent.json`). Edit this field to change the task instruction given to the model.

Other tunable parameters are also in `config/agent/`:
- `model`: model identifier (e.g., `"gpt-5.4"` or `"qwen3-vl:4b"`)
- `max_tokens`: maximum tokens per LLM call
- `trim_strategy`: how to trim message history when the context fills (`"last"` or `"first"`)

Browser and viewport parameters are in `config/environment/`. For Playwright configs, `show_cursor_overlay` controls the small cursor dot shown in screenshots; set it to `false` to remove the overlay entirely.
