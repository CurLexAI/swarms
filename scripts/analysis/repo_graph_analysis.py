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
executes the code it analyzes. The analysis root is fixed to this repository
(inferred from the script's own location), so no caller-supplied filesystem
path ever reaches a directory walk.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

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

# DFS node colours for cycle detection.
WHITE, GREY, BLACK = 0, 1, 2


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

    def detect_cycles(self) -> List[List[str]]:
        """DFS-based cycle detection (see :class:`_CycleFinder`)."""
        return _CycleFinder(self.out, self.nodes).find()

    def topological_sort(self) -> Tuple[Optional[List[str]], List[str]]:
        """Kahn's algorithm. Returns (order, remaining).

        Edge a -> b means "a imports b", so dependencies (out-degree zero) are
        emitted first. If a cycle exists, ``order`` is None and ``remaining``
        lists the nodes that never reach out-degree zero.
        """
        outdeg = {n: len(self.out[n]) for n in self.nodes}
        queue: Deque[str] = deque(sorted(n for n in self.nodes if outdeg[n] == 0))
        order: List[str] = []
        while queue:
            u = queue.popleft()
            order.append(u)
            self._relax_importers(u, outdeg, queue)
        if len(order) == len(self.nodes):
            return order, []
        placed = set(order)
        return None, sorted(n for n in self.nodes if n not in placed)

    def _relax_importers(self, u: str, outdeg: Dict[str, int], queue: Deque[str]) -> None:
        for p in sorted(self.inc[u]):
            outdeg[p] -= 1
            if outdeg[p] == 0:
                queue.append(p)

    def connected_components(self) -> List[List[str]]:
        """Weakly connected components via BFS on the undirected projection."""
        adj = self._undirected_adj()
        visited: Set[str] = set()
        components: List[List[str]] = []
        for start in sorted(self.nodes):
            if start not in visited:
                components.append(_bfs_undirected(start, adj, visited))
        components.sort(key=len, reverse=True)
        return components

    def _undirected_adj(self) -> Dict[str, Set[str]]:
        adj: Dict[str, Set[str]] = defaultdict(set)
        for n in self.nodes:
            for m in self.out[n]:
                adj[n].add(m)
                adj[m].add(n)
        return adj

    def bfs(self, root: str, max_depth: int = 6) -> List[Tuple[str, int]]:
        """BFS traversal of the dependency fan-out from ``root``."""
        if root not in self.nodes:
            return []
        visited = {root}
        q: Deque[Tuple[str, int]] = deque([(root, 0)])
        order: List[Tuple[str, int]] = []
        while q:
            u, d = q.popleft()
            order.append((u, d))
            if d < max_depth:
                self._enqueue_children(u, d, visited, q)
        return order

    def _enqueue_children(
        self, u: str, d: int, visited: Set[str], q: Deque[Tuple[str, int]]
    ) -> None:
        for v in sorted(self.out[u]):
            if v not in visited:
                visited.add(v)
                q.append((v, d + 1))

    def degree_table(self) -> List[Tuple[str, int, int]]:
        """Return (node, in_degree, out_degree) sorted by total degree desc."""
        rows = [(n, len(self.inc[n]), len(self.out[n])) for n in self.nodes]
        rows.sort(key=lambda r: (r[1] + r[2], r[1]), reverse=True)
        return rows


class _CycleFinder:
    """White/grey/black DFS that records each distinct back-edge cycle.

    State (colours, recursion stack, found cycles) lives on the instance so the
    recursive visit needs no long parameter list.
    """

    def __init__(self, out: Dict[str, Set[str]], nodes: Set[str]) -> None:
        self._out = out
        self._nodes = nodes
        self._color: Dict[str, int] = {n: WHITE for n in nodes}
        self._stack: List[str] = []
        self._cycles: List[List[str]] = []
        self._seen: Set[FrozenSet[str]] = set()

    def find(self) -> List[List[str]]:
        for n in sorted(self._nodes):
            if self._color[n] == WHITE:
                self._visit(n)
        return self._cycles

    def _visit(self, u: str) -> None:
        self._color[u] = GREY
        self._stack.append(u)
        for v in sorted(self._out[u]):
            self._step(v)
        self._stack.pop()
        self._color[u] = BLACK

    def _step(self, v: str) -> None:
        if self._color[v] == WHITE:
            self._visit(v)
        elif self._color[v] == GREY:
            self._record(v)

    def _record(self, v: str) -> None:
        cycle = self._stack[self._stack.index(v):] + [v]
        sig = frozenset(cycle[:-1])
        if sig not in self._seen:
            self._seen.add(sig)
            self._cycles.append(cycle)


def _bfs_undirected(start: str, adj: Dict[str, Set[str]], visited: Set[str]) -> List[str]:
    comp: List[str] = []
    q: Deque[str] = deque([start])
    visited.add(start)
    while q:
        u = q.popleft()
        comp.append(u)
        for v in sorted(adj[u]):
            if v not in visited:
                visited.add(v)
                q.append(v)
    return sorted(comp)


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
def is_excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if set(rel.split("/")) & EXCLUDED_DIRS:
        return True
    return any("/" in ex and rel.startswith(ex + "/") for ex in EXCLUDED_DIRS)


def discover(root: Path, exts: Iterable[str]) -> List[Path]:
    suffixes = tuple(exts)
    out: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        out.extend(_collect_files(dirpath, filenames, suffixes, root))
    return sorted(out)


def _collect_files(
    dirpath: str, filenames: List[str], suffixes: Tuple[str, ...], root: Path
) -> List[Path]:
    found: List[Path] = []
    for fn in filenames:
        if not fn.endswith(suffixes):
            continue
        p = Path(dirpath) / fn
        if not is_excluded(p, root):
            found.append(p)
    return found


# --------------------------------------------------------------------------- #
# Python resolution
# --------------------------------------------------------------------------- #
def _index_module(rel: str, index: Dict[str, str]) -> None:
    """Register every dotted-name suffix of one file path into ``index``."""
    parts = rel[:-3].split("/")  # strip .py
    for i in range(len(parts)):
        index.setdefault(".".join(parts[i:]), rel)
    if parts[-1] != "__init__":
        return
    for i in range(len(parts) - 1):
        index.setdefault(".".join(parts[i:-1]), rel)


def _build_module_index(rels: List[str]) -> Dict[str, str]:
    """Map dotted module names to files so both ``router.x`` and
    ``.agents.router.x`` resolve to the same module file."""
    index: Dict[str, str] = {}
    for rel in rels:
        _index_module(rel, index)
    return index


class _PyResolver:
    """Resolve Python import statements to repo-relative file paths."""

    def __init__(self, rels: List[str]) -> None:
        self.relset = set(rels)
        self.module_index = _build_module_index(rels)

    def from_import(self, cur_rel: str, node: ast.ImportFrom) -> Optional[str]:
        if node.level and node.level > 0:
            return self._relative(cur_rel, node.level, node.module)
        if node.module:
            return self.absolute(node.module)
        return None

    def _relative(self, cur_rel: str, level: int, module: Optional[str]) -> Optional[str]:
        base = cur_rel[:-3].split("/")[:-1]  # package dir of current module
        up = level - 1
        if up > len(base):
            return None
        target_parts = base[: len(base) - up] if up else list(base)
        if module:
            target_parts = target_parts + module.split(".")
        joined = "/".join(target_parts)
        for cand in (joined + ".py", joined + "/__init__.py"):
            if cand in self.relset:
                return cand
        return None

    def absolute(self, module: str) -> Optional[str]:
        # A stdlib/third-party top-level name (e.g. ``import types``) must not
        # masquerade as an intra-repo edge just because a local module shares
        # its basename (``.agents/providers/types.py``). Skip stdlib roots, and
        # match the FULL module path only: truncating (e.g.
        # ``mcp.server.fastmcp`` -> ``mcp.server``) would wrongly bind a
        # third-party submodule import to a local file sharing the suffix.
        if module.split(".")[0] in sys.stdlib_module_names:
            return None
        return self.module_index.get(module)


def _py_targets(tree: ast.AST, rel: str, resolver: _PyResolver) -> List[str]:
    targets: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            target = resolver.from_import(rel, node)
            if target:
                targets.append(target)
        elif isinstance(node, ast.Import):
            targets.extend(t for t in (resolver.absolute(a.name) for a in node.names) if t)
    return targets


def _safe_parse(path: Path) -> Optional[ast.AST]:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except SyntaxError:
        return None


def build_python_graph(root: Path) -> Tuple[Graph, Dict[str, str]]:
    files = discover(root, (".py",))
    rels = [f.relative_to(root).as_posix() for f in files]
    resolver = _PyResolver(rels)
    g = Graph()
    for rel in rels:
        g.add_node(rel)
    for f, rel in zip(files, rels):
        tree = _safe_parse(f)
        if tree is None:
            continue
        for target in _py_targets(tree, rel, resolver):
            g.add_edge(rel, target)
    return g, resolver.module_index


# --------------------------------------------------------------------------- #
# TypeScript / JavaScript resolution
# --------------------------------------------------------------------------- #
IMPORT_RE = re.compile(
    r"""(?:import\s[^'"]*?from\s*['"](?P<a>[^'"]+)['"])"""
    r"""|(?:import\s*['"](?P<b>[^'"]+)['"])"""
    r"""|(?:export\s[^'"]*?from\s*['"](?P<c>[^'"]+)['"])"""
    r"""|(?:require\(\s*['"](?P<d>[^'"]+)['"]\s*\))"""
    r"""|(?:import\(\s*['"](?P<e>[^'"]+)['"]\s*\))""",  # dynamic import()
    re.MULTILINE,
)

# Extensions that denote a (possibly compiled) JS artifact whose TypeScript
# source should be preferred when both are present (NodeNext .js specifiers).
_JS_EXTS = (".js", ".jsx", ".mjs", ".cjs")


def _ts_candidates(cur_rel: str, spec: str) -> List[str]:
    base = Path(cur_rel).parent
    target = os.path.normpath((base / spec).as_posix()).replace("\\", "/")
    matched = next((e for e in TS_EXTS if target.endswith(e)), "")
    if matched:
        stem = target[: -len(matched)]
        cands = []
        if matched in _JS_EXTS:
            # Prefer the TS source over a compiled JS companion of the same name.
            cands += [stem + ".ts", stem + ".tsx"]
        cands.append(target)
        cands += [stem + e for e in TS_EXTS]
        return cands
    # Bare specifier: try each extension and a directory index.
    cands = [target]
    for ext in TS_EXTS:
        cands.append(target + ext)
        cands.append((Path(target) / "index").as_posix() + ext)
    return cands


class _TsResolver:
    """Resolve relative TS/JS specifiers to repo-relative file paths."""

    def __init__(self, rels: List[str]) -> None:
        self.relset = set(rels)

    def resolve(self, cur_rel: str, spec: str) -> Optional[str]:
        if not spec.startswith("."):
            return None  # external package, skip
        for cand in _ts_candidates(cur_rel, spec):
            if cand in self.relset:
                return cand
        return None


def _ts_targets(path: Path, rel: str, resolver: _TsResolver) -> List[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    targets: List[str] = []
    for m in IMPORT_RE.finditer(text):
        spec = m.group("a") or m.group("b") or m.group("c") or m.group("d") or m.group("e")
        target = resolver.resolve(rel, spec) if spec else None
        if target:
            targets.append(target)
    return targets


def build_ts_graph(root: Path) -> Graph:
    files = discover(root, TS_EXTS)
    rels = [f.relative_to(root).as_posix() for f in files]
    resolver = _TsResolver(rels)
    g = Graph()
    for rel in rels:
        g.add_node(rel)
    for f, rel in zip(files, rels):
        for target in _ts_targets(f, rel, resolver):
            g.add_edge(rel, target)
    return g


# --------------------------------------------------------------------------- #
# Analysis + reporting
# --------------------------------------------------------------------------- #
def analyze(g: Graph, label: str, bfs_roots: int = 2) -> Dict[str, Any]:
    order, remaining = g.topological_sort()
    isolated = sorted(n for n in g.nodes if not g.out[n] and not g.inc[n])
    # Pick BFS roots by out-degree: high fan-out best illustrates propagation.
    by_outdeg = sorted(g.nodes, key=lambda n: (len(g.out[n]), len(g.inc[n])), reverse=True)
    roots = [n for n in by_outdeg if g.out[n]][:bfs_roots]
    return {
        "label": label,
        "node_count": len(g.nodes),
        "edge_count": sum(len(v) for v in g.out.values()),
        "cycles": g.detect_cycles(),
        "topo_order": order,
        "topo_remaining": remaining,
        "components": g.connected_components(),
        "degrees": g.degree_table(),
        "isolated": isolated,
        "bfs": {r: g.bfs(r) for r in roots},
    }


def _fmt_header(res: Dict[str, Any]) -> str:
    return "\n".join([
        f"## {res['label']} dependency graph\n",
        f"- Nodes (files): **{res['node_count']}**",
        f"- Edges (import relations): **{res['edge_count']}**",
        f"- Weakly connected components: **{len(res['components'])}**",
        f"- Circular dependencies detected: **{len(res['cycles'])}**\n",
    ])


def _fmt_centrality(res: Dict[str, Any]) -> str:
    lines = [
        "### Most central modules (degree centrality)\n",
        "| Module | In (imported by) | Out (imports) | Total |",
        "|---|---|---|---|",
    ]
    lines += [f"| `{n}` | {ind} | {outd} | {ind + outd} |" for n, ind, outd in res["degrees"][:12]]
    lines.append("")
    return "\n".join(lines)


def _fmt_cycles(res: Dict[str, Any]) -> str:
    lines = ["### Circular dependencies (DFS cycle detection)\n"]
    if not res["cycles"]:
        lines.append("None found — the dependency graph is a DAG.\n")
        return "\n".join(lines)
    lines += [f"{i}. " + " → ".join(f"`{c}`" for c in cyc) for i, cyc in enumerate(res["cycles"], 1)]
    lines.append("")
    return "\n".join(lines)


def _fmt_topo(res: Dict[str, Any]) -> str:
    lines = ["### Build / load order (topological sort)\n"]
    if res["topo_order"] is None:
        lines.append("Not possible — cycles present. Tangled nodes:")
        lines += [f"  - `{n}`" for n in res["topo_remaining"]]
        lines.append("")
        return "\n".join(lines)
    lines.append("Acyclic. First 20 in valid dependency-first order:")
    lines += [f"  - `{n}`" for n in res["topo_order"][:20]]
    lines.append("")
    return "\n".join(lines)


def _fmt_components(res: Dict[str, Any]) -> str:
    lines = ["### Isolated / orphaned files (connected components)\n"]
    if res["isolated"]:
        lines.append("Files with **no** intra-repo import edges (in or out):")
        lines += [f"  - `{n}`" for n in res["isolated"]]
    else:
        lines.append("No fully isolated files.")
    lines.append("")
    small = [c for c in res["components"] if 1 < len(c) <= 3]
    if small:
        lines.append("Small detached clusters (2–3 files, weakly connected to nothing else):")
        lines += ["  - " + ", ".join(f"`{x}`" for x in c) for c in small]
        lines.append("")
    return "\n".join(lines)


def _fmt_bfs_depths(run: List[Tuple[str, int]]) -> List[str]:
    by_depth: Dict[int, List[str]] = defaultdict(list)
    for node, d in run:
        by_depth[d].append(node)
    return [
        f"  - depth {d}: " + ", ".join(f"`{x}`" for x in by_depth[d])
        for d in sorted(by_depth)
        if d != 0
    ]


def _fmt_bfs(res: Dict[str, Any]) -> str:
    lines = ["### Dependency fan-out (BFS traversal)\n"]
    for root, run in res["bfs"].items():
        lines.append(f"From `{root}`:")
        lines += _fmt_bfs_depths(run)
        lines.append("")
    return "\n".join(lines)


def fmt_section(res: Dict[str, Any]) -> str:
    return "\n".join([
        _fmt_header(res),
        _fmt_centrality(res),
        _fmt_cycles(res),
        _fmt_topo(res),
        _fmt_components(res),
        _fmt_bfs(res),
    ])


def _to_json(py_res: Dict[str, Any], ts_res: Dict[str, Any]) -> str:
    def clean(r: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(r)
        out["degrees"] = out["degrees"][:25]
        return out

    return json.dumps({"python": clean(py_res), "typescript": clean(ts_res)}, indent=2)


def _repo_root() -> Path:
    """Repository root, inferred from this script's location.

    The root is a fixed, trusted constant (not caller input), so no untrusted
    value ever reaches the directory walk in :func:`discover`.
    """
    return Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--bfs-roots", type=int, default=2)
    args = ap.parse_args()
    root = _repo_root()

    py_res = analyze(build_python_graph(root)[0], "Python", args.bfs_roots)
    ts_res = analyze(build_ts_graph(root), "TypeScript/JavaScript", args.bfs_roots)

    if args.json:
        print(_to_json(py_res, ts_res))
        return 0

    print("# Repository Dependency Graph Analysis\n")
    print(f"Root: `{root.name}`  ·  analysis is read-only, stdlib-only.\n")
    print(fmt_section(py_res))
    print(fmt_section(ts_res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
