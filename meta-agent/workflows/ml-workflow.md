# Workflow: Machine Learning Model

## Sub-agents: Librarian → Data Analyst → Knowledge Curator

---

## Phase 1 — Librarian
1. Catalog all data sources (features + target)
2. Validate: target column present, no all-null columns
3. Register sources, produce manifest

## Phase 2 — Data Analyst
1. Load and merge datasets if multiple sources
2. EDA: distributions, correlations, class balance (classification)
3. Feature engineering: handle nulls, encode categoricals, scale numerics
4. Split: 70/15/15 train/val/test (or as specified in brief)
5. Train baseline model (logistic regression / linear regression)
6. Train candidate models (random forest, XGBoost, LightGBM minimum)
7. Tune best model with cross-validation
8. Evaluate on test set:
   - Classification: accuracy, precision, recall, F1, AUC-ROC
   - Regression: MAE, RMSE, R²
9. SHAP values or feature importance for interpretability
10. Produce outputs:
    - `outputs/model_v1_[DATE].pkl` — serialized model
    - `outputs/model_eval.csv` — metrics comparison
    - `outputs/feature_importance.html` — SHAP/importance chart
    - `outputs/predictions.csv` — test set predictions
    - `notebooks/ml_analysis.ipynb`

## Phase 3 — Knowledge Curator
1. Summarize: "Model achieves [metric] on test set, baseline was [metric]"
2. Document feature importance findings
3. Note deployment considerations (data drift, retraining cadence)
4. Produce `outputs/summary.md`

## Acceptance Criteria
- [ ] Model beats baseline
- [ ] Metrics reported on held-out test set
- [ ] Model artifact saved with version
- [ ] Feature importance documented
- [ ] Reproducible notebook committed
