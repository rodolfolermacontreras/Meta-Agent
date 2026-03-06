"""Unit tests for the meta-agent system."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from meta_agent.orchestrator import MetaAgent, WORKFLOW_MAP
from meta_agent.agents.data_analyst import DataAnalyst
from meta_agent.agents.librarian import Librarian
from meta_agent.agents.knowledge_curator import KnowledgeCurator

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace with a test project brief."""
    project_dir = tmp_path / "projects" / "test-project"
    project_dir.mkdir(parents=True)

    brief = (
        "# Project Brief: test-project\n\n"
        "**Objective:** Forecast monthly sales for the next 12 months\n\n"
        "**Task type:** Forecast\n\n"
        "**Data sources:**\n"
        "- data/raw/sales.csv\n\n"
        "**Deliverables:**\n"
        "- forecast.csv\n"
        "- forecast chart\n\n"
        "**Priority:** High\n"
    )
    (project_dir / "brief.md").write_text(brief, encoding="utf-8")

    # Create shared dirs
    (tmp_path / "shared" / "data-sources").mkdir(parents=True)
    (tmp_path / "shared" / "data-sources" / "registry.md").write_text(
        "# Data Source Registry\n\n", encoding="utf-8",
    )
    (tmp_path / "shared" / "templates").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def ml_workspace(tmp_path: Path) -> Path:
    """Workspace with an ML brief."""
    project_dir = tmp_path / "projects" / "churn-model"
    project_dir.mkdir(parents=True)

    brief = (
        "# Project Brief: churn-model\n\n"
        "**Objective:** Predict customer churn\n\n"
        "**Task type:** ML\n\n"
        "**Data sources:**\n"
        "- data/raw/customers.csv\n\n"
        "**Deliverables:**\n"
        "- trained model\n"
        "- predictions CSV\n\n"
        "**Priority:** Medium\n"
    )
    (project_dir / "brief.md").write_text(brief, encoding="utf-8")
    (tmp_path / "shared" / "data-sources").mkdir(parents=True)
    (tmp_path / "shared" / "data-sources" / "registry.md").write_text(
        "# Data Source Registry\n\n", encoding="utf-8",
    )
    (tmp_path / "shared" / "templates").mkdir(parents=True)
    return tmp_path


# ── Brief Parsing ─────────────────────────────────────────────────────


class TestBriefParsing:
    """Tests for MetaAgent.parse_brief."""

    def test_parse_forecast_brief(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        brief_path = workspace / "projects" / "test-project" / "brief.md"
        result = agent.parse_brief(brief_path)

        assert result["objective"] == "Forecast monthly sales for the next 12 months"
        assert result["task_type"] == "forecast"
        assert result["priority"] == "High"
        assert len(result["data_sources"]) > 0
        assert len(result["deliverables"]) > 0

    def test_parse_ml_brief(self, ml_workspace: Path) -> None:
        agent = MetaAgent(workspace=ml_workspace)
        brief_path = ml_workspace / "projects" / "churn-model" / "brief.md"
        result = agent.parse_brief(brief_path)

        assert result["task_type"] == "ml"
        assert "churn" in result["objective"].lower()

    def test_parse_missing_brief_raises(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        with pytest.raises(FileNotFoundError):
            agent.parse_brief(workspace / "nonexistent.md")


# ── Workflow Selection ────────────────────────────────────────────────


class TestWorkflowSelection:
    """Tests for MetaAgent.select_workflow."""

    def test_forecast_workflow(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        wf = agent.select_workflow("forecast")
        assert "librarian" in wf["agents"]
        assert "data_analyst" in wf["agents"]
        assert "knowledge_curator" in wf["agents"]

    def test_ml_workflow(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        wf = agent.select_workflow("ml")
        assert "data_analyst" in wf["agents"]

    def test_eda_workflow_no_curator(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        wf = agent.select_workflow("eda")
        assert "knowledge_curator" not in wf["agents"]

    def test_unknown_type_raises(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        with pytest.raises(ValueError, match="Unknown task type"):
            agent.select_workflow("teleportation")

    def test_alias_normalisation(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        wf = agent.select_workflow("time-series")
        assert wf == WORKFLOW_MAP["forecast"]

        wf2 = agent.select_workflow("monte carlo")
        assert wf2 == WORKFLOW_MAP["monte_carlo"]


# ── Data Validation (Librarian) ───────────────────────────────────────


class TestDataValidation:
    """Tests for Librarian.validate_data."""

    def test_no_issues_clean_data(self, workspace: Path) -> None:
        lib = Librarian(workspace=workspace)
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        issues = lib.validate_data(df)
        assert issues == []

    def test_high_null_detected(self, workspace: Path) -> None:
        lib = Librarian(workspace=workspace)
        df = pd.DataFrame({"a": [None] * 8 + [1, 2], "b": range(10)})
        issues = lib.validate_data(df)
        null_issues = [i for i in issues if "null" in i["issue"]]
        assert len(null_issues) > 0
        assert null_issues[0]["severity"] == "High"

    def test_duplicates_detected(self, workspace: Path) -> None:
        lib = Librarian(workspace=workspace)
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        issues = lib.validate_data(df)
        dup_issues = [i for i in issues if "duplicate" in i["issue"]]
        assert len(dup_issues) > 0

    def test_constant_column_detected(self, workspace: Path) -> None:
        lib = Librarian(workspace=workspace)
        df = pd.DataFrame({"a": [1, 1, 1], "b": [4, 5, 6]})
        issues = lib.validate_data(df)
        const_issues = [i for i in issues if "Constant" in i["issue"]]
        assert len(const_issues) > 0


# ── Manifest Generation ──────────────────────────────────────────────


class TestManifestGeneration:
    """Tests for Librarian.produce_manifest."""

    def test_manifest_created(self, workspace: Path) -> None:
        lib = Librarian(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        profiles = [{
            "name": "sales",
            "original_path": "/data/sales.csv",
            "format": "CSV",
            "shape": [100, 5],
            "columns": ["date", "value", "region"],
            "null_counts": {"value": 2},
            "issues": [],
        }]

        manifest_path = lib.produce_manifest("test-project", profiles, data_dir)
        assert manifest_path.exists()

        text = manifest_path.read_text(encoding="utf-8")
        assert "test-project" in text
        assert "sales" in text
        assert "100 rows" in text

    def test_manifest_no_data(self, workspace: Path) -> None:
        lib = Librarian(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        profiles = [{
            "name": "no-data-found",
            "original_path": str(data_dir),
            "format": "N/A",
            "shape": [0, 0],
            "columns": [],
            "null_counts": {},
            "issues": ["No data files found"],
        }]

        manifest_path = lib.produce_manifest("test-project", profiles, data_dir)
        assert manifest_path.exists()
        text = manifest_path.read_text(encoding="utf-8")
        assert "no-data-found" in text


# ── End-to-End Pipeline ──────────────────────────────────────────────


class TestEndToEnd:
    """Integration tests: run the full pipeline."""

    def test_forecast_pipeline(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        result = agent.run("test-project")

        assert result["status"] == "complete"
        assert result["project"] == "test-project"
        assert len(result["outputs"]) > 0

        # Check log was written
        log_path = Path(result["log_path"])
        assert log_path.exists()
        log_text = log_path.read_text(encoding="utf-8")
        assert "Complete" in log_text

    def test_ml_pipeline(self, ml_workspace: Path) -> None:
        agent = MetaAgent(workspace=ml_workspace)
        result = agent.run("churn-model")

        assert result["status"] == "complete"
        assert len(result["outputs"]) > 0

    def test_task_override(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        result = agent.run("test-project", task_override="eda")

        assert result["status"] == "complete"

    def test_status_after_run(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        agent.run("test-project")

        status = agent.status("test-project")
        assert status["exists"] is True
        assert len(status["outputs"]) > 0
        assert "Complete" in status["log"]

    def test_status_nonexistent_project(self, workspace: Path) -> None:
        agent = MetaAgent(workspace=workspace)
        status = agent.status("does-not-exist")
        assert status["exists"] is False


# ── CLI ───────────────────────────────────────────────────────────────


class TestCLI:
    """Tests for the CLI entry point."""

    def test_cli_run(self, workspace: Path) -> None:
        from meta_agent.cli import main

        main([
            "run",
            "--project", "test-project",
            "--workspace", str(workspace),
        ])

    def test_cli_status(self, workspace: Path, capsys) -> None:
        from meta_agent.cli import main

        main([
            "status",
            "--project", "test-project",
            "--workspace", str(workspace),
        ])
        captured = capsys.readouterr()
        assert "test-project" in captured.out

    def test_cli_missing_project(self, workspace: Path) -> None:
        from meta_agent.cli import main

        with pytest.raises(SystemExit):
            main([
                "run",
                "--project", "nonexistent",
                "--workspace", str(workspace),
            ])


# ── Real File Loading (Librarian) ────────────────────────────────────


class TestLibrarianRealFiles:
    """Tests for Librarian loading real file formats."""

    def test_librarian_loads_csv(self, workspace: Path) -> None:
        """Load a real CSV fixture and verify profile shape."""
        lib = Librarian(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy(FIXTURES_DIR / "sample_sales.csv", raw_dir / "sample_sales.csv")
        profiles = lib.catalog_sources([], data_dir)

        assert len(profiles) >= 1
        csv_profile = next(p for p in profiles if p["name"] == "sample_sales")
        assert csv_profile["format"] == "CSV"
        assert csv_profile["shape"][0] == 36
        assert csv_profile["shape"][1] == 2
        assert "date" in csv_profile["columns"]
        assert "value" in csv_profile["columns"]

    def test_librarian_loads_excel(self, workspace: Path) -> None:
        """Load a real Excel fixture and verify profile shape."""
        lib = Librarian(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy(
            FIXTURES_DIR / "sample_classification.xlsx",
            raw_dir / "sample_classification.xlsx",
        )
        profiles = lib.catalog_sources([], data_dir)

        xlsx_profile = next(p for p in profiles if p["name"] == "sample_classification")
        assert xlsx_profile["format"] == "Excel"
        assert xlsx_profile["shape"][0] == 100
        assert xlsx_profile["shape"][1] == 4
        assert "target" in xlsx_profile["columns"]

    def test_librarian_loads_parquet(self, workspace: Path) -> None:
        """Load a Parquet fixture and verify profile."""
        lib = Librarian(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy(FIXTURES_DIR / "sample_ts.parquet", raw_dir / "sample_ts.parquet")
        profiles = lib.catalog_sources([], data_dir)

        pq_profile = next(p for p in profiles if p["name"] == "sample_ts")
        assert pq_profile["format"] == "Parquet"
        assert pq_profile["shape"][0] == 60

    def test_librarian_loads_json(self, workspace: Path) -> None:
        """Load a JSON fixture and verify profile."""
        lib = Librarian(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy(FIXTURES_DIR / "sample_data.json", raw_dir / "sample_data.json")
        profiles = lib.catalog_sources([], data_dir)

        json_profile = next(p for p in profiles if p["name"] == "sample_data")
        assert json_profile["format"] == "JSON"
        assert json_profile["shape"][0] == 50


# ── Prophet Forecast ─────────────────────────────────────────────────


class TestForecastWithRealData:
    """Tests for run_forecast with real data fixtures."""

    def test_forecast_with_real_csv(self, workspace: Path) -> None:
        """Run forecast on real fixture data, verify outputs."""
        analyst = DataAnalyst(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        output_dir = workspace / "projects" / "test-project" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy(FIXTURES_DIR / "sample_sales.csv", raw_dir / "sample_sales.csv")

        result = analyst.run_forecast(
            data_dir=data_dir, output_dir=output_dir, config={},
        )

        assert result["status"] == "complete"
        assert (output_dir / "forecast.csv").exists()
        assert (output_dir / "forecast_chart.html").exists()
        assert (output_dir / "model_eval.csv").exists()

        # Verify forecast CSV has expected columns
        fc = pd.read_csv(output_dir / "forecast.csv")
        assert "date" in fc.columns
        assert "yhat" in fc.columns

        # Verify chart is valid HTML
        html = (output_dir / "forecast_chart.html").read_text(encoding="utf-8")
        assert "<html>" in html.lower() or "plotly" in html.lower()


# ── Dashboard Generator ──────────────────────────────────────────────


class TestDashboardGenerator:
    """Tests for run_dashboard."""

    def test_dashboard_generates_app(self, workspace: Path) -> None:
        """Verify dashboard produces a runnable app.py."""
        analyst = DataAnalyst(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        output_dir = workspace / "projects" / "test-project" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy(FIXTURES_DIR / "sample_sales.csv", raw_dir / "sample_sales.csv")

        result = analyst.run_dashboard(
            data_dir=data_dir, output_dir=output_dir, config={},
        )

        assert result["status"] == "complete"
        assert (output_dir / "dashboard" / "app.py").exists()
        assert (output_dir / "dashboard" / "requirements.txt").exists()
        assert (output_dir / "dashboard" / "README.md").exists()
        assert (output_dir / "dashboard" / "data.csv").exists()

        # Verify app.py contains streamlit imports
        app_code = (output_dir / "dashboard" / "app.py").read_text(encoding="utf-8")
        assert "import streamlit" in app_code
        assert "st.title" in app_code

    def test_dashboard_with_generated_data(self, workspace: Path) -> None:
        """Dashboard works even without real data (synthetic fallback)."""
        analyst = DataAnalyst(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir = workspace / "projects" / "test-project" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = analyst.run_dashboard(
            data_dir=data_dir, output_dir=output_dir, config={},
        )

        assert result["status"] == "complete"
        assert (output_dir / "dashboard" / "app.py").exists()


# ── Monte Carlo Outputs ──────────────────────────────────────────────


class TestMonteCarloOutputs:
    """Tests for the upgraded run_monte_carlo."""

    def test_monte_carlo_outputs(self, workspace: Path) -> None:
        """Verify all MC outputs: stats, distribution chart, tornado chart."""
        analyst = DataAnalyst(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir = workspace / "projects" / "test-project" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = analyst.run_monte_carlo(
            data_dir=data_dir, output_dir=output_dir, config={},
        )

        assert result["status"] == "complete"
        assert (output_dir / "simulation_results.csv").exists()
        assert (output_dir / "simulation_stats.csv").exists()
        assert (output_dir / "distribution_chart.html").exists()
        assert (output_dir / "tornado_chart.html").exists()

        # Verify chart files are valid HTML
        dist_html = (output_dir / "distribution_chart.html").read_text(encoding="utf-8")
        assert "plotly" in dist_html.lower()
        tornado_html = (output_dir / "tornado_chart.html").read_text(encoding="utf-8")
        assert "plotly" in tornado_html.lower()

    def test_monte_carlo_percentiles(self, workspace: Path) -> None:
        """Verify P5 < P50 < P95 in simulation stats."""
        analyst = DataAnalyst(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir = workspace / "projects" / "test-project" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        analyst.run_monte_carlo(
            data_dir=data_dir, output_dir=output_dir, config={},
        )

        stats_df = pd.read_csv(output_dir / "simulation_stats.csv")
        assert stats_df["P5"].iloc[0] < stats_df["P50"].iloc[0]
        assert stats_df["P50"].iloc[0] < stats_df["P95"].iloc[0]
        assert stats_df["P10"].iloc[0] < stats_df["P90"].iloc[0]


# ── SHAP in ML Pipeline ─────────────────────────────────────────────


class TestMLWithShap:
    """Tests for SHAP integration in run_ml."""

    def test_ml_with_shap(self, workspace: Path) -> None:
        """Verify run_ml produces shap_summary.html when shap is installed."""
        analyst = DataAnalyst(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir = workspace / "projects" / "test-project" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = analyst.run_ml(
            data_dir=data_dir, output_dir=output_dir, config={},
        )

        assert result["status"] == "complete"
        assert "predictions.csv" in result["outputs"]
        assert "model_eval.csv" in result["outputs"]

        # SHAP is optional — check if installed
        try:
            import shap  # noqa: F401
            assert (output_dir / "shap_summary.html").exists()
            assert "shap_summary.html" in result["outputs"]
            html = (output_dir / "shap_summary.html").read_text(encoding="utf-8")
            assert "plotly" in html.lower()
        except ImportError:
            assert "shap_summary.html" not in result["outputs"]


# ── Dashboard Date Slider ────────────────────────────────────────────


class TestDashboardDateSlider:
    """Tests for date range slider in generated dashboard."""

    def test_dashboard_date_slider(self, workspace: Path) -> None:
        """Verify generated app.py contains st.date_input when date col exists."""
        analyst = DataAnalyst(workspace=workspace)
        data_dir = workspace / "projects" / "test-project" / "data"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        output_dir = workspace / "projects" / "test-project" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Use sample_sales.csv which has a 'date' column
        shutil.copy(FIXTURES_DIR / "sample_sales.csv", raw_dir / "sample_sales.csv")

        analyst.run_dashboard(
            data_dir=data_dir, output_dir=output_dir, config={},
        )

        app_code = (output_dir / "dashboard" / "app.py").read_text(encoding="utf-8")
        assert "st.date_input" in app_code
        assert "Date range" in app_code


# ── CLI Extensions (TASK-004) ────────────────────────────────────────


class TestCLIExtensions:
    """Tests for --version, --verbose, and list subcommand."""

    def test_cli_version(self, capsys) -> None:
        """--version prints the version string and exits."""
        from meta_agent.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "meta-agent v" in captured.out

    def test_cli_verbose_flag(self, workspace: Path, capsys) -> None:
        """--verbose prints pipeline step markers."""
        from meta_agent.cli import main

        main([
            "run",
            "--project", "test-project",
            "--workspace", str(workspace),
            "--verbose",
        ])
        captured = capsys.readouterr()
        assert "[1/5]" in captured.out
        assert "[5/5]" in captured.out

    def test_cli_list_command(self, workspace: Path, capsys) -> None:
        """list subcommand shows projects."""
        from meta_agent.cli import main

        main(["list", "--workspace", str(workspace)])
        captured = capsys.readouterr()
        assert "test-project" in captured.out
        assert "Brief: Yes" in captured.out


# ── Demo Project Smoke Test (TASK-004) ───────────────────────────────


class TestDemoProjects:
    """Verify demo projects can run end-to-end."""

    def test_demo_project_runs(self, tmp_path: Path) -> None:
        """Run a forecast project end-to-end on synthetic data."""
        project_dir = tmp_path / "projects" / "demo"
        project_dir.mkdir(parents=True)
        data_raw = project_dir / "data" / "raw"
        data_raw.mkdir(parents=True)

        brief = (
            "# Demo Brief\n\n"
            "**Objective:** Forecast sales\n\n"
            "**Task type:** Forecast\n\n"
            "**Data sources:**\n- projects/demo/data/raw/demo.csv\n\n"
            "**Deliverables:**\n- Forecast CSV\n\n"
            "**Priority:** High\n"
        )
        (project_dir / "brief.md").write_text(brief, encoding="utf-8")

        dates = pd.date_range("2023-01-01", periods=36, freq="MS")
        vals = np.linspace(100, 200, 36) + np.random.default_rng(1).normal(0, 5, 36)
        pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "value": vals.round(2)}).to_csv(
            data_raw / "demo.csv", index=False,
        )

        agent = MetaAgent(workspace=tmp_path)
        result = agent.run("demo")

        assert result["status"] == "complete"
        assert "forecast.csv" in result["outputs"]
        assert "forecast_chart.html" in result["outputs"]
