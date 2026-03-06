# TASK-004: End-to-End Demo Project + CLI Polish + Minor Fixes

**Assigned to:** DEV
**Assigned by:** PM
**Priority:** Medium
**Branch:** `feat/end-to-end-demo`
**Repo:** https://github.com/rodolfolermacontreras/Meta-Agent
**Depends on:** TASK-003 ✅ merged

---

## Context

The system is functionally complete. This task makes it demo-ready: a working example project anyone can run, CLI improvements for usability, and the 3 carry-forward minor fixes from TASK-003.

---

## Deliverables

### 1. Demo project: `projects/retail-sales-demo/`

Create a fully working example project that showcases the meta-agent end-to-end:

```
projects/retail-sales-demo/
├── brief.md           ← forecast task, uses data/raw/sales.csv
└── data/
    └── raw/
        └── sales.csv  ← 3 years of monthly retail sales (synthetic, 36 rows)
```

`brief.md` content:
```markdown
# Project Brief: Retail Sales Demo

## Objective
Forecast monthly retail sales for the next 12 months.

## Task Type
- [x] Time-series Forecast

## Data Sources
- Source 1: projects/retail-sales-demo/data/raw/sales.csv

## Deliverables
- Forecast with 95% confidence intervals
- Interactive Plotly chart
- Model evaluation metrics

## Priority
High
```

Then run the full pipeline and commit the outputs:
```bash
python -m meta_agent run --project retail-sales-demo
```

Commit all files in `projects/retail-sales-demo/` including outputs.

### 2. Second demo: `projects/churn-prediction-demo/`

A classification ML demo:
```
projects/churn-prediction-demo/
├── brief.md           ← ML task, churn classification
└── data/
    └── raw/
        └── customers.csv  ← 500 rows, columns: tenure, monthly_charges, num_products, churned (0/1)
```

Run and commit outputs including `shap_summary.html` and `model_eval.csv`.

### 3. CLI polish

Upgrade `meta_agent/cli.py`:

- Add `--list` command: `python -m meta_agent list` — shows all projects in `projects/` with their status
- Add `--verbose` flag to `run`: prints each pipeline step as it executes
- Improve `status` output: show file sizes of outputs, not just filenames
- Add `--version` flag: prints `meta-agent v0.1.0`

### 4. Three minor fixes from TASK-003 review

- `run_monte_carlo`: add `# NOTE: for 3+ variables, first two are multiplied and remaining are added` comment, OR add a `"model"` config key (`"product"` vs `"sum"`)
- Dashboard template: consolidate the 3 `+=` blocks into a single `textwrap.dedent` with conditional section
- `_forecast_exp_smoothing`: move the TODO from inside the docstring to an inline `# TODO:` comment just before the relevant line

### 5. Tests

- `test_cli_list_command` — verify `--list` prints project names
- `test_cli_verbose_flag` — verify `--verbose` doesn't crash
- `test_cli_version` — verify `--version` prints version string
- `test_demo_project_runs` — run the retail-sales-demo project, verify outputs exist

---

## Definition of Done

- [ ] Both demo projects committed with outputs
- [ ] `python -m meta_agent run --project retail-sales-demo` works cleanly
- [ ] `python -m meta_agent list` works
- [ ] 3 minor fixes applied
- [ ] `pytest tests/ -v` all passing
- [ ] PR on `feat/end-to-end-demo`
- [ ] `teamates.md` updated

## Notes from PM

The demo projects are the most important part of this task — they're what we show to users. Make the sales data realistic-looking (seasonal pattern + trend + noise). The churn dataset should have meaningful feature correlations so the SHAP chart shows something interesting. — PM
