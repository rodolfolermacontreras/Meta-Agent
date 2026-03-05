# Multi-Agent Workspace

A shared workspace for collaborative multi-agent projects.
**GitHub Repo:** https://github.com/rodolfolermacontreras/Meta-Agent

---

## DS Meta-Agent System

A production meta-agent framework that accepts any data science task — forecasting, dashboards, Monte Carlo simulations, ML pipelines — and orchestrates three specialized sub-agents to complete it.

### Architecture

```
User / PM submits task
        │
        ▼
┌───────────────────┐
│    META-AGENT     │  ← Parses task, selects agents, builds infrastructure
│   (Orchestrator)  │
└───────┬───────────┘
        │
   ┌────┴──────────────────────────┐
   │             │                 │
   ▼             ▼                 ▼
┌──────────────┐  ┌──────────────────────┐  ┌─────────────┐
│ DATA ANALYST │  │ KNOWLEDGE CURATOR    │  │  LIBRARIAN  │
│              │  │                      │  │             │
│ • Forecasts  │  │ • Docs & insights    │  │ • Data cat. │
│ • ML models  │  │ • Methodology notes  │  │ • Sources   │
│ • Monte Carlo│  │ • Results summaries  │  │ • Versioning│
│ • Dashboards │  │ • Knowledge base     │  │ • References│
└──────────────┘  └──────────────────────┘  └─────────────┘
```

### Team

| Agent | Role |
|-------|------|
| PM (Claude Code #1) | Project Manager — task definition, PR review, architecture |
| DEV (Claude Code #2) | Software Dev & Data Scientist — implementation, modeling |

### DS System Folders

```
multi-agent/
├── teamates.md              ← PM ↔ DEV communication log (READ FIRST)
├── meta-agent/AGENT.md      ← Meta-agent orchestrator spec
├── meta-agent/agents/       ← Sub-agent definitions
├── meta-agent/workflows/    ← Reusable workflow templates
├── projects/                ← One subfolder per active DS project
├── inbox/                   ← PM → DEV task assignments
├── outbox/                  ← Completed deliverables
└── shared/                  ← Data sources registry, templates
```

---

## Story Pipeline (Existing Demo)

A demonstration of automated multi-agent workflows using **GitHub Copilot CLI**.

## Quick start

```bash
# 1. Open this folder in a Copilot CLI session
cd C:\Training\Microsoft\Copilot\multi-agent

# 2. (Optional) Edit your story request
# Edit story-pipeline/input.md

# 3. Run the pipeline
/generate-story

# 4. Read the result
# story-pipeline/final.md
```

## The pipeline

4 specialist agents run in sequence, each writing output that the next reads:

| Step | Agent | Reads | Writes |
|------|-------|-------|--------|
| 1 | `plot-designer` | `input.md` | `plot.md` |
| 2 | `character-creator` | `input.md` + `plot.md` | `characters.md` |
| 3 | `story-writer` | all above | `draft.md` |
| 4 | `story-editor` | `draft.md` | `final.md` |

## Customise the story

Edit `story-pipeline/input.md` before running. You can change:
- **Genre**: sci-fi, fantasy, thriller, romance, horror...
- **Theme**: the central idea or conflict
- **Tone**: dark, humorous, hopeful, tense...
- **Length**: short story, flash fiction, chapter...

## Key files

- `.claude/agents/story-orchestrator.md` — the conductor
- `.claude/skills/*/SKILL.md` — each agent's expertise
- `.claude/commands/generate-story.md` — the `/generate-story` command
- `CLAUDE.md` — architecture explanation and concept guide
