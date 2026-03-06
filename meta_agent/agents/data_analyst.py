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
            "dashboard": self.run_dashboard,
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

        Uses Prophet when available, falling back to exponential smoothing.
        Produces a forecast CSV, an interactive Plotly chart, and evaluation
        metrics.

        Args:
            data_dir: Directory containing raw/processed data.
            output_dir: Where to write outputs.
            config: Optional configuration from the brief.

        Returns:
            Summary dict with keys ``status``, ``outputs``, ``metrics``.
        """
        config = config or {}
        horizon = int(config.get("horizon", 12))
        df = self._load_or_generate_ts(data_dir)

        # Ensure date column is datetime
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Train / test split — last 20 %
        split_idx = int(len(df) * 0.8)
        train = df.iloc[:split_idx].copy()
        test = df.iloc[split_idx:].copy()

        try:
            result = self._forecast_prophet(train, test, horizon)
        except Exception:
            # Fallback: exponential smoothing if Prophet is unavailable
            result = self._forecast_exp_smoothing(train, test)

        forecast_df = result["forecast_df"]
        metrics = result["metrics"]

        # --- Save outputs ---
        forecast_path = output_dir / "forecast.csv"
        forecast_df.to_csv(forecast_path, index=False)

        eval_path = output_dir / "model_eval.csv"
        pd.DataFrame([metrics]).to_csv(eval_path, index=False)

        # Plotly interactive chart
        chart_path = output_dir / "forecast_chart.html"
        self._plot_forecast(df, forecast_df, chart_path)

        return {
            "status": "complete",
            "outputs": ["forecast.csv", "model_eval.csv", "forecast_chart.html"],
            "metrics": {k: round(v, 4) for k, v in metrics.items()
                        if isinstance(v, (int, float))},
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
        # Lazy imports — sklearn is heavy, only load when needed
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

        output_files = [
            "predictions.csv",
            "model_eval.csv",
            "feature_importance.csv",
        ]

        # SHAP values — fully optional, graceful skip if not installed
        try:
            import shap  # lazy import
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_test)

            # Handle different SHAP output shapes:
            # - list of arrays (one per class) → use class 1
            # - 3D array (samples, features, classes) → use class 1
            # - 2D array (samples, features) → use directly
            if isinstance(shap_values, list):
                sv = np.abs(np.array(shap_values[1])).mean(axis=0)
            elif shap_values.ndim == 3:
                sv = np.abs(shap_values[:, :, 1]).mean(axis=0)
            else:
                sv = np.abs(shap_values).mean(axis=0)

            # Ensure 1D
            sv = np.asarray(sv).flatten()

            self._plot_shap_summary(
                feature_names=feature_cols,
                mean_abs_shap=sv,
                chart_path=output_dir / "shap_summary.html",
            )
            output_files.append("shap_summary.html")
        except ImportError:
            pass  # SHAP not installed — skip gracefully

        return {
            "status": "complete",
            "outputs": output_files,
            "metrics": {
                "accuracy": round(acc, 4),
                "f1_weighted": round(f1, 4),
            },
        }

    def run_monte_carlo(self, data_dir: Path, output_dir: Path,
                        config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a full Monte Carlo simulation.

        Fits distributions to input variables (or uses config defaults),
        runs 50 000 iterations, and produces a percentile table, a
        distribution histogram, and a tornado (sensitivity) chart.

        Args:
            data_dir: Directory containing raw/processed data.
            output_dir: Where to write outputs.
            config: Simulation parameters. May contain ``variables`` list
                and ``n_simulations``.

        Returns:
            Summary dict with percentile statistics.
        """
        from scipy import stats as sp_stats  # lazy import

        params = config or {}
        n_simulations = int(params.get("n_simulations", 50_000))
        rng = np.random.default_rng(42)

        # --- Define input variables ---
        variables = params.get("variables", None)
        if variables is None:
            # Default: simple revenue model — revenue = price × quantity
            variables = [
                {"name": "price", "mean": 100, "std": 15},
                {"name": "quantity", "mean": 500, "std": 80},
            ]

        # --- Fit / sample each variable ---
        samples: dict[str, np.ndarray] = {}
        for var in variables:
            name = var["name"]
            mean = float(var.get("mean", 100))
            std = float(var.get("std", 10))
            dist_type = var.get("distribution", "normal").lower()

            if dist_type == "lognormal":
                # Convert mean/std to lognormal mu/sigma
                sigma2 = np.log(1 + (std / mean) ** 2)
                mu = np.log(mean) - sigma2 / 2
                samples[name] = rng.lognormal(mu, np.sqrt(sigma2), n_simulations)
            elif dist_type == "uniform":
                lo = mean - std * np.sqrt(3)
                hi = mean + std * np.sqrt(3)
                samples[name] = rng.uniform(lo, hi, n_simulations)
            else:  # default normal
                samples[name] = rng.normal(mean, std, n_simulations)

        # --- Compute outcome ---
        # Outcome model: first two variables are multiplied (e.g., price × quantity),
        # remaining variables are added.  Override via config["model"] in the future.
        if len(samples) >= 2:
            keys = list(samples.keys())
            outcome = samples[keys[0]] * samples[keys[1]]
            for k in keys[2:]:
                outcome = outcome + samples[k]
        else:
            outcome = list(samples.values())[0]

        # --- Statistics ---
        percentiles = [5, 10, 25, 50, 75, 90, 95, 99]
        stats: dict[str, float] = {
            "mean": float(np.mean(outcome)),
            "median": float(np.median(outcome)),
            "std": float(np.std(outcome)),
        }
        for p in percentiles:
            stats[f"P{p}"] = float(np.percentile(outcome, p))

        # --- Sensitivity: Pearson correlation of each input vs outcome ---
        sensitivities: dict[str, float] = {}
        for name, vals in samples.items():
            corr = float(np.corrcoef(vals, outcome)[0, 1])
            sensitivities[name] = corr

        # --- Save outputs ---
        # Simulation results (sampled to 10k rows to keep file size sane)
        sample_idx = rng.choice(n_simulations, min(10_000, n_simulations), replace=False)
        sim_df = pd.DataFrame({k: v[sample_idx] for k, v in samples.items()})
        sim_df["outcome"] = outcome[sample_idx]
        sim_df.to_csv(output_dir / "simulation_results.csv", index=False)

        # Stats CSV
        pd.DataFrame([stats]).to_csv(output_dir / "simulation_stats.csv", index=False)

        # Plotly distribution chart with percentile lines
        self._plot_distribution(outcome, stats, output_dir / "distribution_chart.html")

        # Plotly tornado chart
        self._plot_tornado(sensitivities, output_dir / "tornado_chart.html")

        return {
            "status": "complete",
            "outputs": [
                "simulation_results.csv",
                "simulation_stats.csv",
                "distribution_chart.html",
                "tornado_chart.html",
            ],
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

    def run_dashboard(self, data_dir: Path, output_dir: Path,
                      config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate a ready-to-run Streamlit dashboard for the project data.

        Produces ``outputs/dashboard/app.py``, a requirements file, and a
        README with run instructions.

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

        # Detect columns
        numeric_cols = list(df.select_dtypes(include=["number"]).columns)
        date_col = None
        for col in df.columns:
            if col.lower() in ("date", "timestamp", "datetime", "ds"):
                date_col = col
                break

        dashboard_dir = output_dir / "dashboard"
        dashboard_dir.mkdir(parents=True, exist_ok=True)

        # Write the Streamlit app
        app_code = self._generate_streamlit_app(
            numeric_cols=numeric_cols,
            date_col=date_col,
            all_cols=list(df.columns),
        )
        (dashboard_dir / "app.py").write_text(app_code, encoding="utf-8")

        # Save data for the dashboard to read
        df.to_csv(dashboard_dir / "data.csv", index=False)

        # requirements.txt
        (dashboard_dir / "requirements.txt").write_text(
            "streamlit>=1.30\npandas>=2.0\nplotly>=5.0\n",
            encoding="utf-8",
        )

        # README
        (dashboard_dir / "README.md").write_text(
            "# Dashboard\n\n"
            "## How to run\n\n"
            "```bash\n"
            "pip install -r requirements.txt\n"
            "streamlit run app.py\n"
            "```\n",
            encoding="utf-8",
        )

        return {
            "status": "complete",
            "outputs": [
                "dashboard/app.py",
                "dashboard/data.csv",
                "dashboard/requirements.txt",
                "dashboard/README.md",
            ],
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

    # ------------------------------------------------------------------
    # Forecasting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _forecast_prophet(train: pd.DataFrame, test: pd.DataFrame,
                          horizon: int) -> dict[str, Any]:
        """Fit Prophet and produce forecast + metrics.

        Raises ImportError if prophet is not installed.
        """
        from prophet import Prophet  # lazy import

        prophet_train = train.rename(columns={"date": "ds", "value": "y"})
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                        daily_seasonality=False)
        model.fit(prophet_train)

        # Predict on test dates
        future_test = test[["date"]].rename(columns={"date": "ds"})
        pred_test = model.predict(future_test)

        actuals = test["value"].values
        predicted = pred_test["yhat"].values
        mae = float(np.mean(np.abs(actuals - predicted)))
        rmse = float(np.sqrt(np.mean((actuals - predicted) ** 2)))
        mape = float(np.mean(np.abs((actuals - predicted) / actuals)) * 100)

        # Forecast into the future
        future = model.make_future_dataframe(periods=horizon, freq="MS")
        forecast_full = model.predict(future)
        forecast_df = forecast_full[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        forecast_df = forecast_df.rename(columns={"ds": "date"})

        return {
            "forecast_df": forecast_df,
            "metrics": {"model": "prophet", "MAE": mae, "RMSE": rmse, "MAPE": mape},
        }

    @staticmethod
    def _forecast_exp_smoothing(train: pd.DataFrame,
                                test: pd.DataFrame) -> dict[str, Any]:
        """Simple exponential smoothing fallback."""
        # TODO: horizon not used — forecast covers test period only, not future periods.
        alpha = 0.3
        level = float(train["value"].iloc[0])
        for val in train["value"]:
            level = alpha * val + (1 - alpha) * level

        forecast_values = [level] * len(test)
        std = float(train["value"].std())

        forecast_df = test[["date"]].copy()
        forecast_df["yhat"] = forecast_values
        forecast_df["yhat_lower"] = forecast_df["yhat"] - 1.96 * std
        forecast_df["yhat_upper"] = forecast_df["yhat"] + 1.96 * std

        actuals = test["value"].values
        predicted = np.array(forecast_values)
        mae = float(np.mean(np.abs(actuals - predicted)))
        rmse = float(np.sqrt(np.mean((actuals - predicted) ** 2)))

        return {
            "forecast_df": forecast_df,
            "metrics": {"model": "exp_smoothing", "MAE": mae, "RMSE": rmse},
        }

    @staticmethod
    def _plot_forecast(original: pd.DataFrame, forecast_df: pd.DataFrame,
                       chart_path: Path) -> None:
        """Create an interactive Plotly chart of actuals + forecast + CI."""
        import plotly.graph_objects as go

        fig = go.Figure()

        # Actuals
        fig.add_trace(go.Scatter(
            x=original["date"], y=original["value"],
            mode="lines+markers", name="Actuals",
            line=dict(color="steelblue"),
        ))

        # Forecast
        fig.add_trace(go.Scatter(
            x=forecast_df["date"], y=forecast_df["yhat"],
            mode="lines", name="Forecast",
            line=dict(color="tomato", dash="dash"),
        ))

        # Confidence interval
        fig.add_trace(go.Scatter(
            x=pd.concat([forecast_df["date"], forecast_df["date"][::-1]]),
            y=pd.concat([forecast_df["yhat_upper"], forecast_df["yhat_lower"][::-1]]),
            fill="toself", fillcolor="rgba(255,99,71,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="95% CI",
        ))

        fig.update_layout(
            title="Forecast — Actuals vs Predicted",
            xaxis_title="Date", yaxis_title="Value",
            template="plotly_white",
        )
        fig.write_html(str(chart_path))

    @staticmethod
    def _generate_streamlit_app(numeric_cols: list[str],
                                date_col: str | None,
                                all_cols: list[str]) -> str:
        """Return the source code for a Streamlit dashboard app.

        Uses ``textwrap.dedent`` for cleaner template generation.
        """
        import textwrap

        num_repr = repr(numeric_cols[:5])
        date_repr = repr(date_col)

        # Build the date-slider block only when a date column exists
        if date_col:
            date_block = textwrap.dedent(f"""\
                # --- Date Range Slider ---
                date_col = {date_repr}
                if date_col and date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col])
                    min_date = df[date_col].min().date()
                    max_date = df[date_col].max().date()
                    date_range = st.date_input(
                        "Date range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date,
                    )
                    if len(date_range) == 2:
                        df = df[
                            (df[date_col] >= pd.Timestamp(date_range[0]))
                            & (df[date_col] <= pd.Timestamp(date_range[1]))
                        ]

                    # --- Time Series ---
                    ts_col = st.selectbox("Metric for time series", numeric_cols, index=0)
                    fig_ts = px.line(
                        df.sort_values(date_col), x=date_col, y=ts_col,
                        title=f"{{ts_col}} over time",
                    )
                    st.plotly_chart(fig_ts, use_container_width=True)
            """)
        else:
            date_block = ""

        template = (
            textwrap.dedent(f"""\
                \"\"\"Auto-generated Streamlit dashboard.\"\"\"

                import streamlit as st
                import pandas as pd
                import plotly.express as px
                from pathlib import Path

                st.set_page_config(page_title="Project Dashboard", layout="wide")
                st.title("📊 Project Dashboard")

                data_path = Path(__file__).parent / "data.csv"
                df = pd.read_csv(data_path)

                # --- KPI Row ---
                numeric_cols = {num_repr}
                cols = st.columns(len(numeric_cols[:4]) or 1)
                for i, col_name in enumerate(numeric_cols[:4]):
                    with cols[i]:
                        st.metric(
                            col_name,
                            f"{{df[col_name].mean():.2f}}",
                            f"max: {{df[col_name].max():.2f}}",
                        )

            """)
            + date_block
            + textwrap.dedent(f"""\
                # --- Distribution ---
                if numeric_cols:
                    dist_col = st.selectbox("Distribution column", numeric_cols, index=0, key="dist")
                    fig_dist = px.histogram(df, x=dist_col, title=f"Distribution of {{dist_col}}")
                    st.plotly_chart(fig_dist, use_container_width=True)

                # --- Data Table ---
                st.subheader("Data Table")
                st.dataframe(df, use_container_width=True)
            """)
        )

        return template

    # ------------------------------------------------------------------
    # Monte Carlo chart helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _plot_distribution(outcome: np.ndarray, stats: dict[str, float],
                           chart_path: Path) -> None:
        """Create a Plotly histogram of the outcome distribution with percentile lines."""
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=outcome, nbinsx=100, name="Outcome",
            marker_color="steelblue", opacity=0.75,
        ))

        colors = {"P5": "red", "P50": "green", "P95": "red"}
        for label in ("P5", "P50", "P95"):
            if label in stats:
                fig.add_vline(
                    x=stats[label],
                    line_dash="dash",
                    line_color=colors.get(label, "grey"),
                    annotation_text=f"{label}: {stats[label]:,.0f}",
                )

        fig.update_layout(
            title="Monte Carlo — Outcome Distribution",
            xaxis_title="Outcome Value",
            yaxis_title="Frequency",
            template="plotly_white",
            showlegend=False,
        )
        fig.write_html(str(chart_path))

    @staticmethod
    def _plot_tornado(sensitivities: dict[str, float],
                      chart_path: Path) -> None:
        """Create a horizontal bar (tornado) chart sorted by |correlation|."""
        import plotly.graph_objects as go

        sorted_items = sorted(
            sensitivities.items(), key=lambda x: abs(x[1]),
        )
        names = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]
        colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in values]

        fig = go.Figure(go.Bar(
            x=values, y=names, orientation="h",
            marker_color=colors,
            text=[f"{v:.3f}" for v in values],
            textposition="outside",
        ))

        fig.update_layout(
            title="Sensitivity Analysis — Pearson Correlation with Outcome",
            xaxis_title="Pearson Correlation",
            yaxis_title="Input Variable",
            template="plotly_white",
            xaxis=dict(range=[-1.1, 1.1]),
        )
        fig.write_html(str(chart_path))

    # ------------------------------------------------------------------
    # SHAP helper
    # ------------------------------------------------------------------

    @staticmethod
    def _plot_shap_summary(feature_names: list[str],
                           mean_abs_shap: np.ndarray,
                           chart_path: Path) -> None:
        """Create a Plotly bar chart of mean |SHAP| per feature."""
        import plotly.graph_objects as go

        order = np.argsort(mean_abs_shap)
        sorted_names = [feature_names[i] for i in order]
        sorted_vals = mean_abs_shap[order]

        fig = go.Figure(go.Bar(
            x=sorted_vals, y=sorted_names, orientation="h",
            marker_color="mediumpurple",
            text=[f"{v:.4f}" for v in sorted_vals],
            textposition="outside",
        ))

        fig.update_layout(
            title="SHAP Feature Importance — mean |SHAP value|",
            xaxis_title="Mean |SHAP value|",
            yaxis_title="Feature",
            template="plotly_white",
        )
        fig.write_html(str(chart_path))


if __name__ == "__main__":
    analyst = DataAnalyst()
    print(analyst.run_eda(
        data_dir=Path("data"),
        output_dir=Path("outputs"),
    ))
