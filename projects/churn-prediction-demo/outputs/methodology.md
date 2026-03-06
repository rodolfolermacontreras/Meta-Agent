# Methodology: churn-prediction-demo

**Date:** 2026-03-06
**Task type:** ml

## Approach

Supervised learning pipeline: data cleaning, feature engineering, train/test split (80/20), Random Forest classifier with 100 estimators. Metrics: accuracy, weighted F1. Feature importance via Gini.

## Reproducibility

To reproduce this analysis:
1. Ensure Python 3.10+ and dependencies from `requirements.txt`
2. Place data in `projects/churn-prediction-demo/data/raw/`
3. Run: `python -m meta_agent run --project churn-prediction-demo`
