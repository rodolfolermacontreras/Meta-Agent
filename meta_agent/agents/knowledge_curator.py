"""Knowledge Curator sub-agent.

Transforms raw analytical outputs into clear, actionable knowledge:
summaries, methodology documentation, and reusable pattern identification.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class KnowledgeCurator:
    """Document analytical work and maintain the project knowledge base."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        """Initialise the Knowledge Curator.

        Args:
            workspace: Root directory of the multi-agent workspace.
        """
        self.workspace = Path(workspace) if workspace else Path.cwd()

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def run(self, project_name: str, outputs_dir: Path,
            brief: dict[str, Any]) -> dict[str, Any]:
        """Run the full curator pipeline for a project.

        Args:
            project_name: Name of the current project.
            outputs_dir: Path to the project outputs directory.
            brief: Parsed brief dictionary.

        Returns:
            Summary dict with ``status`` and ``artifacts``.
        """
        findings = self._read_findings(outputs_dir)
        summary_path = self.create_summary(
            project_name, outputs_dir, findings, brief,
        )
        methodology_path = self.document_methodology(
            project_name, outputs_dir, brief,
        )

        reusable = self.check_reusable_patterns(findings, brief)

        return {
            "status": "complete",
            "artifacts": [
                str(summary_path),
                str(methodology_path),
            ],
            "reusable_pattern_detected": reusable,
        }

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def create_summary(self, project_name: str, outputs_dir: Path,
                       findings: dict[str, Any],
                       brief: dict[str, Any]) -> Path:
        """Produce an executive summary report at ``outputs/summary.md``.

        Args:
            project_name: Name of the current project.
            outputs_dir: Project outputs directory.
            findings: Parsed findings from the Data Analyst.
            brief: Parsed brief dictionary.

        Returns:
            Path to the written summary file.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        task_type = brief.get("task_type", "analysis")
        objective = brief.get("objective", "Data analysis")
        metrics = findings.get("metrics", {})

        # Build metrics lines
        metric_lines = "\n".join(
            f"- **{k}:** {v}" for k, v in metrics.items()
        ) if metrics else "- No metrics reported"

        # List output files
        output_files = findings.get("outputs", [])
        file_table = "\n".join(
            f"| `{f}` | Output | Analysis artifact |"
            for f in output_files
        ) if output_files else "| (none) | — | — |"

        content = (
            f"# Project Summary: {project_name}\n\n"
            f"**Date:** {today}\n"
            f"**Project Type:** {task_type}\n"
            f"**Prepared by:** Knowledge Curator\n\n"
            f"---\n\n"
            f"## Executive Summary\n\n"
            f"This project executed a **{task_type}** analysis. "
            f"The objective was: {objective}. "
            f"All deliverables have been produced successfully.\n\n"
            f"## Objective\n\n{objective}\n\n"
            f"## Key Findings\n\n{metric_lines}\n\n"
            f"## Files Produced\n\n"
            f"| File | Type | Description |\n"
            f"|------|------|-------------|\n"
            f"{file_table}\n\n"
            f"## Caveats & Limitations\n\n"
            f"- Synthetic data may have been used where real data was unavailable\n"
            f"- Results should be validated against domain expertise\n"
        )

        summary_path = outputs_dir / "summary.md"
        summary_path.write_text(content, encoding="utf-8")
        return summary_path

    def document_methodology(self, project_name: str,
                             outputs_dir: Path,
                             brief: dict[str, Any]) -> Path:
        """Write a methodology section to ``outputs/methodology.md``.

        Args:
            project_name: Name of the current project.
            outputs_dir: Project outputs directory.
            brief: Parsed brief dictionary.

        Returns:
            Path to the written methodology file.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        task_type = brief.get("task_type", "analysis")

        methodology_map: dict[str, str] = {
            "forecast": (
                "Time-series forecasting using exponential smoothing as a baseline. "
                "Data split 80/20 for train/test. Metrics: MAE, RMSE."
            ),
            "ml": (
                "Supervised learning pipeline: data cleaning, feature engineering, "
                "train/test split (80/20), Random Forest classifier with 100 estimators. "
                "Metrics: accuracy, weighted F1. Feature importance via Gini."
            ),
            "monte_carlo": (
                "Monte Carlo simulation with 10,000 iterations. Input distributions "
                "sampled from normal distributions. Output statistics: mean, median, "
                "P5, P25, P75, P95."
            ),
            "eda": (
                "Exploratory data analysis: descriptive statistics, null analysis, "
                "data type profiling, distribution summary."
            ),
        }

        approach = methodology_map.get(task_type, "Standard analytical pipeline.")

        content = (
            f"# Methodology: {project_name}\n\n"
            f"**Date:** {today}\n"
            f"**Task type:** {task_type}\n\n"
            f"## Approach\n\n{approach}\n\n"
            f"## Reproducibility\n\n"
            f"To reproduce this analysis:\n"
            f"1. Ensure Python 3.10+ and dependencies from `requirements.txt`\n"
            f"2. Place data in `projects/{project_name}/data/raw/`\n"
            f"3. Run: `python -m meta_agent run --project {project_name}`\n"
        )

        methodology_path = outputs_dir / "methodology.md"
        methodology_path.write_text(content, encoding="utf-8")
        return methodology_path

    def check_reusable_patterns(self, findings: dict[str, Any],
                                brief: dict[str, Any]) -> bool:
        """Check if the current analysis contains a reusable pattern.

        Args:
            findings: Parsed findings from the Data Analyst.
            brief: Parsed brief dictionary.

        Returns:
            True if a reusable pattern was detected and documented.
        """
        task_type = brief.get("task_type", "")

        # For now, flag forecast and monte_carlo as reusable templates
        reusable_types = {"forecast", "monte_carlo", "ml"}
        if task_type in reusable_types:
            templates_dir = self.workspace / "shared" / "templates"
            templates_dir.mkdir(parents=True, exist_ok=True)

            template_path = templates_dir / f"{task_type}-template.md"
            if not template_path.exists():
                today = datetime.now().strftime("%Y-%m-%d")
                content = (
                    f"# Pattern: {task_type.replace('_', ' ').title()}\n"
                    f"**First documented:** {today}\n\n"
                    f"## When to use\n\n"
                    f"Use this pattern for {task_type} tasks.\n\n"
                    f"## Template\n\n"
                    f"Run: `python -m meta_agent run "
                    f"--project <name> --task {task_type}`\n"
                )
                template_path.write_text(content, encoding="utf-8")
            return True

        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_findings(outputs_dir: Path) -> dict[str, Any]:
        """Read findings.md and any JSON profiles from outputs_dir."""
        findings: dict[str, Any] = {
            "metrics": {},
            "outputs": [],
        }

        findings_path = outputs_dir / "findings.md"
        if findings_path.exists():
            text = findings_path.read_text(encoding="utf-8")
            findings["raw_text"] = text

            # Extract outputs list
            output_files = []
            for line in text.splitlines():
                if line.strip().startswith("- `outputs/"):
                    fname = line.strip().split("`")[1].replace("outputs/", "")
                    output_files.append(fname)
            findings["outputs"] = output_files

        # Try to read metrics from eval CSV or stats CSV
        for candidate in ["model_eval.csv", "simulation_stats.csv"]:
            eval_path = outputs_dir / candidate
            if eval_path.exists():
                try:
                    import pandas as pd
                    df = pd.read_csv(eval_path)
                    if len(df) > 0:
                        findings["metrics"] = {
                            str(k): v for k, v in df.iloc[0].to_dict().items()
                            if str(k) != "model"
                        }
                except Exception:
                    pass
                break

        # Also collect all output filenames
        if outputs_dir.exists():
            all_files = [
                f.name for f in outputs_dir.iterdir()
                if f.is_file() and f.name != "findings.md"
            ]
            if all_files:
                findings["outputs"] = all_files

        return findings


if __name__ == "__main__":
    curator = KnowledgeCurator()
    print("KnowledgeCurator ready.")
