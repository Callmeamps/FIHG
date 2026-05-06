# Identity / Coordination FIHG: Technical Implementation Spec

## 1. Purpose

The Identity / Coordination FIHG is the outward face and control layer of the synth. It decides:
- how the synth speaks,
- which goals matter first,
- what can be done,
- which internal agents get called,
- how conflicts are resolved.

This is not just a prompt. It is a governance graph.

## 2. What this FIHG contains

### Core node types
- persona
- value
- rule
- goal
- permission
- policy
- style
- safety constraint
- delegation slot
- attention token

### Core edge types
- prioritizes
- permits
- blocks
- delegates_to
- overrides
- softens
- escalates
- suppresses
- resolves_with

### Example
```text
concise_style -> blocks -> long_winded_output
helpfulness -> prioritizes -> direct_answer
safety_policy -> overrides -> stylistic_preference
```

## 3. Main jobs

### 3.1 Style shaping
This FIHG controls tone and format.

Example:
- user asks for a quick answer
- identity graph favors short paths
- long explanations are suppressed unless needed

### 3.2 Policy arbitration
When two rules clash, use the policy graph plus STV ranking.

Example conflict:
- be brief
- provide examples
- avoid overloading the user

Candidate outcomes are ranked, then STV selects the best response pattern [4].

### 3.3 Agent dispatch
Identity does not solve tasks directly. It chooses who should.

Example:
- graph question -> graph specialist
- memory question -> memory specialist
- synthesis question -> coordinator

### 3.4 Public identity stability
The same user should feel one consistent synth.

That means:
- stable voice
- consistent defaults
- predictable response structure
- transparent escalation when uncertain

## 4. Suggested internal schema

Inherits shared primitives from `fihg_holistic.md`. Extends with Identity-specific fields:

### Table: `identity_nodes` (extends base Node)
- importance
- activation
- last_used_at

### Table: `identity_edges` (extends base Edge)
- rule_scope
- trigger_condition

### Table: `policy_votes`
- task_id
- candidate_id
- rank
- voter_type
- weight
- rationale

### Table: `policy_outcomes`
- task_id
- winner_id
- runner_ups[]
- rejected_ids[]
- explanation

## 5. Common implementation methods

### Method A: rule graph
A direct graph of rules and exceptions.

Good for:
- strict behaviors
- safety
- style enforcement

### Method B: policy router
A controller that takes candidate actions and uses STV for final choice.

Good for:
- multiple competing reply shapes
- multiple internal agents
- limited tool slots

### Method C: prompt + graph hybrid
Use a compact system prompt for baseline behavior, then let the graph layer modify and route.

This is the most practical path.

## 6. STV use in identity

### Example scenario
The synth must decide how to answer:
- Option A: compact
- Option B: detailed
- Option C: example-heavy
- Option D: question-first

STV criteria for Identity:
- user preference alignment
- style consistency
- policy compliance
- brevity vs completeness
- task complexity fit

STV elects one response path. Runner-ups are kept for later if the same style becomes better in a future context [4].

## 7. Examples of identity rules

### Example 1
```text
user_prefers_short -> prioritizes -> concise_answer
```

### Example 2
```text
high_uncertainty -> triggers -> explicit_uncertainty_notice
```

### Example 3
```text
multi_step_task -> delegates_to -> coordinator_agent
```

### Example 4
```text
safety_risk -> overrides -> style_preferences
```

## 8. Failure modes

### 8.1 Identity drift
The system starts sounding different across sessions.

Fix:
- keep a stable identity seed
- use versioned style policies
- store successful response patterns

### 8.2 Policy conflict loops
Rules keep fighting.

Fix:
- hard priority levels
- STV tie-break
- conflict logging
- runner-up retention

### 8.3 Over-delegation
Everything gets routed elsewhere.

Fix:
- define a “solve locally” threshold
- keep a direct answer path for simple queries

## 9. Example event record

```json
{
  "event": "response_policy_selected",
  "task": "summarize graph architecture",
  "candidates": [
    {"id": "brief_summary", "votes": 5},
    {"id": "detailed_walkthrough", "votes": 3},
    {"id": "example_first", "votes": 2}
  ],
  "winner": "brief_summary",
  "runner_ups": ["detailed_walkthrough", "example_first"]
}
```

## 10. Build order

1. identity rules
2. STV policy router
3. response style memory
4. delegation map
5. audit trail
6. conflict replay

## 11. References

See `references.md`.
