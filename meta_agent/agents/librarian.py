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

    # Supported file extensions and their format labels
    _SUPPORTED_EXTENSIONS: dict[str, str] = {
        ".csv": "CSV",
        ".xlsx": "Excel",
        ".xls": "Excel",
        ".parquet": "Parquet",
        ".json": "JSON",
    }

    def catalog_sources(self, sources: list[str],
                        data_dir: Path) -> list[dict[str, Any]]:
        """Load, profile, and validate each data source.

        Supports: CSV, Excel (.xlsx/.xls), Parquet, JSON (records orient).

        Args:
            sources: List of source paths or descriptions from the brief.
            data_dir: Project data directory to scan for existing files.

        Returns:
            A list of profile dicts, one per source found.
        """
        profiles: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        # First try the listed sources
        for src in sources:
            path = Path(src)
            if path.exists() and path.suffix.lower() in self._SUPPORTED_EXTENSIONS:
                profile = self._profile_file(path)
                profiles.append(profile)
                seen_paths.add(str(path))

        # Also scan data/raw for any supported files already placed there
        raw_dir = data_dir / "raw"
        if raw_dir.exists():
            for ext in self._SUPPORTED_EXTENSIONS:
                for data_file in sorted(raw_dir.glob(f"*{ext}")):
                    if str(data_file) not in seen_paths:
                        profiles.append(self._profile_file(data_file))
                        seen_paths.add(str(data_file))

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

    @classmethod
    def _profile_file(cls, path: Path) -> dict[str, Any]:
        """Profile a data file (CSV, Excel, Parquet, or JSON).

        Args:
            path: Path to the data file.

        Returns:
            A profile dict with name, shape, dtypes, nulls, etc.
        """
        ext = path.suffix.lower()
        fmt = cls._SUPPORTED_EXTENSIONS.get(ext, ext)

        try:
            df = cls._read_file(path, nrows=10_000)
        except Exception as exc:
            return {
                "name": path.stem,
                "original_path": str(path),
                "format": fmt,
                "shape": [0, 0],
                "columns": [],
                "null_counts": {},
                "issues": [f"Failed to read: {exc}"],
            }

        profile: dict[str, Any] = {
            "name": path.stem,
            "original_path": str(path),
            "format": fmt,
            "shape": list(df.shape),
            "columns": list(df.columns),
            "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
            "null_counts": {str(k): int(v) for k, v in df.isnull().sum().items()},
            "duplicate_rows": int(df.duplicated().sum()),
            "issues": [],
        }

        # Detect date range if any datetime column exists
        date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
        if not date_cols:
            # Try parsing columns named 'date', 'timestamp', etc.
            for col in df.columns:
                if col.lower() in ("date", "timestamp", "datetime", "ds"):
                    try:
                        df[col] = pd.to_datetime(df[col])
                        date_cols.append(col)
                    except Exception:
                        pass
        if date_cols:
            dc = date_cols[0]
            profile["date_range"] = {
                "column": dc,
                "min": str(df[dc].min()),
                "max": str(df[dc].max()),
            }

        return profile

    @staticmethod
    def _read_file(path: Path, nrows: int | None = None) -> pd.DataFrame:
        """Read a data file into a DataFrame based on extension.

        Args:
            path: File path.
            nrows: Maximum rows to read (CSV only).

        Returns:
            A pandas DataFrame.
        """
        ext = path.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(path, nrows=nrows)
        elif ext in (".xlsx", ".xls"):
            import openpyxl  # noqa: F401 — lazy import, needed by pandas
            return pd.read_excel(path, nrows=nrows)
        elif ext == ".parquet":
            df = pd.read_parquet(path)
            if nrows is not None:
                df = df.head(nrows)
            return df
        elif ext == ".json":
            df = pd.read_json(path, orient="records")
            if nrows is not None:
                df = df.head(nrows)
            return df
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    # Keep legacy alias for backward compatibility
    @classmethod
    def _profile_csv(cls, path: Path) -> dict[str, Any]:
        """Profile a CSV file (delegates to ``_profile_file``)."""
        return cls._profile_file(path)

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
