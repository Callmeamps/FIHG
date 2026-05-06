# PRD: Memory FIHG

## 1. Purpose
Memory FIHG is the synth's persistence layer for experiences, facts, preferences, episodes, and meaning. It is not a flat note store. It is a living graph of remembered events, concepts, associations, and trust.

## 2. Problem Statement
A synth without structured memory repeats itself, forgets useful context, and cannot learn from interaction history. Memory must support retrieval, decay, reinforcement, contradiction handling, and abstraction.

## 3. Goals
- Store episodic, semantic, and preference memory.
- Support retrieval by meaning, not only exact keywords.
- Track source reliability and recency.
- Reinforce important memories and decay stale ones.
- Represent memories as connected events and concepts.
- Enable memory-to-skill and memory-to-identity feedback.

## 4. Non-Goals
- General tool execution.
- Persona rendering.
- Direct user-facing explanation of all memory internals.
- Unbounded archival of every raw token.

## 5. Primary Users
- The synth's internal reasoning and planning systems.
- Internal agents that need recall of prior interactions.
- Administrators curating retention and forgetting rules.

## 6. Core Capabilities
### 6.1 Episodic Memory
Stores interaction episodes, sessions, and events.

### 6.2 Semantic Memory
Stores durable facts, concepts, and relations.

### 6.3 Preference Memory
Stores stable user preferences and style signals.

### 6.4 Trust and Source Graph
Tracks where memory came from and how reliable it is.

### 6.5 Decay and Reinforcement
Frequent, useful memories become stronger. Unused memories fade.

### 6.6 Contradiction Management
Conflicting memories are retained with provenance and confidence, not blindly overwritten.

## 7. Data Model
### Nodes
- event
- fact
- concept
- preference
- source
- session
- theme

### Edges
- refers_to
- reinforces
- contradicts
- derived_from
- similar_to
- occurred_before
- supports

### Example Hyperedge
- {user, topic, mood, outcome, timestamp} -> memory_episode

## 8. Memory Subdomains
### 8.1 Episodic Graph
Concrete interaction records.

### 8.2 Semantic Graph
Abstract concepts and stable facts.

### 8.3 Preference Graph
User and synth preferences.

### 8.4 Temporal Graph
Sequences, recency, and lifecycle states.

### 8.5 Trust Graph
Source authority and confidence propagation.

## 9. Success Metrics
- High recall on relevant prior context
- Low retrieval noise
- Low contradiction loss
- Better outcomes after prior exposure
- Measurable decay of unused memory

## 10. Key Risks
- Memory bloat
- False certainty
- Overfitting to old context
- Retrieval pollution
- Conflicting memories creating bad synthesis

## 11. MVP Scope
- Episodic store
- Semantic store
- Preference store
- Confidence and timestamp metadata
- Retrieval by graph neighborhood plus vector similarity
- Simple decay rules

## 12. Future Extensions
- Project-specific memory subgraphs
- Time-based memory phases
- Emotion/importance weighting
- Memory consolidation into summaries
- User-visible memory review and correction

## 13. Acceptance Criteria
- The synth recalls relevant past context when needed.
- Important memories survive longer than trivial ones.
- Conflicts are trackable and not silently destroyed.
- Memory improves response quality over repeated use.
