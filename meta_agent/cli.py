"""CLI entry point for the meta-agent system.

Usage::

    python -m meta_agent run --project sales-forecast
    python -m meta_agent run --project churn-model --task ml
    python -m meta_agent status --project sales-forecast
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from meta_agent.orchestrator import MetaAgent


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and dispatch to the orchestrator.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).
    """
    parser = argparse.ArgumentParser(
        prog="meta_agent",
        description="Meta-Agent: orchestrate data-science projects with "
                    "specialized sub-agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- run ---
    run_parser = subparsers.add_parser(
        "run",
        help="Run the meta-agent pipeline for a project.",
    )
    run_parser.add_argument(
        "--project", required=True,
        help="Project name (must have projects/<name>/brief.md).",
    )
    run_parser.add_argument(
        "--task", default=None,
        help="Override task type (forecast, ml, monte_carlo, eda, dashboard).",
    )
    run_parser.add_argument(
        "--brief", default=None,
        help="Path to brief.md (defaults to projects/<project>/brief.md).",
    )
    run_parser.add_argument(
        "--workspace", default=None,
        help="Workspace root directory (default: current directory).",
    )

    # --- status ---
    status_parser = subparsers.add_parser(
        "status",
        help="Check the status of a project.",
    )
    status_parser.add_argument(
        "--project", required=True,
        help="Project name to check.",
    )
    status_parser.add_argument(
        "--workspace", default=None,
        help="Workspace root directory (default: current directory).",
    )

    args = parser.parse_args(argv)
    workspace = Path(args.workspace) if args.workspace else Path.cwd()
    agent = MetaAgent(workspace=workspace)

    if args.command == "run":
        print(f"🚀 Meta-Agent: running project '{args.project}'...")
        try:
            result = agent.run(
                project_name=args.project,
                brief_path=args.brief,
                task_override=args.task,
            )
            print(f"✅ Project '{args.project}' complete!")
            print(f"   Status: {result['status']}")
            print(f"   Outputs: {', '.join(result['outputs']) or '(none)'}")
            print(f"   Log: {result['log_path']}")
        except FileNotFoundError as exc:
            print(f"❌ Error: {exc}", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"❌ Pipeline failed: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "status":
        result = agent.status(args.project)
        print(f"📋 Project: {result['project']}")
        print(f"   Exists: {'Yes' if result['exists'] else 'No'}")
        if result["outputs"]:
            print(f"   Outputs: {', '.join(result['outputs'])}")
        else:
            print("   Outputs: (none)")
        if result["log"]:
            print(f"\n--- Log ---\n{result['log']}")


if __name__ == "__main__":
    main()
