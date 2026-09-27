"""
polygraph/__main__.py
=====================
Entry-point for ``python -m polygraph <command>``.

Commands
--------
gate on|off|status
    Create or remove ~/.polygraph_private/GATE_OFF.

run start --ticket <id> --gate <on|off>
    Reset demo_repo to baseline, set gate mode, write active_run.json.

run end
    Finalize the active run and clear active_run.json.

run list
    Print experiment/results.csv as a table.

selftest
    End-to-end smoke test (5 checks).
"""

from __future__ import annotations

import argparse
import sys

from polygraph.commands.gate_cmd import cmd_gate
from polygraph.commands.run_cmd import cmd_run
from polygraph.commands.selftest_cmd import cmd_selftest


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m polygraph",
        description="Polygraph experiment automation CLI",
    )
    sub = p.add_subparsers(dest="command", metavar="<command>")

    # --- gate ---
    g = sub.add_parser("gate", help="Control the commit gate")
    g.add_argument("action", choices=["on", "off", "status"])

    # --- run ---
    r = sub.add_parser("run", help="Manage experiment runs")
    r_sub = r.add_subparsers(dest="run_action", metavar="<action>")

    r_start = r_sub.add_parser("start", help="Start a new run")
    r_start.add_argument("--ticket", required=True, metavar="ID",
                         help="Ticket number, e.g. 02")
    r_start.add_argument("--gate", choices=["on", "off"], default="on",
                         help="Gate mode for this run (default: on)")

    r_sub.add_parser("end", help="Finalize the active run")
    r_sub.add_parser("list", help="Print results.csv as a table")

    # --- selftest ---
    sub.add_parser("selftest", help="End-to-end self-test (5 checks)")

    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "gate":
        cmd_gate(args.action)
    elif args.command == "run":
        if not args.run_action:
            parser.parse_args(["run", "--help"])
        else:
            cmd_run(args)
    elif args.command == "selftest":
        cmd_selftest()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
