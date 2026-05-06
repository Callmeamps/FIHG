# FIHG Project Scratchpad

## Session: 2026-05-06 - Phase 1 & 2 Complete

### Commits
| Commit | Message | Issues |
|--------|---------|--------|
| ebbb873 | event log + session state persistence | Projects-azo, Projects-8ib |
| 9b9c333 | kilocode STV enhancements (Droop quota, transfers) | Projects-69v |
| f49bb62 | metrics aggregation module | Projects-bhg |
| 6600f76 | cross-graph Gremlin traversals | Projects-5td |
| fee97c5 | Phase 1 implementation (core modules) | Projects-0p6, f72, dyv, iwa, h99, 9r4 |
| b48a26a | FIHG project structure scaffolding | - |

### Phase 1 - Foundation ✅ COMPLETE
- ArcadeDB 3 graphs setup ✅
- SQLite schema ✅
- Python scaffolding ✅
- Identity FIHG schema ✅
- Memory FIHG schema ✅
- Skills FIHG schema ✅

### Phase 2 - Core ✅ COMPLETE
- Cross-graph bridges ✅
- STV runner-up storage ✅
- Metrics aggregation ✅
- Event log querying ✅
- Session state persistence ✅

### Phase 3 - Polish (NOT STARTED)
- Pending: J, K issues

### Subagent Issues Encountered
1. **Worktrees created outside FIHG directory** - Were at `/home/callmeamps/Desktop/Projects/worktrees/` instead of inside FIHG. Fixed by creating new worktrees in `FIHG/worktrees/`.
2. **Worktrees on wrong branches** - Original worktrees were on old commits (b4b2c99) before FIHG existed. Fixed by removing and recreating on main.
3. **subagent_opencode returned "No result provided"** - Work was actually done (commit 812530f), but tool didn't communicate result back.
4. **subagent_kilocode returned "No result provided"** - Same issue.
5. **subagent_gemini needs trust flag** - Fails with "not running in trusted directory". Needs `GEMINI_CLI_TRUST_WORKSPACE=true` env var or `--skip-trust`.

**Recommendation**: For future parallel work, implement directly rather than using subagents. The tool communication overhead and failures make them less efficient than direct implementation.

### Current Status
- 57 tests passing ✅
- 0 issues in progress ✅
- 45 issues closed ✅
- All Phase 1 & 2 work complete ✅
- Worktrees exist at `FIHG/worktrees/` (opencode-metrics, kilocode-stv, gemini-skills) - can be cleaned up
