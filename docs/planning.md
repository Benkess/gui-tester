# Planning Notes

This document tracks near-term cleanup, packaging, and UX follow-up work for the project. It is intentionally lightweight so it can evolve during the early stages of development without cluttering the main README.

## Near-Term

- Add cleaner entrypoint-level missing-key and config errors for CLI and MCP startup.
- Add a documented MCP startup environment variable for advanced config overrides such as `GUI_TESTER_CONFIG`.
- Add Copilot MCP setup examples once those flows are validated.
- Remove the remaining hard dependency on `python-dotenv` for normal MCP use.
- Continue tightening the README so it stays user-facing.
- Improve setup instructions where contributors still hit avoidable friction.
- Revisit and verify the Claude Code setup example against the current workflow.

## Packaging Follow-Up

- Re-test the package from a clean second repo or temporary workspace after `pip install -e .`.
- Decide whether the bundled `comp_use` subtree should remain broad or be narrowed later.
- Publish on PyPI once the package flow is stable.

## Behavior and UX Follow-Up

- Improve navigation-click logging so successful navigation clicks do not appear to fail when the overlay step is the part that breaks.
- Revisit note-taking and long-run memory if longer GUI tests start dropping earlier findings due to the sliding context window.
- **Add an optional `max_duration_seconds` timeout to `launch_gui_tester`.** If the agent has not submitted a final report within the timeout, the wrapper should force a report submission and exit cleanly. This prevents the MCP call from hanging indefinitely if the agent gets stuck in a loop or an LLM call stalls.
- **Consider subprocess isolation for parallel execution.** The current implementation enforces sequential calls via a semaphore because `contextlib.redirect_stdout` is not thread-safe and Playwright's sync API carries process-level state between calls. Running each `launch_gui_tester` invocation in a fresh subprocess (e.g. via `ProcessPoolExecutor`) would eliminate both constraints, make concurrent calls safe, and enable two-player testing scenarios where two independent browser sessions need to run simultaneously.
