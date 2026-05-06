# FIHG PRD Bundle

## Project goal

Build a modular synth architecture made of three first-class interhypergraph domains, or **FIHGs**:

- **Identity FIHG**: governs outward behavior, style, priorities, and control.
- **Memory FIHG**: stores episodic, semantic, temporal, and trust-linked memory.
- **Skills FIHG**: models capabilities, dependencies, confidence, and skill transfer.

These three FIHGs are connected through an overarching synth architecture so they can coordinate without collapsing into one flat system.

## Files included

- `PRD_Identity_FIHG.md`
- `PRD_Memory_FIHG.md`
- `PRD_Skills_FIHG.md`
- `Spec_Overarching_FIHG_Architecture.md`

## Glossary

**FIHG**  
First-Class Interhypergraph. A graph-of-graphs architecture where a domain is treated as its own recursive, layered network.

**Synth**  
A composite system with one external identity and multiple internal capabilities, agents, and control layers.

**Intergraph**  
A graph that connects to other graphs. Used for bridging domains, layers, or subsystems.

**Hypergraph**  
A graph where a single edge can connect more than two nodes at once. Useful for events, groups, and shared states.

**Hyperedge**  
The multi-node relationship inside a hypergraph.

**Identity FIHG**  
The domain that controls the synth's outward persona, priorities, policies, and response shaping.

**Memory FIHG**  
The domain that manages episodes, facts, meaning, trust, decay, and retrieval pathways.

**Skills FIHG**  
The domain that models what the synth can do, how skills depend on each other, and how capability changes over time.

**Node**  
A thing, concept, agent, or state object inside the graph.

**Edge**  
A relationship between nodes. Can carry metadata, direction, weight, or multiple weights.

**Weight**  
A numerical or symbolic measure attached to a relationship, such as trust, latency, frequency, or cost.

**Metadata**  
Extra information attached to a node, edge, or hyperedge.

**Traffic**  
Activity flowing through nodes or edges. High traffic usually means high use.

**Wear**  
Accumulated load, strain, or degradation from repeated activity.

**Clarity / Brightness**  
A live state signal for how active, fresh, visible, or healthy a node or edge is.

**Bridge**  
A connection between FIHGs, such as Memory feeding Identity or Skills informing task selection.

**Fractal**  
A structure that repeats at multiple scales. In this project, subgraphs can contain subgraphs of the same kind.

## Notes

This bundle is designed as a working architecture document set, not a final implementation.
