"""Local stdio MCP server for the GUI tester."""

from __future__ import annotations

import anyio
from pydantic import BaseModel, Field

from mcp.server import FastMCP

from gui_tester.wrapper import launch_gui_tester_subagent


class LaunchGuiTesterResult(BaseModel):
    """Structured MCP response for a GUI tester run."""

    report_path: str = Field(description="Full path to the final markdown report for the completed test run.")


mcp = FastMCP(
    name="gui_tester",
    instructions=(
        "Use the launch_gui_tester tool to run the GUI testing agent against a supplied URL or local file path. "
        "The caller must provide a report_dir parent directory that the tester can write into."
    ),
)


@mcp.tool(
    name="launch_gui_tester",
    title="Launch GUI Tester",
    description=(
        "Run the GUI testing agent against a provided GUI URL or local file path. "
        "The caller must provide gui_description, test_instructions, and a report_dir parent directory. "
        "The tester creates a timestamped run directory inside report_dir and returns the final report path."
    ),
)
async def launch_gui_tester(
    url: str,
    gui_description: str,
    test_instructions: str,
    report_dir: str,
) -> LaunchGuiTesterResult:
    """Launch the GUI tester and return the final report path."""
    report_path = await anyio.to_thread.run_sync(
        launch_gui_tester_subagent,
        url,
        gui_description,
        test_instructions,
        report_dir,
    )
    return LaunchGuiTesterResult(report_path=report_path)


def main() -> None:
    """Run the GUI tester MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
