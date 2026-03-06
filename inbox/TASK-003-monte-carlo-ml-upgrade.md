# TASK-003: Monte Carlo Upgrade + SHAP for ML + Dashboard Date Slider

**Assigned to:** DEV
**Assigned by:** PM
**Priority:** High
**Branch:** `feat/monte-carlo-ml-upgrade`
**Repo:** https://github.com/rodolfolermacontreras/Meta-Agent
**Depends on:** TASK-002 ✅ merged

---

## Context

Three upgrades based on the review backlog and product roadmap:
1. Make Monte Carlo production-ready (currently runs but needs proper distribution fitting + tornado chart)
2. Add SHAP values to the ML pipeline for interpretability
3. Add a date range slider to the Streamlit dashboard
4. Address 4 minor notes from TASK-002 review

---

## Deliverables

### 1. `meta_agent/agents/data_analyst.py` — upgrade `run_monte_carlo`

Current stub runs a simulation but lacks distribution fitting and sensitivity output. Replace with:

```python
def run_monte_carlo(self, data_dir, output_dir, config=None):
    """Full Monte Carlo: fit distributions, simulate, output percentile table + tornado chart."""
```

Requirements:
- Read input variable definitions from `config["variables"]` if present, otherwise auto-detect numeric columns and fit distributions
- Fit distribution per variable: try Normal, then LogNormal (use `scipy.stats.fit` or `scipy.stats.norm.fit`)
- Run minimum 10,000 iterations (default 50,000)
- Output:
  - `outputs/simulation_results.csv` — all run outcomes (sampled)
  - `outputs/simulation_stats.csv` — mean, median, std, P5, P10, P25, P50, P75, P90, P95, P99
  - `outputs/distribution_chart.html` — Plotly histogram of outcome distribution with vertical percentile lines
  - `outputs/tornado_chart.html` — Plotly horizontal bar chart: sensitivity of each input variable (use Pearson correlation of input vs. output)

### 2. `meta_agent/agents/data_analyst.py` — add SHAP to `run_ml`

After model training, compute SHAP values and save a summary plot:

```python
# After model.fit(X_train, y_train):
try:
    import shap  # lazy import
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)
    # Save SHAP summary as HTML via plotly (not matplotlib)
except ImportError:
    pass  # SHAP optional — log skip in findings
```

Add to outputs: `outputs/shap_summary.html` (bar chart of mean |SHAP| per feature)

### 3. `meta_agent/agents/data_analyst.py` — dashboard date slider

In `_generate_streamlit_app`, when a `date_col` is detected, add a `st.date_input` range slider above the time series chart:

```python
# Generated code should include:
date_range = st.date_input("Date range", value=(df[date_col].min(), df[date_col].max()))
df = df[(df[date_col] >= pd.Timestamp(date_range[0])) & ...]
```

### 4. Address TASK-002 minor review notes

- Replace `import openpyxl  # noqa: F401` with just `pd.read_excel()` (pandas raises its own ImportError)
- Replace f-string escaping in `_generate_streamlit_app` with `textwrap.dedent` template string
- Add `# TODO: horizon not used in exp-smoothing fallback` comment to `_forecast_exp_smoothing`

### 5. Tests to add

- `test_monte_carlo_outputs` — verify `simulation_stats.csv`, `distribution_chart.html`, `tornado_chart.html` all produced
- `test_monte_carlo_percentiles` — verify P5 < P50 < P95 in stats CSV
- `test_ml_with_shap` — verify `shap_summary.html` produced (mock shap import if not installed)
- `test_dashboard_date_slider` — verify generated `app.py` contains `st.date_input`

### 6. Update `requirements.txt`

Add:
```
shap>=0.44
```

---

## Definition of Done

- [ ] `run_monte_carlo` produces distribution chart + tornado chart
- [ ] `run_ml` produces `shap_summary.html` (or logs skip gracefully)
- [ ] Generated Streamlit app includes date range slider when date col detected
- [ ] 4 TASK-002 review notes addressed
- [ ] `pytest tests/ -v` all passing
- [ ] PR on `feat/monte-carlo-ml-upgrade`
- [ ] `teamates.md` updated

## Notes from PM

Monte Carlo is a key differentiator for this system — make the tornado chart look good (horizontal bars, sorted by absolute correlation, color by positive/negative). The SHAP integration should be fully optional (graceful skip if not installed) — don't break the ML pipeline for users without it. — PM
