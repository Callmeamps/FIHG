# Overarching Spec: Synth FIHG Architecture

## 1. System Name
FIHG: Fractal Interhypergraph Grid.

## 2. Purpose
FIHG is the architecture for a synth composed of three primary first-class interhypergraphs:
- Identity FIHG
- Memory FIHG
- Skills FIHG

Each FIHG is independently structured but connected through controlled bridges to produce one coherent external synth.

## 3. System Principle
The synth is not a single monolith. It is a layered and recursive graph system:
- graph inside graph
- hyperedge inside graph
- graph connected to graph
- each domain capable of expansion into subgraphs

## 4. High-Level Roles
### Identity FIHG
Owns outward voice, policy, style, and arbitration.

### Memory FIHG
Owns persistence, recall, preference, episode history, and trust.

### Skills FIHG
Owns capabilities, subskills, dependencies, confidence, and performance.

## 5. Top-Level Flow
1. User request arrives.
2. Identity FIHG interprets the request through persona and policy.
3. Memory FIHG retrieves relevant past context.
4. Skills FIHG selects capability clusters.
5. Internal agents and tools execute tasks.
6. Results are scored, reconciled, and shaped by Identity FIHG.
7. Memory and Skills update based on the outcome.

## 6. Required Bridges
### 6.1 Identity ↔ Memory
- User preference affects tone and disclosure.
- Important episodes influence persona stability.
- Memory can modify response framing.

### 6.2 Identity ↔ Skills
- Identity decides which capabilities are appropriate to expose or use.
- Skill confidence can affect tone and certainty.

### 6.3 Memory ↔ Skills
- Practice strengthens capability.
- Past outcomes reinforce or weaken skills.
- Recalled episodes can trigger specialized capabilities.

## 7. Data Representation
Use property-graph style storage for nodes and edges, with hyperedges for group events.

### Node Examples
- persona
- episode
- fact
- skill
- subskill
- policy
- benchmark
- source

### Edge Examples
- prioritizes
- depends_on
- reinforces
- contradicts
- transfers_to
- suppresses
- approves

### Hyperedge Examples
- {user, task, persona_state, policy_state} -> response
- {event, source, confidence, timestamp} -> memory_episode
- {python, debugging, api_design} -> backend_delivery

## 8. State and Metrics
Every node and edge may have live attributes:
- weight
- confidence
- freshness
- frequency
- decay
- success_rate
- latency
- error_rate
- brightness / activity
- wear / load

Interpretation:
- high activity = bright
- low activity = dim
- overloaded = worn
- unused = fading

## 9. Recursion Model
Any major node may open into a subgraph.

Examples:
- a skill node may expand into subskills
- a memory node may expand into a project memory graph
- an identity node may expand into context-specific subpersonas

## 10. Build Order with Dependencies

### Independent Tasks (start now)
- **A**: ArcadeDB setup — 3 separate graphs (Identity, Memory, Skills)
- **B**: SQLite schema — event_log, threads, user_interactions, metrics
- **C**: Python scaffolding — project structure, gremlinpython integration, mock clients

### Depends on A
- **D**: Identity FIHG schema — vertex types, edge types, sample data
- **E**: Memory FIHG schema — vertex types, edge types, sample data
- **F**: Skills FIHG schema — vertex types, edge types, sample data

*Tasks D, E, F can run in parallel (separate graphs)*

### Depends on D + E + F
- **G**: Cross-graph Gremlin traversals — bridge implementation
- **H**: STV implementation — Python layer with runner-up storage
- **I**: Metrics aggregation — activity, error rate, success rate tracking

### Depends on G + H + I
- **J**: Decay and wear tracking — freshness scoring, confidence adjustment
- **K**: Hyperedge modeling — multi-party events as vertex+links

### Depends on B
- **L**: Session state persistence — thread context, synth state
- **M**: Event log querying — retrieval, filtering, aggregation

### Phase Summary
**Phase 1 (Foundation)**: A, B, C, D, E, F
**Phase 2 (Core)**: G, H, I, L, M
**Phase 3 (Polish)**: J, K

## 11. Storage Architecture

### Graph Stores (ArcadeDB)
Three separate ArcadeDB graphs, one per FIHG domain:
- **Identity Graph**: persona, policy, style, rules, goals
- **Memory Graph**: episodes, facts, concepts, preferences, trust
- **Skills Graph**: capabilities, dependencies, benchmarks, evidence

Each graph uses Gremlin for queries and traversals. ArcadeDB supports Neo4j Bolt protocol.

### Peripheral Storage (SQLite)
For non-graph data:
- `event_log`: timestamp, fihg, event_type, payload_json
- `threads`: id, user_id, created_at, status
- `user_interactions`: id, thread_id, user_input, synth_output, timestamp
- `session_state`: session_id, last_identity_state, last_memory_state, last_skills_state
- `metrics`: fihg, entity_id, activity_count, error_count, success_rate, last_updated
- `stv_outcomes`: task_id, winner, runner_ups_json, rejected, timestamp

### Hyperedges
Modeled as vertices with participant links (no native hyperedge support yet):
- Hyperedge vertex type with properties (event_type, time_window, provenance, outcome, score_vector)
- Participant links as regular edges
- Roles stored as properties on links

## 12. Runtime Loop
### Inbound
Request -> Identity interpretation

### Recall
Memory retrieval -> relevant episodes, facts, preferences

### Capability
Skills selection -> applicable capability cluster

### Execution
Tools and internal agents perform work

### STV Resolution
When the three FIHGs produce competing outputs, Single Transferable Vote (STV) resolves the conflict:
- Each FIHG submits a ranked preference list
- Votes transfer based on strength of preference
- Lowest-ranked candidate eliminated, votes redistributed
- Process repeats until one option has majority support

### Arbitration
Identity shapes final response after STV produces a winner

### STV Implementation
Single Transferable Vote runs in Python layer:
1. Gremlin queries fetch candidate data from ArcadeDB graphs
2. Each FIHG provides ranked preferences based on its criteria:
   - Identity: user preference, style consistency, policy compliance, brevity, complexity fit
   - Memory: relevance, recency, trust, salience, temporal precedence
   - Skills: confidence, cost, latency, recent success rate, evidence strength
3. Python runs STV algorithm (quota, transfer, eliminate, repeat)
4. Winner selected, runner-ups immediately fetched and stored
5. Outcome stored in SQLite `stv_outcomes` table
6. On future similar task or winner failure: check runner-ups first before re-running STV

### Learning
Memory and Skills update from the result

## 13. Main Risks
- Layer leakage
- Over-complexity
- Weak bridge design
- False confidence propagation
- Memory pollution
- Skill drift
- Identity inconsistency

## 14. MVP Definition
A minimal synth should be able to:
- answer with one coherent voice
- remember useful past context
- select appropriate skills
- update state from outcomes
- keep the three FIHGs separate but connected

## 15. Long-Term Vision
A mature FIHG synth behaves like a modular organism:
- identity as face
- memory as lived history
- skills as capability structure
- bridges as nervous system
- hyperedges as events
- recursion as growth

## 16. Acceptance Criteria
- The three FIHGs can be implemented independently.
- Each FIHG can expand into subgraphs.
- Cross-domain bridges work without collapsing the structure.
- The synth remains singular to the user while internally modular.
