# TASK-002: Real Data Connectors + Prophet Forecast + Plotly Dashboard

**Assigned to:** DEV (Software Developer & Data Scientist)
**Assigned by:** PM
**Priority:** High
**Branch:** `feat/real-data-connectors`
**Repo:** https://github.com/rodolfolermacontreras/Meta-Agent
**Depends on:** TASK-001 ✅ merged

---

## Context

TASK-001 gave us a solid skeleton with synthetic data fallback. Now we upgrade to real implementations:
1. Real file connectors (CSV, Excel, Parquet, JSON) in the Librarian
2. Prophet-based time-series forecasting in the Data Analyst (replacing the exp-smoothing stub)
3. A real Plotly HTML chart output for forecasts
4. A basic Streamlit dashboard for EDA/dashboard task type

---

## Deliverables

### 1. `meta_agent/agents/librarian.py` — upgrade `catalog_sources`

Replace the stub with real file loading:

```python
def catalog_sources(self, sources: list[str], project_name: str) -> list[dict]:
    """Load, profile, and validate each data source.

    Supports: CSV, Excel (.xlsx/.xls), Parquet, JSON (records orient).
    For URLs: download to data/raw/ first.
    """
```

Requirements:
- Detect format from file extension automatically
- Profile: shape, dtypes, null counts per column, duplicate row count, date range (if datetime col found)
- Return list of profile dicts (one per source)
- Log each source in `shared/data-sources/registry.md`

### 2. `meta_agent/agents/data_analyst.py` — upgrade `run_forecast`

Replace exp-smoothing with Prophet:

```python
def run_forecast(self, data_dir, output_dir, config=None):
    """Prophet-based forecast. Falls back to exp-smoothing if prophet not installed."""
```

Requirements:
- Auto-detect the date column and target column (or read from `config`)
- Fit Prophet with default seasonality detection
- Forecast horizon from `config.get("horizon", 12)` (in periods)
- Produce:
  - `outputs/forecast.csv` — ds, yhat, yhat_lower, yhat_upper
  - `outputs/forecast_chart.html` — Plotly interactive chart (actuals + forecast + CI band)
  - `outputs/model_eval.csv` — MAE, RMSE, MAPE on holdout

### 3. `meta_agent/agents/data_analyst.py` — implement `run_dashboard`

Stop routing dashboard to `run_eda`. Implement a real Streamlit app generator:

```python
def run_dashboard(self, data_dir, output_dir, config=None):
    """Generate a ready-to-run Streamlit dashboard for the project data."""
```

Requirements:
- Reads processed data from `data_dir`
- Generates `outputs/dashboard/app.py` — a parameterized Streamlit app with:
  - KPI row (count, mean, max of numeric cols)
  - Time series chart if a date column is found
  - Distribution chart for top numeric column
  - Filterable data table
- `outputs/dashboard/requirements.txt`
- `outputs/dashboard/README.md` with `streamlit run app.py` instructions

### 4. Update `tests/test_meta_agent.py`

Add tests for:
- `test_librarian_loads_csv` — load a real CSV fixture, verify profile shape
- `test_librarian_loads_excel` — same for Excel (use `openpyxl`)
- `test_forecast_with_real_data` — fixture with 50 rows of date+value, verify forecast.csv and chart.html produced
- `test_dashboard_generates_app` — verify `outputs/dashboard/app.py` created

Add a `tests/fixtures/` folder with:
- `sample_sales.csv` — 36 rows, columns: `date` (monthly), `value` (random sales)
- `sample_classification.xlsx` — 100 rows classification dataset

### 5. Update `requirements.txt`

Add:
```
prophet>=1.1
plotly>=5.0
streamlit>=1.30
openpyxl>=3.1
pyarrow>=14.0
```

---

## Definition of Done

- [ ] `Librarian.catalog_sources` loads CSV, Excel, Parquet, JSON without errors
- [ ] `DataAnalyst.run_forecast` uses Prophet and produces `forecast_chart.html`
- [ ] `DataAnalyst.run_dashboard` produces a runnable `outputs/dashboard/app.py`
- [ ] `pytest tests/ -v` all passing (including new tests)
- [ ] Test fixtures committed in `tests/fixtures/`
- [ ] PR opened on `feat/real-data-connectors`
- [ ] `teamates.md` updated when PR ready

---

## Notes from PM

The minor notes from TASK-001 review: please also address these in this PR:
- Add lazy-import comment in `run_ml`
- Add `# TODO: implement full dashboard render` comment removed now that you're implementing it
- Range-pin deps in `requirements.txt`

Take it one feature at a time — Librarian first (it unblocks everything else), then forecast, then dashboard.
Open draft PR after Librarian is done so I can review incrementally. — PM
