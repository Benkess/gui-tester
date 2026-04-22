"""Direct CLI for running the GUI tester."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui_tester.wrapper.gui_tester_wrapper import run_gui_tester_session


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run_gui_tester.py",
        description="Run the GUI tester directly against a URL.",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Starting URL for the GUI under test.",
    )
    parser.add_argument(
        "--gui-description",
        required=True,
        help="Description of what the GUI is supposed to do.",
    )
    parser.add_argument(
        "--test-instructions",
        required=True,
        help="Instructions for the GUI testing agent.",
    )
    parser.add_argument(
        "--report-dir",
        required=True,
        help="Parent output directory. A timestamped run subdirectory will be created inside it.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Optional path to an alternate tester config for manual testing/debugging.",
    )

    args = parser.parse_args()

    result = run_gui_tester_session(
        url=args.url,
        gui_description=args.gui_description,
        test_instructions=args.test_instructions,
        report_dir=args.report_dir,
        config_path=args.config,
    )

    print("\nGUI tester run completed.")
    print(f"Final report: {result['report_path']}")
    print(f"Run directory : {result['run_dir']}")
    print(f"Agent log     : {result['log_path']}")


if __name__ == "__main__":
    main()
