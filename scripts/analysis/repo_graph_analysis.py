#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Repository dependency graph analysis (stdlib-only).

Builds a directed dependency graph from intra-repository import edges and runs
classic graph algorithms over it:

  * DFS cycle detection      -> circular import / dependency loops
  * Kahn topological sort    -> a valid build/load order (when acyclic)
  * Connected components     -> isolated / orphaned files (on the undirected view)
  * BFS traversal            -> how dependencies fan out from a root node
  * Degree centrality        -> the most central / load-bearing modules

Two ecosystems are analyzed independently because their module-resolution rules
differ: Python (resolved with the ``ast`` module) and TypeScript/JavaScript
(resolved from relative ``import``/``require``/``export ... from`` specifiers).

The tool is intentionally dependency-free (Python standard library only) to
respect the repository dependency-safety policy. It only reads files; it never
executes the code it analyzes.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# Directories that never contain first-party source we want to graph.
EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".agents/skills",  # documentation playbooks, not import targets
}

TS_EXTS = (".ts", ".tsx", ".js", ".mjs", ".cjs", ".jsx")


# --------------------------------------------------------------------------- #
# Graph container
# --------------------------------------------------------------------------- #
class Graph:
    """A tiny directed graph keyed by node label (repo-relative path)."""

    def __init__(self) -> None:
        self.nodes: Set[str] = set()
        self.out: Dict[str, Set[str]] = defaultdict(set)
        self.inc: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, n: str) -> None:
        self.nodes.add(n)
        _ = self.out[n]
        _ = self.inc[n]

    def add_edge(self, a: str, b: str) -> None:
        if a == b:
            return  # ignore self-imports; they are not dependency cycles
        self.add_node(a)
        self.add_node(b)
        self.out[a].add(b)
        self.inc[b].add(a)

    # -- algorithms -------------------------------------------------------- #
    def detect_cycles(self) -> List[List[str]]:
        """DFS-based cycle detection.

        Uses the classic white/grey/black colouring. When DFS reaches a node
        currently on the recursion stack (grey) we have found a back edge and
        reconstruct the cycle from the stack.
        """
        WHITE, GREY, BLACK = 0, 1, 2
        color: Dict[str, int] = {n: WHITE for n in self.nodes}
        stack: List[str] = []
        cycles: List[List[str]] = []
        seen_signatures: Set[frozenset] = set()

        def dfs(u: str) -> None:
            color[u] = GREY
            stack.append(u)
            for v in sorted(self.out[u]):
                if color[v] == GREY:
                    idx = stack.index(v)
                    cycle = stack[idx:] + [v]
                    sig = frozenset(cycle[:-1])
                    if sig not in seen_signatures:
                        seen_signatures.add(sig)
                        cycles.append(cycle)
                elif color[v] == WHITE:
                    dfs(v)
            stack.pop()
            color[u] = BLACK

        for n in sorted(self.nodes):
            if color[n] == WHITE:
                dfs(n)
        return cycles

    def topological_sort(self) -> Tuple[Optional[List[str]], List[str]]:
        """Kahn's algorithm. Returns (order, remaining).

        ``order`` is a valid build/load order if the graph is acyclic. If a
        cycle exists, ``order`` is None and ``remaining`` lists the nodes that
        could never reach in-degree zero (i.e. tangled in cycles).

        Edge a -> b means "a imports b", so b must be built before a. We emit
        dependencies first by ordering on in-degree of the *reversed* graph.
        """
        indeg: Dict[str, int] = {n: 0 for n in self.nodes}
        for n in self.nodes:
            for m in self.out[n]:
                indeg[m] += 0  # ensure key exists
        # We want dependencies (things with no outgoing imports) first.
        outdeg: Dict[str, int] = {n: len(self.out[n]) for n in self.nodes}
        queue = deque(sorted(n for n in self.nodes if outdeg[n] == 0))
        order: List[str] = []
        outdeg = dict(outdeg)
        while queue:
            u = queue.popleft()
            order.append(u)
            for p in sorted(self.inc[u]):
                outdeg[p] -= 1
                if outdeg[p] == 0:
                    queue.append(p)
        if len(order) == len(self.nodes):
            return order, []
        remaining = sorted(n for n in self.nodes if n not in set(order))
        return None, remaining

    def connected_components(self) -> List[List[str]]:
        """Weakly connected components via BFS on the undirected projection."""
        adj: Dict[str, Set[str]] = defaultdict(set)
        for n in self.nodes:
            for m in self.out[n]:
                adj[n].add(m)
                adj[m].add(n)
        visited: Set[str] = set()
        components: List[List[str]] = []
        for start in sorted(self.nodes):
            if start in visited:
                continue
            comp: List[str] = []
            q = deque([start])
            visited.add(start)
            while q:
                u = q.popleft()
                comp.append(u)
                for v in sorted(adj[u]):
                    if v not in visited:
                        visited.add(v)
                        q.append(v)
            components.append(sorted(comp))
        components.sort(key=len, reverse=True)
        return components

    def bfs(self, root: str, max_depth: int = 6) -> List[Tuple[str, int]]:
        """BFS traversal of the dependency fan-out from ``root``."""
        if root not in self.nodes:
            return []
        visited = {root}
        q: deque = deque([(root, 0)])
        order: List[Tuple[str, int]] = []
        while q:
            u, d = q.popleft()
            order.append((u, d))
            if d >= max_depth:
                continue
            for v in sorted(self.out[u]):
                if v not in visited:
                    visited.add(v)
                    q.append((v, d + 1))
        return order

    def degree_table(self) -> List[Tuple[str, int, int]]:
        """Return (node, in_degree, out_degree) sorted by total degree desc."""
        rows = [(n, len(self.inc[n]), len(self.out[n])) for n in self.nodes]
        rows.sort(key=lambda r: (r[1] + r[2], r[1]), reverse=True)
        return rows


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
def is_excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = set(rel.split("/"))
    if parts & EXCLUDED_DIRS:
        return True
    for ex in EXCLUDED_DIRS:
        if "/" in ex and rel.startswith(ex + "/"):
            return True
    return False


def discover(root: Path, exts: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for fn in filenames:
            if fn.endswith(tuple(exts)):
                p = Path(dirpath) / fn
                if not is_excluded(p, root):
                    out.append(p)
    return sorted(out)


# --------------------------------------------------------------------------- #
# Python resolution
# --------------------------------------------------------------------------- #
def build_python_graph(root: Path) -> Tuple[Graph, Dict[str, str]]:
    files = discover(root, (".py",))
    rels = [f.relative_to(root).as_posix() for f in files]
    relset = set(rels)

    # Map dotted module path -> file for absolute import resolution. We index by
    # the file's directory chain so that e.g. "router.model_router" and
    # ".agents.router.model_router" both resolve.
    module_index: Dict[str, str] = {}
    for rel in rels:
        no_ext = rel[:-3]  # strip .py
        parts = no_ext.split("/")
        # Register every suffix of the path as a candidate dotted name.
        for i in range(len(parts)):
            dotted = ".".join(parts[i:])
            module_index.setdefault(dotted, rel)
        if parts[-1] == "__init__":
            pkg = ".".join(parts[:-1])
            for i in range(len(parts) - 1):
                dotted = ".".join(parts[i:-1])
                module_index.setdefault(dotted, rel)

    g = Graph()
    for rel in rels:
        g.add_node(rel)

    def resolve_relative(cur_rel: str, level: int, module: Optional[str]) -> Optional[str]:
        cur_parts = cur_rel[:-3].split("/")
        # current package directory parts (drop the module filename)
        base = cur_parts[:-1]
        # each extra level goes one directory up
        up = level - 1
        if up > len(base):
            return None
        base = base[: len(base) - up] if up else base
        target_parts = list(base)
        if module:
            target_parts += module.split(".")
        cand_module = "/".join(target_parts) + ".py"
        cand_pkg = "/".join(target_parts) + "/__init__.py"
        if cand_module in relset:
            return cand_module
        if cand_pkg in relset:
            return cand_pkg
        return None

    def resolve_absolute(module: str) -> Optional[str]:
        if module in module_index:
            return module_index[module]
        # try progressively shorter prefixes (pkg.mod.sub -> pkg.mod)
        parts = module.split(".")
        for i in range(len(parts), 0, -1):
            cand = ".".join(parts[:i])
            if cand in module_index:
                return module_index[cand]
        return None

    for f, rel in zip(files, rels):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"), filename=str(f))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target = None
                if node.level and node.level > 0:
                    target = resolve_relative(rel, node.level, node.module)
                elif node.module:
                    target = resolve_absolute(node.module)
                if target:
                    g.add_edge(rel, target)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target = resolve_absolute(alias.name)
                    if target:
                        g.add_edge(rel, target)
    return g, module_index


# --------------------------------------------------------------------------- #
# TypeScript / JavaScript resolution
# --------------------------------------------------------------------------- #
IMPORT_RE = re.compile(
    r"""(?:import\s[^'"]*?from\s*['"](?P<a>[^'"]+)['"])"""
    r"""|(?:import\s*['"](?P<b>[^'"]+)['"])"""
    r"""|(?:export\s[^'"]*?from\s*['"](?P<c>[^'"]+)['"])"""
    r"""|(?:require\(\s*['"](?P<d>[^'"]+)['"]\s*\))""",
    re.MULTILINE,
)


def build_ts_graph(root: Path) -> Graph:
    files = discover(root, TS_EXTS)
    rels = [f.relative_to(root).as_posix() for f in files]
    relset = set(rels)
    g = Graph()
    for rel in rels:
        g.add_node(rel)

    def resolve(cur_rel: str, spec: str) -> Optional[str]:
        if not spec.startswith("."):
            return None  # external package, skip
        base = Path(cur_rel).parent
        target = (base / spec).as_posix()
        target = os.path.normpath(target).replace("\\", "/")
        candidates = [target]
        # strip a trailing extension that may have been written explicitly
        for ext in TS_EXTS:
            if target.endswith(ext):
                stem = target[: -len(ext)]
                candidates += [stem + e for e in TS_EXTS]
        # bare specifier -> try each extension and index files
        for ext in TS_EXTS:
            candidates.append(target + ext)
            candidates.append((Path(target) / "index").as_posix() + ext)
        # .js specifier often maps to a .ts source (ESM convention)
        if target.endswith(".js"):
            candidates.append(target[:-3] + ".ts")
            candidates.append(target[:-3] + ".tsx")
        for c in candidates:
            if c in relset:
                return c
        return None

    for f, rel in zip(files, rels):
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in IMPORT_RE.finditer(text):
            spec = m.group("a") or m.group("b") or m.group("c") or m.group("d")
            if not spec:
                continue
            target = resolve(rel, spec)
            if target:
                g.add_edge(rel, target)
    return g


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def analyze(g: Graph, label: str, bfs_roots: int = 1) -> dict:
    cycles = g.detect_cycles()
    order, remaining = g.topological_sort()
    components = g.connected_components()
    degrees = g.degree_table()
    isolated = [n for n in g.nodes if not g.out[n] and not g.inc[n]]
    leaves = sorted(n for n in g.nodes if g.out[n] and not g.inc[n])  # not imported by anyone

    # Pick BFS roots by out-degree: a high fan-out node best illustrates how
    # dependencies propagate downstream through the project.
    by_outdeg = sorted(g.nodes, key=lambda n: (len(g.out[n]), len(g.inc[n])), reverse=True)
    roots = [n for n in by_outdeg if g.out[n]][:bfs_roots]
    bfs_runs = {r: g.bfs(r) for r in roots}

    return {
        "label": label,
        "node_count": len(g.nodes),
        "edge_count": sum(len(v) for v in g.out.values()),
        "cycles": cycles,
        "topo_order": order,
        "topo_remaining": remaining,
        "components": components,
        "degrees": degrees,
        "isolated": sorted(isolated),
        "entry_points": leaves,
        "bfs": bfs_runs,
    }


def fmt_section(res: dict) -> str:
    L = res["label"]
    lines: List[str] = []
    a = lines.append
    a(f"## {L} dependency graph\n")
    a(f"- Nodes (files): **{res['node_count']}**")
    a(f"- Edges (import relations): **{res['edge_count']}**")
    a(f"- Weakly connected components: **{len(res['components'])}**")
    a(f"- Circular dependencies detected: **{len(res['cycles'])}**\n")

    a("### Most central modules (degree centrality)\n")
    a("| Module | In (imported by) | Out (imports) | Total |")
    a("|---|---|---|---|")
    for n, ind, outd in res["degrees"][:12]:
        a(f"| `{n}` | {ind} | {outd} | {ind + outd} |")
    a("")

    a("### Circular dependencies (DFS cycle detection)\n")
    if not res["cycles"]:
        a("None found — the dependency graph is a DAG.\n")
    else:
        for i, cyc in enumerate(res["cycles"], 1):
            a(f"{i}. " + " → ".join(f"`{c}`" for c in cyc))
        a("")

    a("### Build / load order (topological sort)\n")
    if res["topo_order"] is None:
        a("Not possible — cycles present. Tangled nodes:")
        for n in res["topo_remaining"]:
            a(f"  - `{n}`")
        a("")
    else:
        a("Acyclic. First 20 in valid dependency-first order:")
        for n in res["topo_order"][:20]:
            a(f"  - `{n}`")
        a("")

    a("### Isolated / orphaned files (connected components)\n")
    if res["isolated"]:
        a("Files with **no** intra-repo import edges (in or out):")
        for n in res["isolated"]:
            a(f"  - `{n}`")
    else:
        a("No fully isolated files.")
    a("")
    small = [c for c in res["components"] if 1 < len(c) <= 3]
    if small:
        a("Small detached clusters (2–3 files, weakly connected to nothing else):")
        for c in small:
            a("  - " + ", ".join(f"`{x}`" for x in c))
        a("")

    a("### Dependency fan-out (BFS traversal)\n")
    for root, run in res["bfs"].items():
        a(f"From `{root}`:")
        by_depth: Dict[int, List[str]] = defaultdict(list)
        for node, d in run:
            by_depth[d].append(node)
        for d in sorted(by_depth):
            if d == 0:
                continue
            a(f"  - depth {d}: " + ", ".join(f"`{x}`" for x in by_depth[d]))
        a("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--bfs-roots", type=int, default=2)
    args = ap.parse_args()
    root = Path(args.root).resolve()

    py = build_python_graph(root)[0]
    ts = build_ts_graph(root)

    py_res = analyze(py, "Python", bfs_roots=args.bfs_roots)
    ts_res = analyze(ts, "TypeScript/JavaScript", bfs_roots=args.bfs_roots)

    if args.json:
        def clean(r: dict) -> dict:
            r = dict(r)
            r["degrees"] = r["degrees"][:25]
            r["bfs"] = {k: v for k, v in r["bfs"].items()}
            return r

        print(json.dumps({"python": clean(py_res), "typescript": clean(ts_res)}, indent=2))
        return 0

    print("# Repository Dependency Graph Analysis\n")
    print(f"Root: `{root.name}`  ·  analysis is read-only, stdlib-only.\n")
    print(fmt_section(py_res))
    print(fmt_section(ts_res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
