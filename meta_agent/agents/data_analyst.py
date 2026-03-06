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
        """Return the source code for a Streamlit dashboard app."""
        num_repr = repr(numeric_cols[:5])
        date_repr = repr(date_col)
        return f'''"""Auto-generated Streamlit dashboard."""

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
        st.metric(col_name, f"{{df[col_name].mean():.2f}}", f"max: {{df[col_name].max():.2f}}")

# --- Time Series (if date column found) ---
date_col = {date_repr}
if date_col and date_col in df.columns:
    df[date_col] = pd.to_datetime(df[date_col])
    ts_col = st.selectbox("Metric for time series", numeric_cols, index=0)
    fig_ts = px.line(df.sort_values(date_col), x=date_col, y=ts_col, title=f"{{ts_col}} over time")
    st.plotly_chart(fig_ts, use_container_width=True)

# --- Distribution ---
if numeric_cols:
    dist_col = st.selectbox("Distribution column", numeric_cols, index=0, key="dist")
    fig_dist = px.histogram(df, x=dist_col, title=f"Distribution of {{dist_col}}")
    st.plotly_chart(fig_dist, use_container_width=True)

# --- Data Table ---
st.subheader("Data Table")
st.dataframe(df, use_container_width=True)
'''


if __name__ == "__main__":
    analyst = DataAnalyst()
    print(analyst.run_eda(
        data_dir=Path("data"),
        output_dir=Path("outputs"),
    ))
