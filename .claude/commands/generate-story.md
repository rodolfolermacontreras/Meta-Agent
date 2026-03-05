---
description: Run the full multi-agent story generation pipeline. Invoke the story-orchestrator to coordinate plot design, character creation, writing, and editing agents in sequence.
---

Run the story generation pipeline using the `story-orchestrator` agent.

The pipeline reads from `story-pipeline/input.md` and produces a finished story in `story-pipeline/final.md` by coordinating 4 specialist agents:

1. **plot-designer** → writes `story-pipeline/plot.md`
2. **character-creator** → writes `story-pipeline/characters.md`  
3. **story-writer** → writes `story-pipeline/draft.md`
4. **story-editor** → writes `story-pipeline/final.md`

Start the pipeline now. Use the `story-orchestrator` agent to orchestrate all steps.
