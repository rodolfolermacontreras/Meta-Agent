"""Meta-Agent Orchestrator.

Parses project briefs, selects workflows, launches sub-agents in the
correct order, assembles results, and updates project logs.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from meta_agent.agents.librarian import Librarian
from meta_agent.agents.data_analyst import DataAnalyst
from meta_agent.agents.knowledge_curator import KnowledgeCurator


# Workflow mapping: task type → (workflow file, ordered sub-agents)
WORKFLOW_MAP: dict[str, dict[str, Any]] = {
    "forecast": {
        "workflow": "workflows/forecast-workflow.md",
        "agents": ["librarian", "data_analyst", "knowledge_curator"],
    },
    "dashboard": {
        "workflow": "workflows/dashboard-workflow.md",
        "agents": ["librarian", "data_analyst", "knowledge_curator"],
    },
    "monte_carlo": {
        "workflow": "workflows/monte-carlo-workflow.md",
        "agents": ["librarian", "data_analyst", "knowledge_curator"],
    },
    "ml": {
        "workflow": "workflows/ml-workflow.md",
        "agents": ["librarian", "data_analyst", "knowledge_curator"],
    },
    "eda": {
        "workflow": "workflows/ml-workflow.md",
        "agents": ["librarian", "data_analyst"],
    },
    "pipeline": {
        "workflow": "workflows/ml-workflow.md",
        "agents": ["librarian", "data_analyst"],
    },
}

# Recognised aliases for task types
TASK_TYPE_ALIASES: dict[str, str] = {
    "forecasting": "forecast",
    "time-series": "forecast",
    "time series": "forecast",
    "monte carlo": "monte_carlo",
    "montecarlo": "monte_carlo",
    "simulation": "monte_carlo",
    "machine learning": "ml",
    "classification": "ml",
    "regression": "ml",
    "exploratory data analysis": "eda",
    "data exploration": "eda",
    "data pipeline": "pipeline",
}


class MetaAgent:
    """Orchestrator that drives data-science projects end-to-end."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        """Initialise the meta-agent.

        Args:
            workspace: Root directory of the multi-agent workspace.
                       Defaults to the current working directory.
        """
        self.workspace = Path(workspace) if workspace else Path.cwd()
        self.librarian = Librarian(self.workspace)
        self.data_analyst = DataAnalyst(self.workspace)
        self.knowledge_curator = KnowledgeCurator(self.workspace)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, project_name: str, brief_path: str | None = None,
            task_override: str | None = None) -> dict[str, Any]:
        """Run the full meta-agent pipeline for a project.

        Args:
            project_name: Short name for the project (e.g. ``"sales-forecast"``).
            brief_path: Path to the project brief. Defaults to
                ``projects/<project_name>/brief.md``.
            task_override: Optionally force a specific task type instead of
                inferring from the brief.

        Returns:
            A dict with keys ``project``, ``status``, ``outputs``, and
            ``log_path``.
        """
        # Step 1 – Locate and parse the brief
        brief_path = self._resolve_brief(project_name, brief_path)
        brief = self.parse_brief(brief_path)

        # Allow CLI override of task type
        if task_override:
            brief["task_type"] = self._normalise_task_type(task_override)

        # Step 2 – Select workflow
        workflow = self.select_workflow(brief["task_type"])

        # Step 3 – Initialise project structure
        project_dir = self._init_project(project_name, brief)

        # Step 4 – Execute sub-agents in order
        results: dict[str, Any] = {}
        for agent_key in workflow["agents"]:
            results[agent_key] = self._run_agent(
                agent_key, project_name, project_dir, brief,
            )

        # Step 5 – Assemble results
        outputs = self._collect_outputs(project_dir)
        self._update_log(project_dir, project_name, brief, results, outputs)

        return {
            "project": project_name,
            "status": "complete",
            "outputs": outputs,
            "log_path": str(project_dir / "log.md"),
        }

    def status(self, project_name: str) -> dict[str, Any]:
        """Return the current status of a project.

        Args:
            project_name: The project to query.

        Returns:
            A dict with ``project``, ``exists``, ``log``, and ``outputs``.
        """
        project_dir = self.workspace / "projects" / project_name
        log_path = project_dir / "log.md"
        outputs_dir = project_dir / "outputs"

        exists = project_dir.exists()
        log_content = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        output_files = (
            [f.name for f in outputs_dir.iterdir() if f.is_file()]
            if outputs_dir.exists()
            else []
        )

        return {
            "project": project_name,
            "exists": exists,
            "log": log_content,
            "outputs": output_files,
        }

    # ------------------------------------------------------------------
    # Brief parsing
    # ------------------------------------------------------------------

    def parse_brief(self, brief_path: str | Path) -> dict[str, Any]:
        """Parse a project brief markdown file.

        Extracts *Objective*, *Task type*, *Data sources*, *Deliverables*,
        and *Priority* from a brief that uses markdown headers or bold labels.

        Args:
            brief_path: Path to the ``brief.md`` file.

        Returns:
            A dict with keys ``objective``, ``task_type``, ``data_sources``,
            ``deliverables``, and ``priority``.
        """
        path = Path(brief_path)
        if not path.exists():
            raise FileNotFoundError(f"Brief not found: {brief_path}")

        text = path.read_text(encoding="utf-8")
        return self._extract_brief_fields(text)

    def select_workflow(self, task_type: str) -> dict[str, Any]:
        """Return the workflow definition for *task_type*.

        Args:
            task_type: One of the canonical task types (``"forecast"``,
                ``"ml"``, ``"monte_carlo"``, ``"dashboard"``, ``"eda"``,
                ``"pipeline"``).

        Returns:
            Workflow dict with ``workflow`` and ``agents`` keys.

        Raises:
            ValueError: If the task type is unknown.
        """
        normalised = self._normalise_task_type(task_type)
        if normalised not in WORKFLOW_MAP:
            raise ValueError(
                f"Unknown task type '{task_type}'. "
                f"Valid types: {', '.join(WORKFLOW_MAP)}"
            )
        return WORKFLOW_MAP[normalised]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_brief(self, project_name: str,
                       brief_path: str | None) -> str:
        """Resolve brief path, creating a stub if necessary."""
        if brief_path:
            return brief_path
        default = self.workspace / "projects" / project_name / "brief.md"
        if default.exists():
            return str(default)
        raise FileNotFoundError(
            f"No brief found for project '{project_name}'. "
            f"Expected at {default}"
        )

    @staticmethod
    def _normalise_task_type(raw: str) -> str:
        """Normalise a free-text task type to a canonical key."""
        lowered = raw.strip().lower()
        if lowered in WORKFLOW_MAP:
            return lowered
        if lowered in TASK_TYPE_ALIASES:
            return TASK_TYPE_ALIASES[lowered]
        # Fuzzy match: check if any key is a substring
        for key in WORKFLOW_MAP:
            if key in lowered or lowered in key:
                return key
        return lowered

    @staticmethod
    def _extract_brief_fields(text: str) -> dict[str, Any]:
        """Extract structured fields from brief markdown text."""
        fields: dict[str, Any] = {
            "objective": "",
            "task_type": "eda",
            "data_sources": [],
            "deliverables": [],
            "priority": "medium",
        }

        # Pattern: **Label:** value  OR  ## Label\nvalue
        # Note: in markdown the colon may be inside or outside the bold
        for key, patterns in {
            "objective": [
                r"\*\*Objective:?\*\*:?\s*(.+?)(?:\n\n|\n\*\*|\Z)",
                r"##\s*Objective\s*\n(.+?)(?:\n##|\n\*\*|\Z)",
            ],
            "task_type": [
                r"\*\*Task\s*[Tt]ype:?\*\*:?\s*(.+?)(?:\n|\Z)",
                r"##\s*Task\s*[Tt]ype\s*\n(.+?)(?:\n##|\n\*\*|\Z)",
            ],
            "priority": [
                r"\*\*Priority:?\*\*:?\s*(.+?)(?:\n|\Z)",
            ],
        }.items():
            for pat in patterns:
                m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
                if m:
                    fields[key] = m.group(1).strip()
                    break

        # Normalise task type
        fields["task_type"] = MetaAgent._normalise_task_type(
            fields["task_type"]
        )

        # Data sources: list of bullet points
        ds_match = re.search(
            r"\*\*Data\s*sources?:?\*\*:?\s*(.*?)(?:\n\*\*|\n##|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if ds_match:
            lines = ds_match.group(1).strip().splitlines()
            fields["data_sources"] = [
                re.sub(r"^[-*]\s*", "", line).strip()
                for line in lines
                if line.strip()
            ]

        # Deliverables
        deliv_match = re.search(
            r"\*\*Deliverables?:?\*\*:?\s*(.*?)(?:\n\*\*|\n##|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if deliv_match:
            lines = deliv_match.group(1).strip().splitlines()
            fields["deliverables"] = [
                re.sub(r"^[-*]\s*", "", line).strip()
                for line in lines
                if line.strip()
            ]

        return fields

    def _init_project(self, project_name: str,
                      brief: dict[str, Any]) -> Path:
        """Create project directory structure and initial log."""
        project_dir = self.workspace / "projects" / project_name
        for sub in ["data/raw", "data/processed", "notebooks", "outputs"]:
            (project_dir / sub).mkdir(parents=True, exist_ok=True)

        log_path = project_dir / "log.md"
        if not log_path.exists():
            today = datetime.now().strftime("%Y-%m-%d")
            log_path.write_text(
                f"# Project Log: {project_name}\n"
                f"**Started:** {today}\n"
                f"**Task type:** {brief['task_type']}\n"
                f"**Meta-Agent:** Initialized project structure\n"
                f"**Status:** In Progress\n---\n",
                encoding="utf-8",
            )

        return project_dir

    def _run_agent(self, agent_key: str, project_name: str,
                   project_dir: Path, brief: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to the appropriate sub-agent."""
        data_dir = project_dir / "data"
        outputs_dir = project_dir / "outputs"

        if agent_key == "librarian":
            return self.librarian.run(
                project_name=project_name,
                brief=brief,
                data_dir=data_dir,
            )
        elif agent_key == "data_analyst":
            task_type = brief["task_type"]
            return self.data_analyst.run(
                project_name=project_name,
                task_type=task_type,
                data_dir=data_dir,
                output_dir=outputs_dir,
                brief=brief,
            )
        elif agent_key == "knowledge_curator":
            return self.knowledge_curator.run(
                project_name=project_name,
                outputs_dir=outputs_dir,
                brief=brief,
            )
        else:
            raise ValueError(f"Unknown agent: {agent_key}")

    @staticmethod
    def _collect_outputs(project_dir: Path) -> list[str]:
        """List all files in the project outputs directory."""
        outputs_dir = project_dir / "outputs"
        if not outputs_dir.exists():
            return []
        return [
            str(f.relative_to(outputs_dir))
            for f in outputs_dir.rglob("*")
            if f.is_file()
        ]

    @staticmethod
    def _update_log(project_dir: Path, project_name: str,
                    brief: dict[str, Any], results: dict[str, Any],
                    outputs: list[str]) -> None:
        """Append completion entry to the project log."""
        log_path = project_dir / "log.md"
        today = datetime.now().strftime("%Y-%m-%d")

        agents_run = ", ".join(results.keys())
        output_list = "\n".join(f"  - {o}" for o in outputs) if outputs else "  - (none)"

        entry = (
            f"\n## {today} — Pipeline Complete\n"
            f"**Agents executed:** {agents_run}\n"
            f"**Outputs:**\n{output_list}\n"
            f"**Status:** Complete\n"
        )

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)


if __name__ == "__main__":
    agent = MetaAgent()
    result = agent.run("test-project")
    print(result)
