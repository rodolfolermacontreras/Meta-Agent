# TASK-001: Implement Meta-Agent Core and Sub-Agents

**Assigned to:** DEV (Software Developer & Data Scientist)
**Assigned by:** PM
**Priority:** High
**Branch:** `feat/meta-agent-core`
**Repo:** https://github.com/rodolfolermacontreras/Meta-Agent

---

## Objective

Implement the runnable Python infrastructure for the meta-agent system. The architecture specs are already written in `meta-agent/` — your job is to build the actual code that makes them executable.

## Deliverables

### 1. `meta_agent/orchestrator.py`
The main orchestrator class. Must:
- Accept a project brief (path to `brief.md`)
- Parse task type, data sources, deliverables
- Select the correct workflow
- Launch sub-agents in the right order
- Assemble results and update `log.md`

```python
class MetaAgent:
    def run(self, project_name: str, brief_path: str) -> dict:
        """Run the full meta-agent pipeline for a project."""
        ...
```

### 2. `meta_agent/agents/data_analyst.py`
Implements the Data Analyst sub-agent. Must support:
- `run_forecast(data_path, output_path, config)` — Prophet/ARIMA
- `run_ml(data_path, output_path, config)` — sklearn/XGBoost pipeline
- `run_monte_carlo(params, output_path, config)` — scipy-based simulation
- `run_eda(data_path, output_path)` — ydata-profiling or pandas-profiling

### 3. `meta_agent/agents/librarian.py`
Implements the Librarian sub-agent. Must:
- `catalog_sources(sources: list[str])` — load and profile each source
- `validate_data(df)` — check quality, return issues list
- `produce_manifest(project_name)` — write `data/manifest.md`
- `register_source(source_info)` — append to `shared/data-sources/registry.md`

### 4. `meta_agent/agents/knowledge_curator.py`
Implements the Knowledge Curator. Must:
- `create_summary(findings_path, outputs_path)` — produce `summary.md`
- `document_methodology(project_name, approach)` — write methodology section
- `check_reusable_patterns(findings)` — flag if pattern worth adding to templates

### 5. `meta_agent/cli.py`
A CLI entry point:
```bash
python -m meta_agent run --project sales-forecast
python -m meta_agent run --project churn-model --task ml
python -m meta_agent status --project sales-forecast
```

### 6. `requirements.txt`
```
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3
prophet>=1.1
xgboost>=2.0
lightgbm>=4.0
plotly>=5.0
dash>=2.0
streamlit>=1.30
scipy>=1.11
ydata-profiling>=4.0
shap>=0.44
joblib>=1.3
python-dotenv>=1.0
```

### 7. `tests/test_meta_agent.py`
Basic unit tests:
- Test brief parsing
- Test workflow selection
- Test data validation (mock data)
- Test manifest generation

## Definition of Done

- [ ] All 5 Python files created and importable
- [ ] `python -m meta_agent run --project test-project` runs end to end (even with dummy data)
- [ ] Tests pass: `pytest tests/`
- [ ] `requirements.txt` committed
- [ ] PR opened for PM review
- [ ] `teamates.md` updated when PR is ready

## Resources

- Architecture specs: `meta-agent/AGENT.md`
- Sub-agent specs: `meta-agent/agents/`
- Workflow templates: `meta-agent/workflows/`
- Communication: `teamates.md`

## Notes from PM

Start with the `orchestrator.py` skeleton and the CLI so we can test the flow early. Don't aim for perfection on first pass — get the pipeline running end-to-end with stubs, then fill in the real implementations. Open a draft PR when you have the skeleton, I'll review incrementally.

Good luck! — PM
