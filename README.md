# GUI-Tester

GUI-tester is a framework for automating web-GUI testing through natural language prompts using a GUI testing AI agent. It is intended as a tool to allow AI coding agents to iteratively test the GUIs they build. It can also be used directly by humans in the CLI. 

It provides:
- a local stdio MCP server for coding-assistant integrations
- a direct CLI for manually running the tester
- bundled `comp_use` support code used by the agent to interact with GUIs.


> **Notes:** 
> - Currently only web-GUIs are supported.
> - Currently only Windows is supported. On Linux the computer-use agent can have issues creating the browser with Playwright.

## Getting Started

1) API Key Setup:

    - The default config uses `gpt-5.4` (as the computer-use agent), which expects `OPENAI_API_KEY`. To test with the default settings, an OpenAI API key is required. For help creating an OpenAI API key see the [OpenAI Docs](https://developers.openai.com/api/docs/quickstart#create-and-export-an-api-key).
    - Other model configs may use different API key names. 

    > **Note:** Advanced users may override the computer-use model and API key name via the CLI, but this feature is not yet supported for the MCP.

2) Package Setup:

    - Complete all the steps under [Package Setup](/README.md#package-setup)

3) Choose the path that fits your workflow:

    | | Best for |
    |---|---|
    | **[GUI-Tester CLI](/README.md#gui-tester-cli)** | Human driven testing |
    | **[GUI-Tester MCP](/README.md#gui-tester-mcp)** | Coding agents (Claude Code, Codex) |

## Package Setup

For MCP use, clone this repo separately from the project you want to test. The MCP host should point at this package's virtual environment and install.

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

Upgrade packaging tools:

```bash
python -m pip install --upgrade pip wheel setuptools
```

### Package Install

From this directory:

```powershell
pip install -e .
```

Install the [Playwright](https://playwright.dev/) browser used by the tester:

```powershell
playwright install chromium
```

<details>
<summary>Optional dotenv support</summary>

Optional local development convenience:

```powershell
pip install -e .[dev]
```

The optional `dev` extra installs `python-dotenv`. Normal CLI and MCP usage should pass API keys through the shell or MCP host environment. Some bundled compatibility paths can use a local `.env` file when `python-dotenv` is available, but `.env` loading is not the primary package interface.
</details>

---

## GUI-Tester CLI

The GUI-Tester command-line interface is intended for Human use. It allows you to directly run the GUI tester agent and view its report and notes. To understand the output see the [output section](/README.md#output).

### API Key

Before CLI use, export your API key.

The default config uses `gpt-5.4`, which expects `OPENAI_API_KEY`. Other models may use different API key names. 

Example API key export (Windows Powershell):

```powershell
$env:OPENAI_API_KEY="sk-your-key"
```

Example API key export (Linux):

```bash
export OPENAI_API_KEY=sk-your-key
```

### CLI Use

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

--- 

## GUI-Tester MCP

A Model Context Protocol (MCP) server that provides web-GUI testing subagent using [Playwright](https://playwright.dev/). This server enables coding agents to test out the GUIs they build using GUI-Tester as a subagent.

### Setup

Standard config works for most of the tools:

```json
{
  "mcpServers": {
    "gui_tester": {
      "type": "stdio",
      "command": "<path-to-venv>/Scripts/python.exe",
      "args": [
        "-m",
        "gui_tester.mcp"
      ],
      "env": {
        "YOUR_API_KEY": "sk-your-key"
      }
    }
  }
}
```

<details>
<summary>Claude Code Setup</summary>

**CLI + VS Code extension** (project scope, creates `.mcp.json` in the project root):

```powershell
claude mcp add gui_tester --scope project --transport stdio --env YOUR_API_KEY=sk-your-key -- <path-to-venv>\Scripts\python.exe -m gui_tester.mcp
```

> **Note:** Add `.mcp.json` to `.gitignore` in the project being tested.

Replace `YOUR_API_KEY` with whatever environment variable name your model config expects, such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

**Then verify the connection:**

In Claude Code, use `/mcp` and ensure `gui_tester` shows `Connected`.

**Notes:**
- After you set up or change the MCP config, start a fresh Claude session and reconnect to the MCP before retesting tool availability.

</details>

<details>
<summary>Codex Setup</summary>

The Codex VS Code extension and CLI share the same `~/.codex/config.toml` file. Configure it once and both tools use it.

**VS Code Extension**

In the Codex sidebar, select the gear icon -> Codex settings -> **MCP Servers** -> **+ Add server** -> **STDIO**, then fill in:

- **Name:** `gui_tester`
- **Command to launch:** `<path-to-venv>\Scripts\python.exe`
- **Arguments:** `-m` and `gui_tester.mcp` (as separate entries)
- **Environment variables:** add your key name (e.g. `OPENAI_API_KEY`) and value

Save and restart the extension.

**CLI**

```powershell
codex mcp add gui_tester --env YOUR_API_KEY=sk-your-key -- <path-to-venv>\Scripts\python.exe -m gui_tester.mcp
```

Replace `YOUR_API_KEY` with whatever environment variable name your model config expects, such as `OPENAI_API_KEY`.

**Verify**

Ask Codex in chat: *"Do you have access to a `launch_gui_tester` tool?"*

</details>

### How it works

Your coding agent can now have a subagent test out the GUI. This is useful to catch visual issues that would be missed by just reviewing the code. 

Ask you coding agent to use the `launch_gui_tester` MCP tool to test out a GUI.

Example prompts:

```text
Call the launch_gui_tester MCP tool with these arguments:

url = file:///C:/path/to/your/gui/index.html
gui_description = A template for a personal website. It includes a landing page, blog page, and resume page. The sidebar on the landing page contains links to other media accounts.
test_instructions = Check all three pages for functionality and visual layout correctness. Report any issues found including visual, layout, and navigation issues. Pay attention to whether the site fits cleanly in the viewport and whether each page looks complete and usable.
report_dir = C:\path\to\your\context\reports
```

```text
I had another coding agent create the personal website template in `guis/personal_webpage`. I gave it the spec.md included in that directory. 

Can you use the launch_gui_tester tool to test this GUI? 

You can use report_dir: C:\path\to\your\context\reports 

If the GUI tester reports issues fix them.

Use the GUI tester tool to test once you make changes. When you are done let me know if any issues have been caught.
```

[Full MCP documentation](/docs/gui_tester_mcp.md)

---

## Development Docs

Development-focused notes, compatibility details, and roadmap material live in `docs/`:
- `docs/dev.md`
- `docs/roadmap.md`
