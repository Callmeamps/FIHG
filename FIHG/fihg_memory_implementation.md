# Memory FIHG: Technical Implementation Spec

## 1. Purpose

The Memory FIHG stores experiences, facts, preferences, contradictions, and temporal context in graph form. It is not a flat note pile. It is a relational memory ecosystem.

Graph-based memory is a well-supported direction for agents because it naturally represents relationships, hierarchy, retrieval paths, and memory evolution [2]. It also aligns with graph-enhanced agent systems that use structured information for planning, execution, memory, and coordination [6].

## 2. Memory layers

### 2.1 Episodic memory
Specific events.

Example:
```text
{user, asked, "What is a hypergraph?", date, tone=curious}
```

### 2.2 Semantic memory
Stable facts and concepts.

Example:
```text
{knowledge_graph, is_a, graph_structure}
```

### 2.3 Preference memory
User or system preferences.

Example:
```text
{user, prefers, concise_answers}
```

### 2.4 Skill-adjacent memory
What worked, what failed, what was learned.

Example:
```text
{STV_routing, improved, conflict_resolution_quality}
```

### 2.5 Temporal memory
Sequence and freshness.

Example:
```text
{memory_A, before, memory_B}
```

### 2.6 Source trust memory
Where a memory came from.

Example:
```text
{fact_X, sourced_from, official_docs, trust=0.93}
```

## 3. Data model

Inherits shared primitives from `fihg_holistic.md`. Memory adds domain-specific types:

### Node types
- episode
- fact
- preference
- contradiction
- summary
- source
- concept
- timeline_marker

### Edge types
- related_to
- caused_by
- reinforces
- contradicts
- derived_from
- summarized_by
- retrieved_with
- decays_to
- depends_on

### Hyperedge types
- conversation episode
- multi-turn session
- project thread
- decision bundle
- failure bundle

Example hyperedge:
```text
{user, topic=FIHG, tone=curious, success=true, date=2026-05-06}
```

## 4. Common implementation methods

### Method A: graph-first memory
Store memory as a property graph and traverse by relation.

Good for:
- concept association
- related-memory retrieval
- contradiction checks

### Method B: retrieval + summary hybrid
Keep:
- raw event log
- rolling summaries
- graph links between summaries and events

Good for:
- long conversations
- session continuity
- compact context windows

### Method C: graph + embeddings hybrid
Use embeddings to find candidate memories, then graph traversal to verify and expand.

Good for:
- fuzzy recall
- semantic search
- partial prompts

This is one of the most common practical methods for agent memory systems because graph retrieval alone can miss approximate matches, while embeddings alone can miss structure [2][3].

## 5. Retrieval pipeline

1. receive query
2. embed query
3. find candidate memories
4. traverse related nodes
5. score by:
   - relevance
   - recency
   - trust
   - salience
6. rank with STV if several retrieval bundles compete
7. return winner plus optional runner-ups

## 6. STV in memory selection

When multiple memory bundles match, do not collapse them too early.

Use STV to choose the best bundle for:
- immediate recall
- context injection
- summary expansion

STV criteria for Memory:
- relevance to query
- recency
- trust and source authority
- salience
- temporal precedence

Store the runner-ups because they are often useful when the first choice later proves incomplete.

Example:
- Bundle A: exact topic match
- Bundle B: same user preference history
- Bundle C: same structural pattern

STV can pick Bundle A, while Bundles B and C remain archived for future retrieval.

## 7. Wear, brightness, and decay

A memory should not stay equally strong forever.

### Metrics
- `salience`
- `freshness`
- `usage_count`
- `reinforcement`
- `decay_rate`
- `clarity`
- `wear`

### Simple rule
- frequent success = stronger
- repeated contradiction = lower trust
- unused memory = decay
- high-value memory = protected

This makes memory alive instead of static.

## 8. Consolidation path

### Step 1: event capture
Store the raw conversation or action.

### Step 2: episode extraction
Turn it into structured memory nodes.

### Step 3: abstraction
Make a summary node.

### Step 4: linking
Link summary to facts, preferences, and prior episodes.

### Step 5: decay and reinforcement
Update strength based on later use.

## 9. Example memory graph

```text
episode_17 -> summarized_by -> summary_4
summary_4 -> reinforces -> preference_concise
summary_4 -> related_to -> hypergraph_topic
episode_17 -> caused_by -> user_question
```

## 10. Contradiction handling

Do not overwrite immediately.

Store:
- the new claim
- the old claim
- source trust
- date
- conflict edge

Example:
```text
fact_A contradicts fact_B
```

Then let future retrieval use recency, trust, and provenance.

## 11. Failure modes

### 11.1 Memory flood
Too many tiny memories.

Fix:
- salience threshold
- batching
- summarization
- TTL for low-value items

### 11.2 False recall
Wrong memory gets picked.

Fix:
- trust weighting
- source provenance
- STV ranking
- graph verification

### 11.3 Stale memory dominance
Old memories keep winning.

Fix:
- decay
- freshness boost
- periodic consolidation

## 12. Practical storage layout

Inherits base schema from shared primitives (`fihg_holistic.md`). Memory tables extend base Node/Edge/Hyperedge:

### Tables
- `memory_nodes`
- `memory_edges`
- `memory_hyperedges`
- `memory_events`
- `memory_summaries`
- `memory_embeddings`
- `memory_conflicts`

### Example event payload
```json
{
  "event_type": "conversation_turn",
  "participants": ["user", "synth"],
  "topic": "FIHG",
  "mood": "curious",
  "outcome": "positive",
  "salience": 0.87
}
```

## 13. Build order

1. event capture
2. episode extraction
3. relation graph
4. summary nodes
5. retrieval
6. decay
7. STV selection
8. runner-up archive

## 14. References

See `references.md`.
