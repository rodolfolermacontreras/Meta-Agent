# Workflow: Interactive Dashboard

## Sub-agents: Librarian → Data Analyst → Knowledge Curator

---

## Phase 1 — Librarian
1. Catalog all data sources to be visualized
2. Validate: all required dimensions and metrics present
3. Register sources, produce manifest
4. Note refresh cadence (will dashboard need live data connection?)

## Phase 2 — Data Analyst
1. Load and clean data
2. Identify key metrics and dimensions from brief
3. Design layout: determine chart types for each metric
   - KPI scorecards for headline numbers
   - Time series for trends
   - Bar/column for comparisons
   - Scatter/bubble for relationships
   - Maps for geographic data
4. Build dashboard using Dash or Streamlit:
   - Add filters (date range, category, region, etc.)
   - Make all charts interactive (hover, zoom, filter)
   - Add a data table with export
5. Test: ensure all filters work, no broken charts
6. Produce outputs:
   - `outputs/dashboard/app.py` — runnable dashboard app
   - `outputs/dashboard/requirements.txt` — dependencies
   - `outputs/dashboard/README.md` — how to run locally
   - `outputs/dashboard_screenshot.png` — static preview
   - `notebooks/dashboard_data_prep.ipynb` — data prep notebook

## Phase 3 — Knowledge Curator
1. Document each chart: what it shows, how to interpret it
2. Write user guide for non-technical stakeholders
3. Note any data freshness limitations
4. Produce `outputs/summary.md` with user guide

## Acceptance Criteria
- [ ] Dashboard runs locally with `python app.py` or `streamlit run app.py`
- [ ] All specified KPIs visible
- [ ] At least one filter works
- [ ] Screenshot committed for preview
- [ ] User guide written
