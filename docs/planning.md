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
