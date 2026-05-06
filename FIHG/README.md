# FIHG — First-Class Interhypergraph Grid

A modular synth architecture with three first-class interhypergraph domains, connected through an overarching graph-of-graphs system.

## Architecture

Three independent FIHG graphs, each owning its domain:

| Graph | Domain | Purpose |
|-------|--------|---------|
| **Identity** | Persona & control | Governs outward behavior, style, priorities, arbitration |
| **Memory** | Storage & recall | Episodic, semantic, temporal, and trust-linked memory |
| **Skills** | Capabilities | Models skills, dependencies, confidence, and transfer |

Connected by explicit bridge edges — never collapsed into one flat graph.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| Graph DB | ArcadeDB (3 separate graphs) |
| Query Language | Gremlin |
| Python Client | gremlinpython (Apache TinkerPop) |
| Peripheral Storage | SQLite |

## Project Structure

```
FIHG/
├── src/
│   ├── core/                    # Shared primitives & cross-cutting concerns
│   │   ├── base.py              # BaseNode, BaseEdge, BaseHyperedge, GraphState
│   │   ├── bridges.py           # Cross-graph traversal and bridge managers
│   │   ├── decay.py             # DecayEngine — freshness & wear scoring
│   │   ├── hyperedges.py        # HyperedgeManager — multi-party events
│   │   ├── metrics.py           # Metrics aggregation per graph
│   │   ├── replay.py            # ReplayEngine — event history & summarization
│   │   └── subgraphs.py         # SubgraphManager — recursive subgraphs
│   ├── db/
│   │   ├── arcadedb.py          # ArcadeDB connection layer
│   │   ├── sqlite_schema.py     # SQLite schema (event_log, session_state)
│   │   ├── event_log.py         # EventLogQuerier — querying & aggregation
│   │   └── session_state.py     # SessionStateManager — cross-graph persistence
│   └── fihg/
│       ├── identity/            # Identity FIHG — STV voting, client
│       ├── memory/              # Memory FIHG — retrieval, client
│       └── skills/              # Skills FIHG — routing, client
├── tests/                       # Full test suite (130 tests)
├── fihg_holistic.md             # Architecture overview
├── PRD_Identity_FIHG.md         # Identity domain spec
├── PRD_Memory_FIHG.md           # Memory domain spec
├── PRD_Skills_FIHG.md           # Skills domain spec
└── README.md
```

## Completion Status

### Phase 1 — Foundation ✅
- ArcadeDB 3-graph setup
- SQLite schema (event_log, session_state)
- Python scaffolding with pydantic models
- Identity FIHG schema + STV voting base
- Memory FIHG schema + retrieval
- Skills FIHG schema + routing

### Phase 2 — Core ✅
- Cross-graph Gremlin bridge traversals
- STV enhancements: Droop quota, transfer values, runner-up storage
- Metrics aggregation per graph (activity, skill stats, memory retrieval, identity confidence)
- Event log querying with time windows, filters, aggregation
- Session state persistence across all 3 FIHG graphs

### Phase 3 — Polish ✅
- Hyperedge manager for multi-party events (create, query, resolve, stats)
- Recursive subgraph support (CRUD, merge, archive, entity tracking)
- Decay & wear scoring engine (exponential half-life freshness, error-ratio wear, batch operations)
- Replay & summarization (event timeline, session summary, graph activity reports, JSON export)

### Phase 4 — Advanced _(not started)_
- Cross-FIHG learning
- Automatic candidate promotion
- Adaptive governance

## Key Concepts

| Term | Meaning |
|------|---------|
| **FIHG** | First-Class Interhypergraph — a domain as its own recursive, layered network |
| **Synth** | Composite system with external identity + internal capabilities |
| **Hyperedge** | Multi-node relationship inside a hypergraph (events, groups, shared states) |
| **Bridge** | Connection between FIHG graphs |
| **STV** | Single Transferable Vote — conflict resolution across candidate responses |
| **Fractal** | Subgraphs containing subgraphs of the same kind |
| **Wear** | Accumulated degradation from activity and errors |
| **Clarity/Brightness** | Live state signal for node/edge health |

## Running Tests

```bash
cd FIHG
python -m pytest tests/ -v
```

130 tests, all passing.

## Design Principle

> Do not collapse everything into one giant graph. Let each FIHG own its own domain, then connect them with explicit bridge edges. That keeps the system recursive, debuggable, and extensible.
