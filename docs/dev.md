# Dev Info

`gui_tester` is a self-contained GUI testing agent package. It includes:
- a direct CLI for human use
- a local stdio MCP server for editor and coding-assistant integrations
- a bundled copy of the `comp_use` support code it depends on

This document is for maintainers. It collects implementation notes, packaging details, and development-specific behavior that does not need to be front-and-center in the main README.

## Repository Layout

- `gui_tester/` contains the package code, prompts, config, wrapper, custom tools, CLI, and MCP server
- `comp_use/` contains the bundled computer-use support code
- `pyproject.toml` defines the installable package and console entrypoints

The `comp_use` copy is intentionally kept as a sibling directory to `gui_tester` so the package boundary remains explicit.

## Package Setup

For MCP use, it is recommended to clone this repo separately from the project being tested. The MCP host should point at this package's virtual environment and install.

### Environment Setup

> **Note:** If `python` does not default to `python3` on your system, substitute `python3` for `python` in the following commands.

Navigate to the root directory:

```bash
cd path/to/gui-tester
```

Use the `venv` module to create a new virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment:

```bash
# On macOS/Linux
source .venv/bin/activate
```

```powershell
# On Windows
.venv\Scripts\activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

```bash
# Also upgrade these for TensorFlow or PyTorch
python -m pip install --upgrade pip wheel setuptools
```

### Package Install

From this directory:

```powershell
pip install -e .
```

Optional local development convenience:

```powershell
pip install -e .[dev]
```

The optional `dev` extra installs `python-dotenv`, which the bundled computer-use agent can use as a local `.env` fallback.

> **Note:** Normal install currently still requires `python-dotenv`. That compatibility gap is planned to be removed in a future update.

## Secrets and Config

Official package story:
- direct CLI usage should rely on normal environment variables
- MCP hosts should pass environment variables in their MCP config

Important:
- this package preserves the bundled computer-use agent's existing `api_key` and `api_key_env` behavior
- not all configs use `OPENAI_API_KEY`
- for example, some local-model configs use an explicit `api_key` value such as `ollama`

Local development convenience:
- if `python-dotenv` is installed, the bundled computer-use agent may still use its existing lower-level `.env` fallback
- this is preserved for compatibility, but it is not the primary package contract

Advanced config:
- the CLI supports `--config`
- the MCP tool schema is intentionally minimal
- tool inputs: `url`, `gui_description`, `test_instructions`, `report_dir`
- tool output: `report_path`

## Claude Code Setup

This section is kept as a concrete MCP host example for maintainers and contributors who want an end-to-end reference setup.

Example using the installed entrypoint inside the repo virtual environment:

**CLI only** (default local scope, goes into `~/.claude.json`):

```powershell
claude mcp add gui_tester --transport stdio --env YOUR_API_KEY=sk-your-key -- <path-to-venv>\Scripts\python.exe -m gui_tester.mcp
```

**CLI + VS Code extension** (project scope, creates `.mcp.json` in the project root):

```powershell
claude mcp add gui_tester --scope project --transport stdio --env YOUR_API_KEY=sk-your-key -- <path-to-venv>\Scripts\python.exe -m gui_tester.mcp
```

Replace `YOUR_API_KEY` with whatever environment variable name your model config expects, such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

Then verify:

In Claude Code, use `/mcp` and ensure `gui_tester` shows `Connected`.

Notes:
- After you set up or change the MCP config, start a fresh Claude session and reconnect to the MCP before retesting tool availability.

Example prompt for Claude Code:

```text
Call the launch_gui_tester MCP tool with these arguments:

url = file:///C:/path/to/your/gui/index.html
gui_description = A template for a personal website. It includes a landing page, blog page, and resume page. The sidebar on the landing page contains links to other media accounts.
test_instructions = Check all three pages for functionality and visual layout correctness. Report any issues found including visual, layout, and navigation issues. Pay attention to whether the site fits cleanly in the viewport and whether each page looks complete and usable.
report_dir = C:\path\to\your\context\reports
```

## Maintainer Notes

- The main `README.md` should stay user-facing.
- Development notes, compatibility caveats, and planning material should live under `docs/`.
- The current package intentionally preserves some compatibility behavior from the bundled computer-use agent while the public interface is stabilized.
