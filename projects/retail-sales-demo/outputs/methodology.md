# Methodology: retail-sales-demo

**Date:** 2026-03-06
**Task type:** forecast

## Approach

Time-series forecasting using exponential smoothing as a baseline. Data split 80/20 for train/test. Metrics: MAE, RMSE.

## Reproducibility

To reproduce this analysis:
1. Ensure Python 3.10+ and dependencies from `requirements.txt`
2. Place data in `projects/retail-sales-demo/data/raw/`
3. Run: `python -m meta_agent run --project retail-sales-demo`
