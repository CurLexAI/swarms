# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for the repository dependency-graph analyzer.

These lock in the correctness of the graph algorithms (cycle detection,
topological sort, connected components, BFS) and the import-resolution rules
that the generated reports' headline claims (e.g. "0 cycles", degree
centrality) depend on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.analysis.repo_graph_analysis import (
    Graph,
    _PyResolver,
    _ts_candidates,
    _to_json,
    analyze,
    build_python_graph,
)

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analysis" / "repo_graph_analysis.py"


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
    # A TS importer of a .js specifier should resolve to the .ts source.
    cands = _ts_candidates("src/services/adapter.ts", "./AuditService.js")
    ts = "src/services/AuditService.ts"
    js = "src/services/AuditService.js"
    assert ts in cands and js in cands
    assert cands.index(ts) < cands.index(js)


def test_ts_candidates_js_importer_keeps_js_target() -> None:
    # A real .js importer must keep its .js target (no redirect to .ts).
    cands = _ts_candidates("src/services/adapter.js", "./AuditService.js")
    ts = "src/services/AuditService.ts"
    js = "src/services/AuditService.js"
    assert cands.index(js) < cands.index(ts)


def test_degree_table_breaks_ties_by_name() -> None:
    # x and y both have in=1/out=0; the tie must resolve by name, not hash order.
    g = _graph([("z", "x"), ("a", "y")])
    rows = g.degree_table()
    tied = [n for n, indeg, outdeg in rows if (indeg, outdeg) == (1, 0)]
    assert tied == ["x", "y"]


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_build_python_graph_over_fixture(tmp_path: Path) -> None:
    # End-to-end: real file parsing -> graph, including a relative-import cycle,
    # a one-way edge, and a stdlib import that must NOT become an edge.
    _write(tmp_path / "pkg" / "__init__.py", "")
    _write(tmp_path / "pkg" / "a.py", "from .b import thing\n")
    _write(tmp_path / "pkg" / "b.py", "from .a import other\n")  # a <-> b cycle
    _write(tmp_path / "pkg" / "c.py", "import os\nfrom .a import z\n")  # os ignored

    g, _index = build_python_graph(tmp_path)

    assert {"pkg/a.py", "pkg/b.py", "pkg/c.py", "pkg/__init__.py"} <= g.nodes
    assert "pkg/b.py" in g.out["pkg/a.py"]
    assert "pkg/a.py" in g.out["pkg/b.py"]
    assert "pkg/a.py" in g.out["pkg/c.py"]
    # ``import os`` must not fabricate an intra-repo edge.
    assert all(not t.startswith("os") for t in g.out["pkg/c.py"])
    assert len(g.detect_cycles()) == 1


def test_analyze_and_to_json_shape(tmp_path: Path) -> None:
    _write(tmp_path / "m" / "leaf.py", "x = 1\n")
    _write(tmp_path / "m" / "user.py", "from .leaf import x\n")
    g, _index = build_python_graph(tmp_path)
    res = analyze(g, "Python")
    payload = json.loads(_to_json(res, res))
    assert set(payload) == {"python", "typescript"}
    assert payload["python"]["node_count"] == len(g.nodes)
    assert payload["python"]["cycles"] == []


def test_cli_json_output_is_valid() -> None:
    # Protects the PR's "valid JSON" claim by exercising the real CLI entry point.
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    for eco in ("python", "typescript"):
        assert payload[eco]["node_count"] > 0
        assert isinstance(payload[eco]["cycles"], list)
