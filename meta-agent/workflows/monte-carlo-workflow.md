# Workflow: Monte Carlo Simulation

## Sub-agents: Librarian → Data Analyst → Knowledge Curator

---

## Phase 1 — Librarian
1. Catalog input data / parameter distributions from brief
2. If historical data provided: extract distribution parameters
3. Register sources, produce manifest

## Phase 2 — Data Analyst
1. Define input variables and their distributions (read from brief):
   - Normal, lognormal, uniform, triangular, PERT, etc.
2. Fit distributions to historical data if provided (use scipy.stats)
3. Define the model function: how inputs combine to produce outcome
4. Run simulation (minimum 10,000 iterations, default 100,000)
5. Compute output statistics:
   - Mean, median, std
   - Percentiles: P5, P10, P25, P50, P75, P90, P95, P99
   - Probability of exceeding key thresholds (from brief)
6. Sensitivity analysis: tornado chart of input contributions
7. Produce outputs:
   - `outputs/simulation_results.csv` — all simulation runs
   - `outputs/distribution_chart.html` — output distribution histogram with percentiles
   - `outputs/tornado_chart.html` — sensitivity / tornado chart
   - `outputs/simulation_stats.csv` — summary statistics
   - `notebooks/monte_carlo.ipynb`

## Phase 3 — Knowledge Curator
1. Summarize: "Under current assumptions, [outcome] has [X]% probability of exceeding [threshold]"
2. Document all input assumptions and their source
3. Highlight most sensitive inputs from tornado chart
4. Note what would change the outcome most
5. Produce `outputs/summary.md`

## Acceptance Criteria
- [ ] Minimum 10,000 simulation runs
- [ ] Full percentile table produced
- [ ] Sensitivity analysis included
- [ ] All input assumptions documented
- [ ] Interactive distribution chart saved
