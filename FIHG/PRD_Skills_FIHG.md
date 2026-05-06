# PRD: Skills FIHG

## 1. Purpose
Skills FIHG is the capability layer of a synth. It models what the synth can do, how well it can do it, what it depends on, and how those abilities change over time.

## 2. Problem Statement
A synth needs more than a generic "can do" list. Skills are not static labels. They are networks of subskills, dependencies, confidence, recency, transfer, and task fit.

## 3. Goals
- Represent skills as connected capability graphs.
- Support subskills, prerequisites, and transferable abilities.
- Track proficiency, confidence, speed, and rustiness.
- Activate skill clusters based on task context.
- Learn from outcomes and feedback.
- Link skills to memory and identity layers.

## 4. Non-Goals
- Long-term factual storage.
- Persona control.
- Full tool orchestration.
- Raw user preference management.

## 5. Primary Users
- Internal planners selecting capabilities.
- Schedulers and orchestrators assigning work.
- Administrators defining skill taxonomy and benchmarks.

## 6. Core Capabilities
### 6.1 Skill Nodes
Each skill is a node that can represent:
- a domain
- a method
- a tool proficiency
- a subskill
- a composite capability

### 6.2 Skill Edges
Edges can represent:
- depends_on
- strengthens
- transfers_to
- blocks
- overlaps_with
- composes_into

### 6.3 Skill State
Each skill may track:
- confidence
- proficiency
- freshness
- recent_success
- latency
- error_rate

### 6.4 Skill Activation
A task request can activate multiple skills at once.

### 6.5 Skill Decay and Recovery
Unused skills weaken. Repeated practice restores strength.

## 7. Data Model
### Nodes
- domain
- method
- tool
- subskill
- composite_skill
- benchmark

### Edges
- depends_on
- improves
- transfers_to
- competes_with
- composes_into
- blocked_by
- validated_by

### Example Hyperedge
- {python, api_design, debugging} -> backend_build_task

## 8. Skill Families
### 8.1 Technical Skills
Coding, debugging, architecture, deployment.

### 8.2 Communication Skills
Summarization, tone control, persuasion, instruction design.

### 8.3 Analytical Skills
Reasoning, decomposition, pattern finding, forecasting.

### 8.4 Creative Skills
Writing, music, ideation, visual framing.

### 8.5 Operational Skills
Scheduling, execution, verification, tool chaining.

## 9. Success Metrics
- Higher task completion quality
- Better skill selection accuracy
- Skill confidence matches actual performance
- Lower repeated failure rates
- Improved transfer between related skills

## 10. Key Risks
- Overstating capability
- Skill fragmentation
- Incorrect routing to a weak skill
- Skill decay becoming too aggressive
- Capability confusion between adjacent domains

## 11. MVP Scope
- Skill taxonomy
- Skill confidence scoring
- Prerequisite graph
- Outcome feedback loop
- Simple activation rules

## 12. Future Extensions
- Skill subgraphs that expand recursively
- Benchmarks per skill family
- Skill rehearsal and recovery
- Context-specific skill modes
- Cross-synth shared skill graphs

## 13. Acceptance Criteria
- The synth can pick the right capability cluster for a task.
- Skill performance updates after use.
- Dependencies are visible.
- Related skills influence each other.
- Weak skills are not treated as strong ones.
