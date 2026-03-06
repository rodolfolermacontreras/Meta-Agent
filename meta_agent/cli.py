"""CLI entry point for the meta-agent system.

Usage::

    python -m meta_agent run --project sales-forecast
    python -m meta_agent run --project churn-model --task ml
    python -m meta_agent status --project sales-forecast
    python -m meta_agent list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from meta_agent import __version__
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
    parser.add_argument(
        "--version", action="version",
        version=f"meta-agent v{__version__}",
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
    run_parser.add_argument(
        "--verbose", action="store_true",
        help="Print each pipeline step as it runs.",
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

    # --- list ---
    list_parser = subparsers.add_parser(
        "list",
        help="List all projects and their status.",
    )
    list_parser.add_argument(
        "--workspace", default=None,
        help="Workspace root directory (default: current directory).",
    )

    args = parser.parse_args(argv)
    workspace = Path(args.workspace) if getattr(args, "workspace", None) else Path.cwd()
    agent = MetaAgent(workspace=workspace)

    if args.command == "run":
        print(f"🚀 Meta-Agent: running project '{args.project}'...")
        try:
            result = agent.run(
                project_name=args.project,
                brief_path=args.brief,
                task_override=args.task,
                verbose=getattr(args, "verbose", False),
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
            lines: list[str] = []
            out_dir = workspace / "projects" / args.project / "outputs"
            for name in result["outputs"]:
                fpath = out_dir / name
                if fpath.exists():
                    size = fpath.stat().st_size
                    lines.append(f"{name} ({_human_size(size)})")
                else:
                    lines.append(name)
            print(f"   Outputs: {', '.join(lines)}")
        else:
            print("   Outputs: (none)")
        if result["log"]:
            print(f"\n--- Log ---\n{result['log']}")

    elif args.command == "list":
        projects_dir = workspace / "projects"
        if not projects_dir.exists():
            print("No projects/ directory found.")
            sys.exit(0)
        entries = sorted(p for p in projects_dir.iterdir() if p.is_dir())
        if not entries:
            print("No projects found.")
            sys.exit(0)
        print(f"📂 Found {len(entries)} project(s):\n")
        for proj in entries:
            has_brief = (proj / "brief.md").exists()
            has_log = (proj / "log.md").exists()
            outputs = [
                f.name for f in proj.rglob("*")
                if f.is_file() and f.name not in ("brief.md", "pipeline.log")
                and "data/raw" not in f.as_posix()
            ]
            status_icon = "✅" if has_log else ("📝" if has_brief else "❓")
            print(f"  {status_icon} {proj.name}")
            print(f"      Brief: {'Yes' if has_brief else 'No'}  |  "
                  f"Ran: {'Yes' if has_log else 'No'}  |  "
                  f"Outputs: {len(outputs)}")


def _human_size(nbytes: int) -> str:
    """Convert bytes to a human-readable size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes:.1f} {unit}"
        nbytes /= 1024  # type: ignore[assignment]
    return f"{nbytes:.1f} TB"


if __name__ == "__main__":
    main()
