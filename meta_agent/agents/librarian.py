"""Librarian sub-agent.

Manages data sources: cataloging, validation, registration, and
manifest production. Always runs first in any workflow.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class Librarian:
    """Catalog, validate, and register data sources for projects."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        """Initialise the Librarian.

        Args:
            workspace: Root directory of the multi-agent workspace.
        """
        self.workspace = Path(workspace) if workspace else Path.cwd()

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def run(self, project_name: str, brief: dict[str, Any],
            data_dir: Path) -> dict[str, Any]:
        """Run the full librarian pipeline for a project.

        Args:
            project_name: Name of the current project.
            brief: Parsed brief dictionary.
            data_dir: Path to the project data directory.

        Returns:
            Summary dict with ``status``, ``sources``, ``manifest_path``.
        """
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "raw").mkdir(exist_ok=True)
        (data_dir / "processed").mkdir(exist_ok=True)

        sources = brief.get("data_sources", [])
        profiles = self.catalog_sources(sources, data_dir)
        manifest_path = self.produce_manifest(project_name, profiles, data_dir)
        self.register_sources(project_name, profiles)

        return {
            "status": "complete",
            "sources": [p["name"] for p in profiles],
            "manifest_path": str(manifest_path),
        }

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def catalog_sources(self, sources: list[str],
                        data_dir: Path) -> list[dict[str, Any]]:
        """Load and profile each data source.

        Args:
            sources: List of source paths or descriptions from the brief.
            data_dir: Project data directory to scan for existing files.

        Returns:
            A list of profile dicts, one per source found.
        """
        profiles: list[dict[str, Any]] = []

        # First try the listed sources
        for src in sources:
            path = Path(src)
            if path.exists() and path.suffix == ".csv":
                profiles.append(self._profile_csv(path))

        # Also scan data/raw for any CSVs already placed there
        raw_dir = data_dir / "raw"
        if raw_dir.exists():
            for csv_file in sorted(raw_dir.glob("*.csv")):
                if not any(p["original_path"] == str(csv_file) for p in profiles):
                    profiles.append(self._profile_csv(csv_file))

        # If nothing found, note that
        if not profiles:
            profiles.append({
                "name": "no-data-found",
                "original_path": str(data_dir),
                "format": "N/A",
                "shape": [0, 0],
                "columns": [],
                "null_counts": {},
                "issues": ["No data files found — will use synthetic data"],
            })

        return profiles

    def validate_data(self, df: pd.DataFrame) -> list[dict[str, str]]:
        """Check data quality and return a list of issues.

        Args:
            df: DataFrame to validate.

        Returns:
            List of dicts with keys ``issue``, ``column``, ``severity``,
            ``recommendation``.
        """
        issues: list[dict[str, str]] = []

        # Check for null columns
        null_pct = df.isnull().mean()
        for col in null_pct.index:
            pct = float(null_pct[col])
            if pct > 0.5:
                issues.append({
                    "issue": f"{pct:.0%} null values",
                    "column": str(col),
                    "severity": "High",
                    "recommendation": "Drop column or impute values",
                })
            elif pct > 0.1:
                issues.append({
                    "issue": f"{pct:.0%} null values",
                    "column": str(col),
                    "severity": "Medium",
                    "recommendation": "Impute or investigate missing pattern",
                })

        # Check for duplicate rows
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            issues.append({
                "issue": f"{dup_count} duplicate rows",
                "column": "ALL",
                "severity": "Medium" if dup_count < len(df) * 0.05 else "High",
                "recommendation": "Deduplicate before analysis",
            })

        # Check for constant columns
        for col in df.columns:
            if df[col].nunique() <= 1:
                issues.append({
                    "issue": "Constant column (no variance)",
                    "column": str(col),
                    "severity": "Low",
                    "recommendation": "Consider dropping — no predictive value",
                })

        return issues

    def produce_manifest(self, project_name: str,
                         profiles: list[dict[str, Any]],
                         data_dir: Path) -> Path:
        """Write a data manifest to ``data/manifest.md``.

        Args:
            project_name: Name of the current project.
            profiles: List of source profiles from ``catalog_sources``.
            data_dir: Project data directory.

        Returns:
            Path to the written manifest file.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# Data Manifest: {project_name}",
            f"**Prepared by:** Librarian Agent",
            f"**Date:** {today}",
            "",
            "## Data Sources",
            "",
        ]

        for i, prof in enumerate(profiles, 1):
            lines.append(f"### Source {i}: {prof['name']}")
            lines.append(f"- **Original path:** `{prof['original_path']}`")
            lines.append(f"- **Format:** {prof.get('format', 'N/A')}")
            shape = prof.get("shape", [0, 0])
            lines.append(f"- **Shape:** {shape[0]} rows × {shape[1]} columns")
            cols = prof.get("columns", [])
            if cols:
                lines.append(f"- **Key columns:** {', '.join(cols[:10])}")
            nulls = prof.get("null_counts", {})
            if nulls:
                null_str = ", ".join(f"{k}: {v}" for k, v in nulls.items() if v > 0)
                if null_str:
                    lines.append(f"- **Null counts:** {null_str}")
            issues = prof.get("issues", [])
            if issues:
                lines.append(f"- **Notes:** {'; '.join(issues)}")
            lines.append("")

        lines.append("## Ready for Analysis")
        has_real_data = any(p["name"] != "no-data-found" for p in profiles)
        lines.append(f"- [{'x' if has_real_data else ' '}] All sources accessible")
        lines.append(f"- [{'x' if has_real_data else ' '}] Raw copies in `data/raw/`")

        manifest_path = data_dir / "manifest.md"
        manifest_path.write_text("\n".join(lines), encoding="utf-8")
        return manifest_path

    def register_sources(self, project_name: str,
                         profiles: list[dict[str, Any]]) -> None:
        """Append source entries to the shared registry.

        Args:
            project_name: Name of the current project.
            profiles: Source profiles to register.
        """
        registry_path = self.workspace / "shared" / "data-sources" / "registry.md"
        if not registry_path.exists():
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(
                "# Data Source Registry\n\n", encoding="utf-8",
            )

        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[str] = []
        for prof in profiles:
            if prof["name"] == "no-data-found":
                continue
            entries.append(
                f"\n## {prof['name']}\n"
                f"- **First used:** {project_name} — {today}\n"
                f"- **Location:** `{prof['original_path']}`\n"
                f"- **Format:** {prof.get('format', 'N/A')}\n"
                f"- **Description:** {prof.get('shape', [0,0])[0]} rows, "
                f"{prof.get('shape', [0,0])[1]} columns\n"
            )

        if entries:
            with open(registry_path, "a", encoding="utf-8") as f:
                f.writelines(entries)

    def register_source(self, source_info: dict[str, Any]) -> None:
        """Register a single source entry.

        Args:
            source_info: Dict with at minimum ``name``, ``path``, ``format``.
        """
        self.register_sources(
            source_info.get("project", "unknown"),
            [self._make_profile(source_info)],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _profile_csv(path: Path) -> dict[str, Any]:
        """Profile a CSV file and return a summary dict."""
        try:
            df = pd.read_csv(path, nrows=10_000)
        except Exception as exc:
            return {
                "name": path.stem,
                "original_path": str(path),
                "format": "CSV",
                "shape": [0, 0],
                "columns": [],
                "null_counts": {},
                "issues": [f"Failed to read: {exc}"],
            }

        return {
            "name": path.stem,
            "original_path": str(path),
            "format": "CSV",
            "shape": list(df.shape),
            "columns": list(df.columns),
            "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
            "null_counts": {str(k): int(v) for k, v in df.isnull().sum().items()},
            "issues": [],
        }

    @staticmethod
    def _make_profile(source_info: dict[str, Any]) -> dict[str, Any]:
        """Convert a simple source_info dict into a profile dict."""
        return {
            "name": source_info.get("name", "unnamed"),
            "original_path": source_info.get("path", "unknown"),
            "format": source_info.get("format", "N/A"),
            "shape": source_info.get("shape", [0, 0]),
            "columns": source_info.get("columns", []),
            "null_counts": {},
            "issues": [],
        }


if __name__ == "__main__":
    lib = Librarian()
    print(lib.validate_data(pd.DataFrame({"a": [1, None, 3], "b": [4, 5, 6]})))
