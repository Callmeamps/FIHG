# Fractal Interhypergraph (FIHG) Runtime: Holistic Technical Implementation Spec

## 1. Goal

Build a synth runtime where one outward identity is backed by three interacting FIHGs:

- Identity / Coordination FIHG
- Memory FIHG
- Skills FIHG

Each FIHG is its own graph domain, but all of them can recurse into subgraphs. The top-level synth uses them as a single operating surface.

This design follows the common graph-system pattern of using a property-graph core with richer edge/node metadata, while allowing hyperedges for multi-party events and group relations [1][5]. It also follows the direction of current graph-for-agents work: graphs help with planning, execution, memory, and multi-agent coordination [2][6].

## 2. Recommended architecture

### 2.1 Core shapes

- **ArcadeDB graphs** — one per FIHG domain (Identity, Memory, Skills)
- **Gremlin queries** — for graph traversals and cross-graph bridge operations
- **Hyperedges modeled as vertices** — with participant links (no native hyperedge support)
- **SQLite peripheral store** — event log, threads, user interactions, metrics, STV outcomes
- **Python layer** — STV voting, business logic, coordination

This combines:
1. graph-native reasoning,
2. explicit event history (SQLite),
3. auditable decision-making (STV),
4. modular domain separation.

### 2.2 Top-level domains

```text
Synth Core
├── ArcadeDB: Identity Graph
├── ArcadeDB: Memory Graph
├── ArcadeDB: Skills Graph
└── SQLite: peripheral data
```

Each ArcadeDB graph owns its own vertex/edge types, schema, and lifecycle rules. Cross-graph traversal via Gremlin.

### 2.3 Shared primitives

All FIHGs should share a small set of primitive record types:

#### Node
- id
- type
- label
- state
- confidence
- freshness
- wear
- visibility
- version

#### Edge
- source
- target
- relation
- weight vector
- direction
- timestamps
- wear
- clarity
- activation count
- evidence set

#### Hyperedge
- id
- participants[]
- role map
- event type
- score vector
- time window
- provenance
- outcome
- runner_ups[]

A hyperedge is the cleanest way to represent events that belong to more than two things at once [1][5].

## 3. Implementation architecture

### Graph stores (ArcadeDB)
Three separate ArcadeDB instances/graphs, one per FIHG:

**Identity Graph**: persona, policy, style, rules, goals, delegation slots
**Memory Graph**: episodes, facts, concepts, preferences, sources, contradictions
**Skills Graph**: capabilities, subskills, benchmarks, evidence, dependencies

Each graph queried via Gremlin. ArcadeDB supports Neo4j Bolt protocol, accessible via gremlinpython.

### Peripheral store (SQLite)
Non-graph data stored in SQLite:

- `event_log`: timestamp, fihg, event_type, payload_json
- `threads`: id, user_id, created_at, status
- `user_interactions`: id, thread_id, user_input, synth_output, timestamp
- `session_state`: session_id, last_identity_state, last_memory_state, last_skills_state
- `metrics`: fihg, entity_id, activity_count, error_count, success_rate, last_updated
- `stv_outcomes`: task_id, winner, runner_ups_json, rejected, timestamp

### Hyperedges
Modeled as vertices with participant links (no native hyperedge support in ArcadeDB yet):
- Vertex type: `Hyperedge` with properties (event_type, time_window, provenance, outcome, score_vector)
- Participant links: regular edges from Hyperedge vertex to participant nodes
- Roles: stored as edge properties or JSON on Hyperedge vertex

## 4. STV as the conflict resolution policy

Use Single Transferable Vote whenever several candidate actions, memories, or skills compete for a limited slot.

### 4.1 STV criteria by FIHG

Each FIHG uses its own criteria when ranking candidates. This keeps domains focused on what matters to them:

**Identity FIHG votes on:**
- user preference alignment
- style consistency
- policy compliance
- brevity vs completeness
- task complexity fit

**Memory FIHG votes on:**
- relevance to query
- recency
- trust and source authority
- salience
- temporal precedence

**Skills FIHG votes on:**
- confidence
- cost
- latency
- recent success rate
- evidence strength

Then:
1. compute quota,
2. elect the top winner(s),
3. transfer surplus preference,
4. eliminate weakest,
5. continue until the slot is filled [4].

### 4.2 What to store from STV

Store more than just the winner.

Keep:
- winner
- runner-up 1
- runner-up 2
- eliminated candidates
- transferred support trail
- reasons for rejection

This gives you a reusable failure archive. On the next similar task, the system can revive strong runners-up instead of searching from scratch.

### 4.3 Example

Task: "answer a graph architecture question"

Candidates:
- C1: memory specialist
- C2: graph specialist
- C3: synthesis agent
- C4: style agent

The STV controller may elect C3 first, transfer surplus to C2, and store C1 as runner-up for future reuse.

## 5. Traffic, wear, and clarity

Treat nodes and edges as stateful objects.

### Metrics
- `activity_count`
- `last_used_at`
- `success_rate`
- `failure_rate`
- `latency`
- `clarity`
- `wear`
- `decay`
- `trust`

### Interpretation
- high activity + high success = bright / strong path
- high activity + high failure = worn / overloaded path
- low activity + old last_used_at = dim / stale path

This is useful for memory pruning, skill depreciation, and routing confidence.

## 6. Routing loop

1. User input arrives.
2. Identity FIHG frames the answer style and constraints.
3. Memory FIHG retrieves relevant episodes and facts.
4. Skills FIHG proposes candidate capabilities.
5. STV ranks candidate actions.
6. Winning route executes.
7. Runner-ups are stored.
8. Metrics update node/edge wear.

## 7. Practical API surface

### Core calls
- `create_node`
- `create_edge`
- `create_hyperedge`
- `record_event`
- `query_subgraph`
- `rank_candidates_stv`
- `promote_runner_up`
- `decay_states`
- `rebuild_projection`

### Example payload
```json
{
  "task": "Draft an architecture note",
  "candidates": [
    {"id": "synth_writer", "rank": 1, "confidence": 0.82},
    {"id": "graph_reasoner", "rank": 2, "confidence": 0.79},
    {"id": "memory_retriever", "rank": 3, "confidence": 0.74}
  ]
}
```

## 8. Common failure modes

### 8.1 Graph bloat
Problem: every detail becomes a node.

Fix:
- thresholding
- salience scoring
- TTL for low-value artifacts
- hierarchical summaries

### 8.2 Routing thrash
Problem: too many agents compete.

Fix:
- STV quota gate
- candidate caps
- role-based prefiltering

### 8.3 Memory contradiction
Problem: several memories disagree.

Fix:
- store both
- attach source trust
- use temporal precedence
- keep contradiction edges

### 8.4 Skill drift
Problem: stale skills keep winning.

Fix:
- decay unused skills
- require recent evidence
- keep failed attempts for retraining or later review

## 9. Suggested build sequence

### Phase 1
- property graph schema
- event log
- STV ranking
- runner-up archive

### Phase 2
- memory FIHG
- skill FIHG
- identity FIHG
- graph traversal retrieval

### Phase 3
- hyperedges for multi-party events
- recursive subgraphs
- decay and wear scoring
- replay and summarization

### Phase 4
- cross-FIHG learning
- automatic candidate promotion
- adaptive governance

## 10. Example end-to-end flow

User asks: "What about inter-graphs?"

1. Identity selects concise educational style.
2. Memory retrieves prior graph discussion.
3. Skills selects "graph explanation" and "systems mapping".
4. STV compares candidate response forms.
5. Winner becomes the user-facing answer.
6. Runner-up is stored because it still had strong support.
7. Memory records the event as a hyperedge:
   `{user, topic=inter-graphs, outcome=successful, style=concise}`

## 11. Design principle

Do not collapse everything into one giant graph. Let each FIHG own its own domain, then connect them with explicit bridge edges. That keeps the system recursive, debuggable, and extensible.

## 12. References

See `references.md`.
