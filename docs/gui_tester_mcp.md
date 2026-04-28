# GUI-Tester MCP Server

A Model Context Protocol (MCP) server that provides web-GUI testing subagent using [Playwright](https://playwright.dev/). This server enables coding agents to test out the GUIs they build using GUI-Tester as a subagent.

MCP details:
- server name: `gui_tester`
- tool name: `launch_gui_tester`
- tool inputs: `url`, `gui_description`, `test_instructions`, `report_dir`
- tool output: `report_path`

> **Note:** The MCP server processes calls sequentially. If a coding agent issues two `launch_gui_tester` calls simultaneously, the second will wait in a queue and start automatically once the first completes. Parallel execution is not currently supported.

<details>
<summary>Testing</summary>

Run the MCP server after installation:

```powershell
gui-tester-mcp
```

Module form also works:

```powershell
python -m gui_tester.mcp
```

</details>

## Setup

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

**CLI only** (default local scope, goes into `~/.claude.json`):

```powershell
claude mcp add gui_tester --transport stdio --env YOUR_API_KEY=sk-your-key -- <path-to-venv>\Scripts\python.exe -m gui_tester.mcp
```

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

### VS Code Extension

In the Codex sidebar, select the gear icon -> Codex settings -> **MCP Servers** -> **+ Add server** -> **STDIO**, then fill in:

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

</details>

## How it works

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