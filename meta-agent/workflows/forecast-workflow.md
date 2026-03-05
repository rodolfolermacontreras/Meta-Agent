# Workflow: Time-Series Forecasting

## Sub-agents: Librarian → Data Analyst → Knowledge Curator

---

## Phase 1 — Librarian
1. Catalog time-series data source
2. Validate: date column, target column, no gaps > 10% of series
3. Register in shared registry
4. Copy to `data/raw/`, produce manifest

## Phase 2 — Data Analyst
1. Load data, parse dates, sort ascending
2. EDA: plot series, check stationarity (ADF test), identify seasonality
3. Split: last 20% as test set (or use explicit holdout dates from brief)
4. Fit models (try at minimum 2):
   - Prophet (handles seasonality, holidays well)
   - ARIMA/SARIMA (for stationary series)
   - Exponential Smoothing (simple baseline)
5. Evaluate on test set: MAE, RMSE, MAPE
6. Select best model, refit on full data
7. Generate forecast for requested horizon
8. Produce outputs:
   - `outputs/forecast.csv` — date, forecast, lower_95, upper_95
   - `outputs/forecast_chart.html` — interactive Plotly chart (actuals + forecast + CI)
   - `outputs/model_eval.csv` — model comparison metrics
   - `notebooks/forecast_analysis.ipynb` — full reproducible notebook

## Phase 3 — Knowledge Curator
1. Read findings.md and all outputs
2. Write executive summary: "We forecast [metric] will reach [value] by [date] ± [CI]"
3. Document model selection rationale
4. Note key assumptions (no structural breaks, seasonality patterns hold, etc.)
5. Produce `outputs/summary.md`

## Acceptance Criteria
- [ ] Forecast covers requested horizon
- [ ] Confidence intervals included
- [ ] Model evaluation metrics reported
- [ ] Interactive chart saved
- [ ] Methodology documented
