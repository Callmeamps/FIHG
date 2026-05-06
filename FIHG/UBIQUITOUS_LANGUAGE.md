# Ubiquitous Language

## Synth Architecture

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Synth** | A collection of scripts, patterns, and models that coordinate to act as a singular being | AI agent, bot, assistant |
| **FIHG** | Fractal Interhypergraph Grid — the architecture for building synths, composed of three first-class interhypergraph domains | System, platform, framework |
| **Identity FIHG** | The domain that controls the synth's outward persona, priorities, policies, style, and arbitration | Identity, persona layer |
| **Memory FIHG** | The domain that manages episodes, facts, meaning, trust, decay, retrieval pathways, and temporal context | Memory, storage layer |
| **Skills FIHG** | The domain that models what the synth can do, how skills depend on each other, capability changes over time, and skill transfer | Skills, capabilities layer |

## Graph Structures

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Hypergraph** | A graph where a single edge can connect more than two nodes at once. Useful for events, groups, and shared states | Graph, network |
| **Hyperedge** | A multi-node relationship inside a hypergraph. Modeled as a vertex with participant links | Edge, relationship, event |
| **Node** | A thing, concept, agent, or state object inside the graph. Expresses properties visually (size, shape, texture, orientation) | Vertex, entity, object |
| **Edge** | A relationship between nodes. Can carry metadata, direction, weight, or multiple weights | Link, connection, arc |
| **Bridge** | A connection between FIHGs, such as Memory feeding Identity or Skills informing task selection. Implemented via Gremlin cross-graph traversals | Interface, integration |
| **Fractal** | A structure that repeats at multiple scales — subgraphs can contain subgraphs of the same kind | Recursion, nested |

## Graph State

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Brightness** | A live state signal for how active, fresh, visible, or healthy a node or edge is in the **graph** | Clarity (for models), activity |
| **Clarity** | A live state signal for how active, fresh, visible, or healthy a node or edge is in a **model** | Brightness (for graphs) |
| **Wear** | Accumulated load, strain, or degradation from repeated activity on a node or edge | Degradation, fatigue |
| **Decay** | The weakening of a memory or skill over time due to lack of use | Fade, erosion |
| **Traffic** | Activity flowing through nodes or edges. High traffic usually means high use | Activity, load |

### Graph State (extended)

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Visibility** | Whether a node or edge is visible to the synth's processing | Hidden, shown |
| **Activation** | Current activity level of a node — how "awake" or "engaged" it is | Activity, energy |
| **Importance** | Relative priority of a node or edge in the graph | Priority, weight |
| **Freshness** | How recent a memory, skill, or fact is — recency signal | Recency, newness |
| **Salience** | Importance or prominence of a memory relative to the current context | Relevance, prominence |
| **Activity count** | Number of times a node or edge has been used or traversed | Use count, hit count |
| **Recency** | Temporal proximity — how recently something occurred | Age, freshness |

## STV Voting

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **STV** | Single Transferable Vote — a conflict resolution mechanism where candidates are ranked, votes transfer based on preference strength, and the lowest-ranked candidate is eliminated until one has majority | Voting, election, ranking |
| **Runner-up** | An alternative candidate that was not elected but stored for quick reference when the winner fails or a fork is needed | Alternative, backup, secondary |
| **Quota** | The threshold number of votes required to elect a candidate in STV | Threshold, minimum |
| **Transfer** | Moving votes from an eliminated or fulfilled candidate to the next preference | Shift, move |
| **Eliminate** | Removing the lowest-ranked candidate from STV contention | Remove, drop |
| **Majority** | Winning threshold — more than 50% of votes | Win threshold, quota winner |
| **Candidate** | An option competing in STV election — a potential action, memory, skill route, or response shape | Option, choice, alternative |

## STV Criteria by FIHG

| FIHG | Votes on |
|------|----------|
| **Identity** | user preference alignment, style consistency, policy compliance, brevity vs completeness, task complexity fit |
| **Memory** | relevance to query, recency, trust and source authority, salience, temporal precedence |
| **Skills** | confidence, cost, latency, recent success rate, evidence strength |

## Hyperedge Components

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Provenance** | Source or origin of a hyperedge — where the data came from | Source, origin |
| **Score vector** | Metadata describing how the hyperedge was scored or ranked | Score, ranking |
| **Time window** | Temporal bounds of a hyperedge — when it started and ended | Duration, span |
| **Outcome** | Result or conclusion of the hyperedge event | Result, conclusion |
| **Role map** | Mapping of participant IDs to their roles within the hyperedge | Roles, participants |

## Metrics

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Latency** | Response time or delay — how long an operation takes | Delay, speed |
| **Success rate** | Proportion of operations that succeeded | Hit rate, pass rate |
| **Failure rate** | Proportion of operations that failed | Error rate, fail rate |
| **Evidence** | Supporting data or proof for a skill's confidence or a memory's reliability | Proof, data |

## Implementation Components

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Policy vote** | A recorded vote in Identity FIHG — candidate, rank, voter type, weight, rationale | Vote, ballot |
| **Policy outcome** | Result of STV in Identity FIHG — winner, runner-ups, rejected candidates, explanation | Decision, result |
| **Weight** | Numerical or symbolic measure attached to a relationship (trust, latency, frequency, cost) | Score, value |
| **Metadata** | Extra information attached to a node, edge, or hyperedge | Data, attributes |
| **Thread** | A conversation context in SQLite — tracks user interactions and maintains session continuity | Conversation, chat, session |
| **Session** | Runtime state of the synth — includes thread context, last identity/memory/skills state | Context, state |

## Tech Stack
| **Gremlin** | Apache TinkerPop graph traversal language used to query ArcadeDB and implement cross-graph bridges | Cypher, SQL |
| **gremlinpython** | The official Python client library for Gremlin | neo4j driver |
| **SQLite** | Peripheral storage for non-graph data: event logs, threads, user interactions, session state, metrics, STV outcomes | PostgreSQL, JSONB |
| **Intergraph** | A graph that connects to other graphs — used for bridging domains, layers, or subsystems | Bridge, connector |

## Relationships

- A **Synth** is backed by three **FIHGs**: Identity, Memory, and Skills
- Each **FIHG** is a separate **ArcadeDB** graph
- **Bridges** connect FIHGs via **Gremlin** cross-graph traversals
- **Nodes** participate in **Hyperedges** via participant links
- **STV** resolves conflicts by ranking candidates and storing **Runner-ups**
- **Brightness** applies to graphs; **Clarity** applies to models — these are intentionally distinct

## Example Dialogue

> **Dev:** "When the user asks about graph architecture, how does the synth decide which response to give?"
> 
> **Domain expert:** "The **Skills FIHG** proposes candidate capabilities. The **Memory FIHG** retrieves relevant episodes. The **Identity FIHG** shapes the style. Then **STV** ranks the candidates."
> 
> **Dev:** "And if the winning candidate fails?"
> 
> **Domain expert:** "The **Runner-up** is already stored in SQLite. We promote it instead of re-running the full **STV** election. Faster recovery."
> 
> **Dev:** "What happens to memory that hasn't been used in a while?"
> 
> **Domain expert:** "It **decays**. The **Memory FIHG** tracks **freshness** — unused memories lose strength. High-value memories are protected from **decay**."
> 
> **Dev:** "How do the three FIHGs talk to each other?"
> 
> **Domain expert:** "Through **Bridges**. **Gremlin** traversals span the three **ArcadeDB** graphs — Identity to Memory, Identity to Skills, Memory to Skills. They're separate graphs but connected."

## Flagged Ambiguities

- **"account"** was not used, but ensure "user" means authentication identity and "persona" means outward identity — these are distinct
- **"confidence" vs "trust"**: Confidence is a skill's self-assessment of performance. Trust is Memory's assessment of a source's reliability. These are different concepts applied in different contexts
- **"decay" vs "decay_rate"**: Use "decay" as the general concept and "decay_rate" as the numerical parameter controlling decay speed
- **"hyperedge" vs "hypergraph"**: A hypergraph contains hyperedges. A hyperedge is a multi-node relationship. Don't use these interchangeably

## Build Order

| Phase | Tasks | Description |
|-------|-------|-------------|
| **Phase 1** | A, B, C, D, E, F | Foundation: ArcadeDB setup, SQLite schema, Python scaffolding, three FIHG schemas |
| **Phase 2** | G, H, I, L, M | Core: cross-graph traversals, STV implementation, metrics, session state |
| **Phase 3** | J, K | Polish: decay/wear tracking, hyperedge modeling |

### Build Task Reference

| Task | Description | Dependencies |
|------|-------------|--------------|
| A | ArcadeDB setup (3 graphs) | None |
| B | SQLite schema (event_log, threads, metrics) | None |
| C | Python scaffolding (gremlinpython, mock clients) | None |
| D | Identity FIHG schema (ArcadeDB) | A |
| E | Memory FIHG schema (ArcadeDB) | A |
| F | Skills FIHG schema (ArcadeDB) | A |
| G | Cross-graph Gremlin traversals (bridges) | D, E, F |
| H | STV implementation with runner-up storage | D, E, F |
| I | Metrics aggregation (activity, error rate) | B |
| J | Decay and wear tracking | G, H, I |
| K | Hyperedge modeling (vertex + links) | G, H, I |
| L | Session state persistence | B |
| M | Event log querying and aggregation | B |