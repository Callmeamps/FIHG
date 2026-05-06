# Skills FIHG: Technical Implementation Spec

## 1. Purpose

The Skills FIHG stores capabilities, dependencies, confidence, rustiness, and transfer paths. It is the synth's capability map.

Current graph-for-agent work points toward graphs as a way to organize planning, execution, memory, and coordination [6]. Skills fit that pattern directly because capability is relational: one skill depends on another, transfers into another, and competes with other ways of solving the same task.

## 2. Skill taxonomy

### Core skill node types
- language
- reasoning
- coding
- debugging
- search
- summarization
- planning
- synthesis
- tool use
- domain knowledge
- style control

### Example
```text
coding
├── python
├── javascript
├── sql
├── bash
└── testing
```

## 3. Skill edges

- depends_on
- transfers_to
- strengthens
- weakens
- blocks
- unlocks
- substitutes_for
- overlaps_with
- requires
- evidence_from

Example:
```text
debugging -> depends_on -> code_reading
sql -> transfers_to -> data_analysis
testing -> strengthens -> debugging
```

## 4. Skills are not flat labels

Each skill should have:
- confidence
- evidence count
- last practiced time
- success rate
- failure rate
- latency
- domain scope
- decay factor

That is what makes the skill graph useful in practice rather than decorative.

## 5. Common implementation methods

### Method A: capability graph
A graph of skills and dependencies.

Good for:
- route selection
- prerequisite modeling
- skill transfer

### Method B: capability graph + benchmark memory
Each skill is linked to past tasks and evaluation outcomes.

Good for:
- confidence estimation
- skill promotion
- skill retirement

### Method C: skill graph + expert agents
Each node points to a specialist sub-agent or tool.

Good for:
- modular synths
- composable execution
- task-specific routing

## 6. Skill retrieval and routing

1. user task arrives
2. identify required skills
3. traverse dependency graph
4. score candidate skill paths
5. use STV when multiple routes compete
6. execute winning route
7. store runner-ups

## 7. STV in skill choice

Example task: “fix query performance”

Candidate routes:
- database tuning
- caching
- indexing
- query rewrite
- application-level batching

STV criteria for Skills:
- confidence
- cost
- latency
- recent success rate
- evidence strength

Runner-ups are valuable because they are often the second-best answer when conditions change.

## 8. Skill decay and recovery

### Decay
If a skill is not used:
- confidence drops slowly
- review frequency increases
- activation threshold rises

### Recovery
If a skill succeeds again:
- confidence rises
- latency falls
- reuse likelihood increases

This prevents stale expertise from dominating.

## 9. Skill examples

### Example 1: coding skill
```text
coding
 -> depends_on -> reading_errors
 -> transfers_to -> debugging
 -> unlocks -> automation
```

### Example 2: communication skill
```text
brief_explanation
 -> transfers_to -> summary_writing
 -> overlaps_with -> executive_reporting
```

### Example 3: systems skill
```text
graph_reasoning
 -> depends_on -> relation_tracking
 -> unlocks -> architecture_design
```

## 10. Failure modes

### 10.1 Skill inflation
Every node claims to be a skill.

Fix:
- require evidence
- require benchmarks
- require usage history

### 10.2 Skill fragmentation
Too many tiny subskills.

Fix:
- periodic consolidation
- parent-child skill mapping
- pruning of unused leaves

### 10.3 Skill masking
The system chooses a flashy skill instead of the right one.

Fix:
- STV gating
- confidence penalties
- evidence checks

## 11. Practical tables

Inherits base schema from shared primitives (`fihg_holistic.md`). Skills tables extend base Node/Edge:

### `skill_nodes` (extends base Node)
- id
- label
- category
- confidence
- evidence_count
- last_practiced_at
- decay

### `skill_edges`
- source_id
- target_id
- relation
- strength
- evidence

### `skill_benchmarks`
- task_id
- skill_id
- score
- notes
- date

### `skill_routes`
- task_id
- route_id
- winner
- runner_ups

## 12. Example runtime

Task: “create a markdown spec for the memory FIHG”

Skill graph chooses:
- markdown_writing
- technical_structuring
- graph_reasoning
- example_generation

STV selects the strongest route:
1. technical_structuring
2. graph_reasoning
3. markdown_writing

Runner-up route:
1. markdown_writing
2. example_generation

## 13. Build order

1. define skill taxonomy
2. connect prerequisites
3. attach benchmark history
4. add decay
5. add STV routing
6. store runner-ups
7. link to memory episodes

## 14. References

See `references.md`.
