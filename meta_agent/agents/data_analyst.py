"""Data Analyst sub-agent.

Handles all quantitative work: forecasting, ML models, Monte Carlo
simulations, EDA, and interactive dashboards.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class DataAnalyst:
    """Execute analytical and modelling tasks for data-science projects."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        """Initialise the Data Analyst.

        Args:
            workspace: Root directory of the multi-agent workspace.
        """
        self.workspace = Path(workspace) if workspace else Path.cwd()

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def run(self, project_name: str, task_type: str, data_dir: Path,
            output_dir: Path, brief: dict[str, Any]) -> dict[str, Any]:
        """Run the appropriate analysis for the given task type.

        Args:
            project_name: Name of the current project.
            task_type: Canonical task type (forecast, ml, monte_carlo, eda, etc.).
            data_dir: Path to the project data directory.
            output_dir: Path to the project outputs directory.
            brief: Parsed brief dictionary.

        Returns:
            A summary dict with ``status``, ``outputs``, and ``findings``.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        dispatch = {
            "forecast": self.run_forecast,
            "ml": self.run_ml,
            "monte_carlo": self.run_monte_carlo,
            "eda": self.run_eda,
            "dashboard": self.run_eda,   # dashboard starts with EDA
            "pipeline": self.run_eda,
        }

        handler = dispatch.get(task_type, self.run_eda)
        result = handler(
            data_dir=data_dir,
            output_dir=output_dir,
            config=brief,
        )

        # Write findings.md for the Knowledge Curator
        self._write_findings(output_dir, project_name, task_type, result)

        return result

    # ------------------------------------------------------------------
    # Analytical methods
    # ------------------------------------------------------------------

    def run_forecast(self, data_dir: Path, output_dir: Path,
                     config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a time-series forecast.

        Produces a forecast CSV and an evaluation summary. If real data is
        available in *data_dir*, uses it; otherwise generates a synthetic
        series for demonstration.

        Args:
            data_dir: Directory containing raw/processed data.
            output_dir: Where to write outputs.
            config: Optional configuration from the brief.

        Returns:
            Summary dict with keys ``status``, ``outputs``, ``metrics``.
        """
        df = self._load_or_generate_ts(data_dir)

        # Simple exponential-smoothing baseline
        train = df.iloc[: int(len(df) * 0.8)]
        test = df.iloc[int(len(df) * 0.8):]

        alpha = 0.3
        forecast_values = []
        level = float(train["value"].iloc[0])
        for val in train["value"]:
            level = alpha * val + (1 - alpha) * level
        for _ in range(len(test)):
            forecast_values.append(level)

        test = test.copy()
        test["forecast"] = forecast_values
        test["lower_95"] = test["forecast"] - 1.96 * float(train["value"].std())
        test["upper_95"] = test["forecast"] + 1.96 * float(train["value"].std())

        mae = float(np.mean(np.abs(test["value"] - test["forecast"])))
        rmse = float(np.sqrt(np.mean((test["value"] - test["forecast"]) ** 2)))

        # Save outputs
        forecast_path = output_dir / "forecast.csv"
        test.to_csv(forecast_path, index=False)

        eval_path = output_dir / "model_eval.csv"
        pd.DataFrame([{"model": "exp_smoothing", "MAE": mae, "RMSE": rmse}]).to_csv(
            eval_path, index=False
        )

        return {
            "status": "complete",
            "outputs": ["forecast.csv", "model_eval.csv"],
            "metrics": {"MAE": round(mae, 4), "RMSE": round(rmse, 4)},
        }

    def run_ml(self, data_dir: Path, output_dir: Path,
               config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a machine-learning pipeline.

        Trains a simple model (sklearn) and reports metrics. Falls back to
        synthetic data if none is found in *data_dir*.

        Args:
            data_dir: Directory containing raw/processed data.
            output_dir: Where to write outputs.
            config: Optional configuration from the brief.

        Returns:
            Summary dict.
        """
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, f1_score

        df = self._load_or_generate_classification(data_dir)
        feature_cols = [c for c in df.columns if c != "target"]
        X = df[feature_cols]
        y = df["target"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42,
        )

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))
        f1 = float(f1_score(y_test, y_pred, average="weighted"))

        # Save outputs
        pred_path = output_dir / "predictions.csv"
        pd.DataFrame({"actual": y_test, "predicted": y_pred}).to_csv(
            pred_path, index=False
        )

        eval_path = output_dir / "model_eval.csv"
        pd.DataFrame([{
            "model": "random_forest",
            "accuracy": acc,
            "f1_weighted": f1,
        }]).to_csv(eval_path, index=False)

        importance_path = output_dir / "feature_importance.csv"
        pd.DataFrame({
            "feature": feature_cols,
            "importance": model.feature_importances_,
        }).sort_values("importance", ascending=False).to_csv(
            importance_path, index=False
        )

        return {
            "status": "complete",
            "outputs": [
                "predictions.csv",
                "model_eval.csv",
                "feature_importance.csv",
            ],
            "metrics": {
                "accuracy": round(acc, 4),
                "f1_weighted": round(f1, 4),
            },
        }

    def run_monte_carlo(self, data_dir: Path, output_dir: Path,
                        config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a Monte Carlo simulation.

        Uses scipy for sampling. Parameters come from *config* or defaults.

        Args:
            data_dir: Directory containing raw/processed data.
            output_dir: Where to write outputs.
            config: Simulation parameters.

        Returns:
            Summary dict with percentile statistics.
        """
        n_simulations = 10_000
        params = config or {}

        # Default: simple revenue model  revenue = price * quantity
        price_mean = float(params.get("price_mean", 100))
        price_std = float(params.get("price_std", 15))
        qty_mean = float(params.get("qty_mean", 500))
        qty_std = float(params.get("qty_std", 80))

        rng = np.random.default_rng(42)
        prices = rng.normal(price_mean, price_std, n_simulations)
        quantities = rng.normal(qty_mean, qty_std, n_simulations)
        revenue = prices * quantities

        stats = {
            "mean": float(np.mean(revenue)),
            "median": float(np.median(revenue)),
            "std": float(np.std(revenue)),
            "P5": float(np.percentile(revenue, 5)),
            "P25": float(np.percentile(revenue, 25)),
            "P75": float(np.percentile(revenue, 75)),
            "P95": float(np.percentile(revenue, 95)),
        }

        # Save outputs
        sim_path = output_dir / "simulation_results.csv"
        pd.DataFrame({
            "price": prices,
            "quantity": quantities,
            "revenue": revenue,
        }).to_csv(sim_path, index=False)

        stats_path = output_dir / "simulation_stats.csv"
        pd.DataFrame([stats]).to_csv(stats_path, index=False)

        return {
            "status": "complete",
            "outputs": ["simulation_results.csv", "simulation_stats.csv"],
            "metrics": {k: round(v, 2) for k, v in stats.items()},
        }

    def run_eda(self, data_dir: Path, output_dir: Path,
                config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run exploratory data analysis.

        Produces descriptive statistics and a data profile summary.

        Args:
            data_dir: Directory containing raw/processed data.
            output_dir: Where to write outputs.
            config: Optional configuration.

        Returns:
            Summary dict.
        """
        df = self._load_first_csv(data_dir)
        if df is None:
            df = self._generate_sample_data()

        profile: dict[str, Any] = {
            "shape": list(df.shape),
            "columns": list(df.columns),
            "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
            "null_counts": {str(k): int(v) for k, v in df.isnull().sum().items()},
            "describe": df.describe().to_dict(),
        }

        profile_path = output_dir / "eda_profile.json"
        profile_path.write_text(
            json.dumps(profile, indent=2, default=str), encoding="utf-8",
        )

        desc_path = output_dir / "descriptive_stats.csv"
        df.describe().to_csv(desc_path)

        return {
            "status": "complete",
            "outputs": ["eda_profile.json", "descriptive_stats.csv"],
            "metrics": {"rows": df.shape[0], "columns": df.shape[1]},
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_first_csv(data_dir: Path) -> pd.DataFrame | None:
        """Try to load the first CSV found in data_dir (recursive)."""
        for p in sorted(data_dir.rglob("*.csv")):
            try:
                return pd.read_csv(p)
            except Exception:
                continue
        return None

    @staticmethod
    def _load_or_generate_ts(data_dir: Path) -> pd.DataFrame:
        """Load time-series data or generate a synthetic one."""
        csv = DataAnalyst._load_first_csv(data_dir)
        if csv is not None and "date" in csv.columns and "value" in csv.columns:
            return csv

        rng = np.random.default_rng(42)
        dates = pd.date_range("2023-01-01", periods=120, freq="MS")
        trend = np.linspace(100, 200, 120)
        seasonal = 10 * np.sin(np.linspace(0, 4 * np.pi, 120))
        noise = rng.normal(0, 5, 120)
        return pd.DataFrame({"date": dates, "value": trend + seasonal + noise})

    @staticmethod
    def _load_or_generate_classification(data_dir: Path) -> pd.DataFrame:
        """Load classification data or generate synthetic."""
        csv = DataAnalyst._load_first_csv(data_dir)
        if csv is not None and "target" in csv.columns:
            return csv

        rng = np.random.default_rng(42)
        n = 500
        return pd.DataFrame({
            "feature_1": rng.normal(0, 1, n),
            "feature_2": rng.normal(0, 1, n),
            "feature_3": rng.normal(0, 1, n),
            "target": rng.integers(0, 2, n),
        })

    @staticmethod
    def _generate_sample_data() -> pd.DataFrame:
        """Generate a small sample DataFrame for EDA."""
        rng = np.random.default_rng(42)
        n = 200
        return pd.DataFrame({
            "id": range(1, n + 1),
            "value_a": rng.normal(50, 10, n),
            "value_b": rng.exponential(5, n),
            "category": rng.choice(["A", "B", "C"], n),
        })

    @staticmethod
    def _write_findings(output_dir: Path, project_name: str,
                        task_type: str,
                        result: dict[str, Any]) -> None:
        """Write findings.md for the Knowledge Curator."""
        today = datetime.now().strftime("%Y-%m-%d")
        metrics = result.get("metrics", {})
        metric_lines = "\n".join(f"- **{k}:** {v}" for k, v in metrics.items())
        outputs_lines = "\n".join(
            f"- `outputs/{o}`" for o in result.get("outputs", [])
        )

        content = (
            f"# Findings: {project_name}\n"
            f"**Analyst:** Data Analyst Agent\n"
            f"**Date:** {today}\n"
            f"**Task type:** {task_type}\n\n"
            f"## Key Results\n{metric_lines}\n\n"
            f"## Outputs Produced\n{outputs_lines}\n\n"
            f"## Assumptions & Caveats\n"
            f"- Synthetic/demo data used if real data was unavailable\n"
        )
        (output_dir / "findings.md").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    analyst = DataAnalyst()
    print(analyst.run_eda(
        data_dir=Path("data"),
        output_dir=Path("outputs"),
    ))
