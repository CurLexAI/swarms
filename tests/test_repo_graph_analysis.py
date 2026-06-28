# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for the repository dependency-graph analyzer.

These lock in the correctness of the graph algorithms (cycle detection,
topological sort, connected components, BFS) and the import-resolution rules
that the generated reports' headline claims (e.g. "0 cycles", degree
centrality) depend on.
"""

from __future__ import annotations

from scripts.analysis.repo_graph_analysis import (
    Graph,
    _PyResolver,
    _ts_candidates,
)


def _graph(edges: list[tuple[str, str]]) -> Graph:
    g = Graph()
    for a, b in edges:
        g.add_edge(a, b)
    return g


def test_detect_cycles_finds_a_loop() -> None:
    g = _graph([("a", "b"), ("b", "c"), ("c", "a")])
    cycles = g.detect_cycles()
    assert len(cycles) == 1
    # The cycle closes back on its first node.
    assert cycles[0][0] == cycles[0][-1]
    assert set(cycles[0]) == {"a", "b", "c"}


def test_detect_cycles_empty_for_dag() -> None:
    g = _graph([("a", "b"), ("a", "c"), ("b", "c")])
    assert g.detect_cycles() == []


def test_self_edges_are_ignored() -> None:
    g = _graph([("a", "a")])
    assert g.out["a"] == set()
    assert g.detect_cycles() == []


def test_topological_sort_orders_dependencies_first() -> None:
    # a imports b, b imports c -> c then b then a.
    g = _graph([("a", "b"), ("b", "c")])
    order, remaining = g.topological_sort()
    assert remaining == []
    assert order is not None
    assert order.index("c") < order.index("b") < order.index("a")


def test_topological_sort_reports_tangled_nodes_on_cycle() -> None:
    # a<->b form a cycle; x imports leaf d, so x and d can still be ordered.
    g = _graph([("a", "b"), ("b", "a"), ("x", "d")])
    order, remaining = g.topological_sort()
    assert order is None
    assert set(remaining) == {"a", "b"}  # only the cycle is tangled


def test_connected_components_separates_islands() -> None:
    g = _graph([("a", "b"), ("c", "d")])
    g.add_node("lonely")
    comps = g.connected_components()
    assert [sorted(c) for c in comps] == [["a", "b"], ["c", "d"], ["lonely"]]


def test_bfs_reports_depth_per_node() -> None:
    g = _graph([("a", "b"), ("b", "c"), ("a", "c")])
    depths = dict(g.bfs("a"))
    assert depths["a"] == 0
    assert depths["b"] == 1
    assert depths["c"] == 1  # reached directly from a before b's edge


def test_degree_table_ranks_by_total_degree() -> None:
    g = _graph([("a", "hub"), ("b", "hub"), ("hub", "leaf")])
    rows = g.degree_table()
    assert rows[0][0] == "hub"  # in=2, out=1 -> highest total
    assert dict((n, (i, o)) for n, i, o in rows)["hub"] == (2, 1)


def test_py_resolver_skips_stdlib_collision() -> None:
    # A local module shares the stdlib name "types"; ``import types`` must NOT
    # resolve to it.
    resolver = _PyResolver(["pkg/types.py", "pkg/mod.py"])
    assert resolver.absolute("types") is None
    assert resolver.absolute("os.path") is None


def test_py_resolver_does_not_truncate_thirdparty_submodule() -> None:
    # ``from mcp.server.fastmcp import X`` must not bind to a local mcp/server.
    resolver = _PyResolver(["a/mcp/server.py"])
    assert resolver.absolute("mcp.server.fastmcp") is None
    assert resolver.absolute("mcp.server") == "a/mcp/server.py"


def test_py_resolver_matches_full_dotted_path() -> None:
    resolver = _PyResolver(["pkg/sub/mod.py", "pkg/__init__.py"])
    assert resolver.absolute("pkg.sub.mod") == "pkg/sub/mod.py"
    assert resolver.absolute("pkg") == "pkg/__init__.py"


def test_ts_candidates_prefer_ts_source_over_js_companion() -> None:
    cands = _ts_candidates("src/services/adapter.ts", "./AuditService.js")
    ts = "src/services/AuditService.ts"
    js = "src/services/AuditService.js"
    assert ts in cands and js in cands
    assert cands.index(ts) < cands.index(js)
