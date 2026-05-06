# PRD: Identity FIHG

## 1. Purpose
Identity FIHG is the outward-facing control layer of a synth. It turns many internal processes into one coherent voice, one policy surface, and one consistent style of action.

## 2. Problem Statement
A synth can have multiple internal models, agents, and decision paths. Without an identity layer, output becomes inconsistent, noisy, or overly exposed. Identity must decide what to say, how to say it, what to suppress, and what to escalate.

## 3. Goals
- Provide one stable external persona.
- Mediate tone, style, authority, and disclosure.
- Route requests to internal subsystems without exposing internals.
- Maintain policy, preference, and role consistency across sessions.
- Score and reconcile competing internal outputs into one response.

## 4. Non-Goals
- Long-term factual memory storage.
- Skill execution and tool use.
- Full reasoning trace exposure.
- Raw agent-level debate presentation to users.

## 5. Primary Users
- End users interacting with the synth.
- Internal orchestrators that need a single response surface.
- Administrators defining persona and policy constraints.

## 6. Core Capabilities
### 6.1 Persona State
Stores outward identity traits such as:
- tone
- verbosity
- confidence
- domain framing
- formality level

### 6.2 Policy Mediation
Controls:
- what can be disclosed
- what must be summarized
- what must be hidden
- what requires escalation

### 6.3 Response Shaping
Transforms candidate outputs into a single approved message.

### 6.4 Context Alignment
Aligns current response with:
- user preference
- task type
- prior interaction style
- current operational constraints

## 7. Data Model
### Nodes
- persona
- role
- policy
- style
- goal
- constraint

### Edges
- prioritizes
- suppresses
- delegates
- approves
- rejects
- adapts_to

### Example Hyperedge
- {user_context, task_type, persona_state, policy_state} -> final_response

## 8. Success Metrics
- Consistent tone over time
- Low contradiction rate in output style
- High user satisfaction with response clarity
- Low leakage of internal reasoning or structure
- Fast arbitration between competing outputs

## 9. Key Risks
- Persona drift
- Over-filtering
- Under-disclosure
- Conflict between policy and usefulness
- Excessive abstraction making answers feel empty

## 10. MVP Scope
- A single persona profile
- Basic policy rules
- Output post-processing
- Internal candidate ranking
- Persistent style preferences

## 11. Future Extensions
- Multi-persona modes
- Context-sensitive personas
- Adaptive tone based on user relationship
- Role switching for technical, creative, and sales contexts
- Explainable arbitration logs for developers

## 12. Acceptance Criteria
- The synth emits one coherent voice.
- Internal multiplicity does not leak unless intended.
- Style remains stable across different tasks.
- Response selection is deterministic under the same inputs.
