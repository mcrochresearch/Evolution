#!/usr/bin/env python3
"""
WORKFLOW EVOLUTION — DAG Pipeline + AFlow + SEW Topology Optimization.

Inspired by EvoAgentX's AFlow (task decomposition exploration) and SEW
(Self-Evolving Workflow structure optimization). Represents the agent
pipeline as a directed acyclic graph (DAG) where:

- NODES are pipeline stages (each with a prompt, tools, and role)
- EDGES are data dependencies between stages
- The DAG ITSELF evolves: nodes can be added, removed, reordered, merged,
  or parallelized based on performance data

This is Optimizer #3 from the three-optimizer design: topology optimization.

Usage:
    python3 engine/workflow_evolution.py init <name> <description>
    python3 engine/workflow_evolution.py add-node <node_id> <role> <prompt> [depends_on_json]
    python3 engine/workflow_evolution.py remove-node <node_id>
    python3 engine/workflow_evolution.py add-edge <from_id> <to_id>
    python3 engine/workflow_evolution.py remove-edge <from_id> <to_id>
    python3 engine/workflow_evolution.py score-node <node_id> <fitness>
    python3 engine/workflow_evolution.py optimize            Run SEW optimization pass
    python3 engine/workflow_evolution.py aflow <task_desc>   Explore alternative decompositions
    python3 engine/workflow_evolution.py topology            Show current DAG
    python3 engine/workflow_evolution.py validate            Validate DAG (no cycles, connected)
    python3 engine/workflow_evolution.py execution-order     Get topological sort order
    python3 engine/workflow_evolution.py parallel-groups     Get parallelizable node groups
    python3 engine/workflow_evolution.py history
"""

import json
import os
import sys
import tempfile
from pathlib import Path

try:
    from engine.stats import now
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now

ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = ENGINE_DIR.parent
STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
WORKFLOW_STATE = STATE_DIR / "workflow.json"
MAX_HISTORY = 50


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_workflow_state() -> dict:
    """Load workflow state."""
    if WORKFLOW_STATE.exists():
        with open(WORKFLOW_STATE) as f:
            return json.load(f)
    return {
        "name": "",
        "description": "",
        "nodes": {},
        "edges": [],
        "version": 0,
        "optimization_history": [],
        "aflow_explorations": [],
    }


def _atomic_write(path: Path, data):
    """Write JSON atomically via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_workflow_state(state: dict):
    """Save workflow state (atomic write)."""
    for key in ("optimization_history", "aflow_explorations"):
        if key in state and len(state[key]) > MAX_HISTORY:
            state[key] = state[key][-MAX_HISTORY:]
    _atomic_write(WORKFLOW_STATE, state)


# ---------------------------------------------------------------------------
# DAG Construction
# ---------------------------------------------------------------------------

def cmd_init(name: str, description: str):
    """Initialize a new workflow DAG."""
    state = load_workflow_state()
    state["name"] = name
    state["description"] = description
    state["nodes"] = {}
    state["edges"] = []
    state["version"] = 1
    save_workflow_state(state)

    print(json.dumps({"status": "initialized", "name": name}))


def cmd_add_node(node_id: str, role: str, prompt: str, depends_on: list = None):
    """Add a node to the workflow DAG."""
    state = load_workflow_state()

    if node_id in state["nodes"]:
        print(json.dumps({"error": f"Node '{node_id}' already exists"}))
        sys.exit(1)

    state["nodes"][node_id] = {
        "id": node_id,
        "role": role,
        "prompt": prompt,
        "tools": [],
        "fitness_sum": 0.0,
        "evaluations": 0,
        "avg_fitness": 0.0,
        "created": now(),
        "active": True,
    }

    # Add dependency edges
    if depends_on:
        for dep in depends_on:
            if dep in state["nodes"]:
                edge = {"from": dep, "to": node_id}
                if edge not in state["edges"]:
                    state["edges"].append(edge)

    state["version"] += 1
    save_workflow_state(state)

    print(json.dumps({
        "status": "node_added",
        "node_id": node_id,
        "role": role,
        "dependencies": depends_on or [],
        "total_nodes": len(state["nodes"]),
    }))


def cmd_remove_node(node_id: str):
    """Remove a node and its edges from the DAG."""
    state = load_workflow_state()

    if node_id not in state["nodes"]:
        print(json.dumps({"error": f"Node '{node_id}' not found"}))
        sys.exit(1)

    del state["nodes"][node_id]
    state["edges"] = [e for e in state["edges"]
                      if e["from"] != node_id and e["to"] != node_id]
    state["version"] += 1
    save_workflow_state(state)

    print(json.dumps({
        "status": "node_removed",
        "node_id": node_id,
        "total_nodes": len(state["nodes"]),
    }))


def cmd_add_edge(from_id: str, to_id: str):
    """Add a dependency edge between two nodes."""
    state = load_workflow_state()

    for nid in (from_id, to_id):
        if nid not in state["nodes"]:
            print(json.dumps({"error": f"Node '{nid}' not found"}))
            sys.exit(1)

    edge = {"from": from_id, "to": to_id}
    if edge in state["edges"]:
        print(json.dumps({"error": "Edge already exists"}))
        sys.exit(1)

    state["edges"].append(edge)

    # Check for cycles
    if _has_cycle(state["nodes"], state["edges"]):
        state["edges"].remove(edge)
        print(json.dumps({"error": "Adding this edge would create a cycle"}))
        sys.exit(1)

    state["version"] += 1
    save_workflow_state(state)

    print(json.dumps({"status": "edge_added", "from": from_id, "to": to_id}))


def cmd_remove_edge(from_id: str, to_id: str):
    """Remove a dependency edge."""
    state = load_workflow_state()

    edge = {"from": from_id, "to": to_id}
    if edge not in state["edges"]:
        print(json.dumps({"error": "Edge not found"}))
        sys.exit(1)

    state["edges"].remove(edge)
    state["version"] += 1
    save_workflow_state(state)

    print(json.dumps({"status": "edge_removed", "from": from_id, "to": to_id}))


def cmd_score_node(node_id: str, fitness: float):
    """Record a fitness observation for a node."""
    fitness = max(0.0, min(1.0, fitness))
    state = load_workflow_state()

    if node_id not in state["nodes"]:
        print(json.dumps({"error": f"Node '{node_id}' not found"}))
        sys.exit(1)

    node = state["nodes"][node_id]
    node["fitness_sum"] += fitness
    node["evaluations"] += 1
    node["avg_fitness"] = round(node["fitness_sum"] / node["evaluations"], 4)
    save_workflow_state(state)

    print(json.dumps({
        "status": "scored",
        "node_id": node_id,
        "avg_fitness": node["avg_fitness"],
        "evaluations": node["evaluations"],
    }))


# ---------------------------------------------------------------------------
# DAG Analysis
# ---------------------------------------------------------------------------

def _has_cycle(nodes: dict, edges: list) -> bool:
    """Detect cycles using DFS."""
    adjacency = {nid: [] for nid in nodes}
    for e in edges:
        if e["from"] in adjacency:
            adjacency[e["from"]].append(e["to"])

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in nodes}

    def dfs(node):
        color[node] = GRAY
        for neighbor in adjacency.get(node, []):
            if color.get(neighbor) == GRAY:
                return True
            if color.get(neighbor) == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False

    return any(color[nid] == WHITE and dfs(nid) for nid in nodes)


def _topological_sort(nodes: dict, edges: list) -> list:
    """Kahn's algorithm for topological sort."""
    import heapq
    in_degree = {nid: 0 for nid in nodes}
    adjacency = {nid: [] for nid in nodes}

    for e in edges:
        if e["to"] in in_degree and e["from"] in adjacency:
            in_degree[e["to"]] += 1
            adjacency[e["from"]].append(e["to"])

    # Use a min-heap for O(n log n) deterministic ordering instead of O(n^2)
    heap = sorted(nid for nid in nodes if in_degree[nid] == 0)
    heapq.heapify(heap)
    order = []

    while heap:
        node = heapq.heappop(heap)
        order.append(node)
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                heapq.heappush(heap, neighbor)

    return order


def _parallel_groups(nodes: dict, edges: list) -> list:
    """Find groups of nodes that can execute in parallel (same topological level)."""
    in_degree = {nid: 0 for nid in nodes}
    adjacency = {nid: [] for nid in nodes}

    for e in edges:
        if e["to"] in in_degree and e["from"] in adjacency:
            in_degree[e["to"]] += 1
            adjacency[e["from"]].append(e["to"])

    groups = []
    queue = [nid for nid in nodes if in_degree[nid] == 0]

    while queue:
        groups.append(sorted(queue))
        next_queue = []
        for node in queue:
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_queue.append(neighbor)
        queue = next_queue

    return groups


def cmd_topology():
    """Show current DAG topology."""
    state = load_workflow_state()

    # Build adjacency dicts once instead of O(n*edges)
    deps_map = {nid: [] for nid in state["nodes"]}
    fwd_map = {nid: [] for nid in state["nodes"]}
    for e in state["edges"]:
        if e["to"] in deps_map:
            deps_map[e["to"]].append(e["from"])
        if e["from"] in fwd_map:
            fwd_map[e["from"]].append(e["to"])

    nodes_info = {}
    for nid, node in state["nodes"].items():
        nodes_info[nid] = {
            "role": node["role"],
            "prompt_preview": node["prompt"][:100],
            "avg_fitness": node["avg_fitness"],
            "evaluations": node["evaluations"],
            "depends_on": deps_map.get(nid, []),
            "feeds_into": fwd_map.get(nid, []),
            "active": node["active"],
        }

    print(json.dumps({
        "name": state["name"],
        "version": state["version"],
        "total_nodes": len(state["nodes"]),
        "total_edges": len(state["edges"]),
        "nodes": nodes_info,
        "execution_order": _topological_sort(state["nodes"], state["edges"]),
        "parallel_groups": _parallel_groups(state["nodes"], state["edges"]),
    }))


def cmd_validate():
    """Validate the DAG structure."""
    state = load_workflow_state()

    issues = []

    # Check for cycles
    if _has_cycle(state["nodes"], state["edges"]):
        issues.append("CRITICAL: DAG contains cycles")

    # Check for disconnected nodes
    connected = set()
    for e in state["edges"]:
        connected.add(e["from"])
        connected.add(e["to"])
    if len(state["nodes"]) > 1:
        disconnected = set(state["nodes"].keys()) - connected
        if disconnected:
            issues.append(f"WARNING: Disconnected nodes: {sorted(disconnected)}")

    # Check for missing edge targets
    for e in state["edges"]:
        if e["from"] not in state["nodes"]:
            issues.append(f"ERROR: Edge references missing node '{e['from']}'")
        if e["to"] not in state["nodes"]:
            issues.append(f"ERROR: Edge references missing node '{e['to']}'")

    # Check for low-fitness nodes
    for nid, node in state["nodes"].items():
        if node["evaluations"] >= 5 and node["avg_fitness"] < 0.3:
            issues.append(f"WARNING: Node '{nid}' has low fitness ({node['avg_fitness']:.2f}) — consider replacing")

    valid = not any(i.startswith("CRITICAL") or i.startswith("ERROR") for i in issues)

    print(json.dumps({
        "valid": valid,
        "issues": issues,
        "node_count": len(state["nodes"]),
        "edge_count": len(state["edges"]),
    }))


def cmd_execution_order():
    """Get topological sort execution order."""
    state = load_workflow_state()
    order = _topological_sort(state["nodes"], state["edges"])
    print(json.dumps({"execution_order": order}))


def cmd_parallel_groups():
    """Get groups of nodes that can execute in parallel."""
    state = load_workflow_state()
    groups = _parallel_groups(state["nodes"], state["edges"])
    print(json.dumps({
        "parallel_groups": groups,
        "max_parallelism": max(len(g) for g in groups) if groups else 0,
        "pipeline_depth": len(groups),
    }))


# ---------------------------------------------------------------------------
# SEW — Self-Evolving Workflow Optimization
# ---------------------------------------------------------------------------

def cmd_optimize():
    """Run one SEW optimization pass on the workflow.

    Analyzes node fitness data and recommends structural changes:
    1. Remove consistently low-performing nodes
    2. Split overloaded nodes (high variance = trying to do too much)
    3. Merge redundant nodes (similar roles, both performing well)
    4. Suggest parallelization opportunities
    """
    state = load_workflow_state()

    recommendations = []
    nodes = state["nodes"]

    # 1. Identify nodes to remove (consistently poor)
    for nid, node in nodes.items():
        if node["evaluations"] >= 5 and node["avg_fitness"] < 0.2:
            recommendations.append({
                "action": "REMOVE",
                "node_id": nid,
                "reason": f"Consistently low fitness ({node['avg_fitness']:.2f} over {node['evaluations']} evals)",
                "priority": "HIGH",
            })

    # 2. Identify overloaded nodes (high variance suggests doing too much)
    # We approximate variance from the limited data we have
    for nid, node in nodes.items():
        if node["evaluations"] >= 5:
            # If avg fitness is middling despite many evals, node might be inconsistent
            if 0.3 <= node["avg_fitness"] <= 0.6:
                recommendations.append({
                    "action": "SPLIT",
                    "node_id": nid,
                    "reason": f"Middling fitness ({node['avg_fitness']:.2f}) after {node['evaluations']} evals — consider splitting into focused sub-nodes",
                    "priority": "MEDIUM",
                })

    # 3. Identify merge candidates (similar roles, both decent)
    node_list = list(nodes.items())
    for i in range(len(node_list)):
        for j in range(i + 1, len(node_list)):
            nid1, n1 = node_list[i]
            nid2, n2 = node_list[j]
            if (n1["role"] == n2["role"]
                    and n1["avg_fitness"] >= 0.5
                    and n2["avg_fitness"] >= 0.5):
                recommendations.append({
                    "action": "MERGE",
                    "nodes": [nid1, nid2],
                    "reason": f"Same role '{n1['role']}' with similar fitness — consider merging to reduce pipeline complexity",
                    "priority": "LOW",
                })

    # 4. Parallelization opportunities
    groups = _parallel_groups(nodes, state["edges"])
    for group in groups:
        if len(group) == 1:
            # Single node in a level — check if it could be parallelized with neighbors
            nid = group[0]
            dependents = [e["to"] for e in state["edges"] if e["from"] == nid]
            if len(dependents) >= 2:
                recommendations.append({
                    "action": "PARALLELIZE",
                    "node_id": nid,
                    "downstream": dependents,
                    "reason": f"Node '{nid}' feeds {len(dependents)} independent nodes — they could run in parallel",
                    "priority": "MEDIUM",
                })

    record = {
        "version": state["version"],
        "recommendations": recommendations,
        "node_count": len(nodes),
        "timestamp": now(),
    }
    state["optimization_history"].append(record)
    save_workflow_state(state)

    print(json.dumps({
        "status": "optimized",
        "recommendations": recommendations,
        "total_recommendations": len(recommendations),
        "version": state["version"],
    }))


# ---------------------------------------------------------------------------
# AFlow — Alternative Task Decomposition Exploration
# ---------------------------------------------------------------------------

def cmd_aflow(task_description: str):
    """Explore alternative task decompositions (AFlow pattern).

    Given a task description, generate multiple ways to decompose it
    into a pipeline of steps. Each decomposition is a different "flow"
    that could be evaluated.
    """
    state = load_workflow_state()

    # Generate 3 alternative decompositions
    decompositions = []

    # Strategy 1: Sequential (simple linear chain)
    decompositions.append({
        "strategy": "sequential",
        "description": "Simple linear pipeline — each step feeds the next",
        "nodes": [
            {"id": "analyze", "role": "analyzer", "prompt": f"Analyze the task: {task_description[:200]}"},
            {"id": "plan", "role": "planner", "prompt": "Create a concrete plan based on the analysis"},
            {"id": "execute", "role": "executor", "prompt": "Execute the plan step by step"},
            {"id": "verify", "role": "verifier", "prompt": "Verify the execution meets requirements"},
        ],
        "edges": [
            {"from": "analyze", "to": "plan"},
            {"from": "plan", "to": "execute"},
            {"from": "execute", "to": "verify"},
        ],
    })

    # Strategy 2: Parallel analysis + converge
    decompositions.append({
        "strategy": "parallel_analysis",
        "description": "Parallel analysis from multiple angles, then converge",
        "nodes": [
            {"id": "decompose", "role": "decomposer", "prompt": f"Break down: {task_description[:200]}"},
            {"id": "analyze_risk", "role": "risk_analyzer", "prompt": "Analyze risks and failure modes"},
            {"id": "analyze_approach", "role": "approach_analyzer", "prompt": "Analyze possible approaches and trade-offs"},
            {"id": "synthesize", "role": "synthesizer", "prompt": "Synthesize parallel analyses into a unified plan"},
            {"id": "execute", "role": "executor", "prompt": "Execute the synthesized plan"},
        ],
        "edges": [
            {"from": "decompose", "to": "analyze_risk"},
            {"from": "decompose", "to": "analyze_approach"},
            {"from": "analyze_risk", "to": "synthesize"},
            {"from": "analyze_approach", "to": "synthesize"},
            {"from": "synthesize", "to": "execute"},
        ],
    })

    # Strategy 3: Iterative refinement
    decompositions.append({
        "strategy": "iterative_refinement",
        "description": "Quick draft, then refine in multiple passes",
        "nodes": [
            {"id": "draft", "role": "drafter", "prompt": f"Create a quick first draft for: {task_description[:200]}"},
            {"id": "critique", "role": "critic", "prompt": "Critique the draft — what's wrong, missing, or weak?"},
            {"id": "refine", "role": "refiner", "prompt": "Refine the draft based on the critique"},
            {"id": "validate", "role": "validator", "prompt": "Validate the refined output meets all requirements"},
        ],
        "edges": [
            {"from": "draft", "to": "critique"},
            {"from": "critique", "to": "refine"},
            {"from": "refine", "to": "validate"},
        ],
    })

    record = {
        "task": task_description[:200],
        "decomposition_count": len(decompositions),
        "strategies": [d["strategy"] for d in decompositions],
        "timestamp": now(),
    }
    state["aflow_explorations"].append(record)
    save_workflow_state(state)

    print(json.dumps({
        "status": "decompositions_generated",
        "task": task_description[:200],
        "decompositions": decompositions,
        "recommendation": "Evaluate each decomposition by running it and comparing fitness scores",
    }))


def cmd_history():
    """Show workflow evolution history."""
    state = load_workflow_state()
    print(json.dumps({
        "version": state["version"],
        "optimization_history": state["optimization_history"][-10:],
        "aflow_explorations": state["aflow_explorations"][-10:],
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: init <name> <description>"}))
            sys.exit(1)
        cmd_init(sys.argv[2], sys.argv[3])
    elif cmd == "add-node":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: add-node <node_id> <role> <prompt> [depends_on_json]"}))
            sys.exit(1)
        depends = json.loads(sys.argv[5]) if len(sys.argv) > 5 else None
        cmd_add_node(sys.argv[2], sys.argv[3], sys.argv[4], depends)
    elif cmd == "remove-node":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: remove-node <node_id>"}))
            sys.exit(1)
        cmd_remove_node(sys.argv[2])
    elif cmd == "add-edge":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: add-edge <from_id> <to_id>"}))
            sys.exit(1)
        cmd_add_edge(sys.argv[2], sys.argv[3])
    elif cmd == "remove-edge":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: remove-edge <from_id> <to_id>"}))
            sys.exit(1)
        cmd_remove_edge(sys.argv[2], sys.argv[3])
    elif cmd == "score-node":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: score-node <node_id> <fitness>"}))
            sys.exit(1)
        cmd_score_node(sys.argv[2], float(sys.argv[3]))
    elif cmd == "optimize":
        cmd_optimize()
    elif cmd == "aflow":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: aflow <task_description>"}))
            sys.exit(1)
        cmd_aflow(sys.argv[2])
    elif cmd == "topology":
        cmd_topology()
    elif cmd == "validate":
        cmd_validate()
    elif cmd == "execution-order":
        cmd_execution_order()
    elif cmd == "parallel-groups":
        cmd_parallel_groups()
    elif cmd == "history":
        cmd_history()
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
