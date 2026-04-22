# gui_tester

`gui_tester` is a self-contained GUI testing agent package. It includes:
- a direct CLI for human use
- a local stdio MCP server for coding-assistant integrations
- a bundled copy of the `comp_use` support code it depends on

> **Note:** Currently only Windows is supported. On Linux the computer-use agent can have issues creating the browser.

## Repository Layout

- `gui_tester/` contains the package code, prompts, config, wrapper, custom tools, CLI, and MCP server
- `comp_use/` contains the bundled computer-use support code
- `pyproject.toml` defines the installable package and console entrypoints

## Package Setup

For MCP use, it is recommended to clone this repo separately from the project you want to test. The MCP host should point at this package's virtual environment and install.

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

## Direct CLI

Before CLI use, export your API key.

The default config uses `gpt-5.4`, which expects `OPENAI_API_KEY`. Other models may use different key names. Example:

```powershell
$env:OPENAI_API_KEY="sk-your-key"
```

```bash
export OPENAI_API_KEY=sk-your-key
```

Example CLI usage:

```powershell
gui-tester `
  --url "http://localhost:3000" `
  --gui-description "A small browser game with a start button, score display, and status messages." `
  --test-instructions "Check that the main controls are visible, verify the start button works, and report any obvious UI problems." `
  --report-dir "C:/path/to/context/reports"
```

Module form also works:

```powershell
python -m gui_tester `
  --url "http://localhost:3000" `
  --gui-description "A small browser game with a start button, score display, and status messages." `
  --test-instructions "Check that the main controls are visible, verify the start button works, and report any obvious UI problems." `
  --report-dir "C:/path/to/context/reports"
```

Required arguments:
- `--url`
- `--gui-description`
- `--test-instructions`
- `--report-dir`

Optional arguments:
- `--config`

## Output

Each run creates a timestamped `run_<timestamp>` directory inside the supplied `--report-dir` parent directory.

Run contents:
- `final_report.md`
- `notes/`
- `screenshots/`
- `tool_calls/`
- `gui_tester_run.log`

The final report links to notes, and notes link to screenshots when attached.

## MCP Server

The package includes a local stdio MCP server with:
- server name: `gui_tester`
- tool name: `launch_gui_tester`

Tool inputs:
- `url`
- `gui_description`
- `test_instructions`
- `report_dir`

Tool output:
- `report_path`

Run the MCP server after installation:

```powershell
gui-tester-mcp
```

Module form also works:

```powershell
python -m gui_tester.mcp
```

## Claude Code Setup

This section is included as one example of how to connect the MCP server from a host tool. The same general pattern applies to other MCP-capable editors and agents.

Example using the installed entrypoint inside the repo virtual environment:

**CLI only** (default local scope, goes into `~/.claude.json`):

```powershell
claude mcp add gui_tester --transport stdio --env YOUR_API_KEY=sk-your-key -- <path-to-venv>\Scripts\python.exe -m gui_tester.mcp
```

**CLI + VS Code extension** (project scope, creates `.mcp.json` in the project root):

```powershell
claude mcp add gui_tester --scope project --transport stdio --env YOUR_API_KEY=sk-your-key -- <path-to-venv>\Scripts\python.exe -m gui_tester.mcp
```

> **Note:** Add `.mcp.json` to `.gitignore`.

Replace `YOUR_API_KEY` with whatever environment variable name your model config expects, such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

Then verify the connection:

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

## Codex Setup

The Codex VS Code extension and CLI share the same `~/.codex/config.toml` file. Configure it once and both tools use it.

### VS Code Extension

In the Codex sidebar, select the gear icon → Codex settings → **MCP Servers** → **+ Add server** → **STDIO**, then fill in:

- **Name:** `gui_tester`
- **Command to launch:** `<path-to-venv>\Scripts\python.exe`
- **Arguments:** `-m` and `gui_tester.mcp` (as separate entries)
- **Environment variables:** add your key name (e.g. `OPENAI_API_KEY`) and value

Save and restart the extension.

### CLI

```powershell
codex mcp add gui_tester --env YOUR_API_KEY=sk-your-key -- <path-to-venv>\Scripts\python.exe -m gui_tester.mcp
```

Replace `YOUR_API_KEY` with whatever environment variable name your model config expects, such as `OPENAI_API_KEY`.

### Verify

Ask Codex in chat: *"Do you have access to a `launch_gui_tester` tool?"*

## Development Docs

Development-focused notes, compatibility details, and planning material live in `docs/`:
- `docs/dev.md`
- `docs/planning.md`
