"""Helper: load `.agents` Python modules under a synthetic package for tests.

The `.agents` directory uses a leading dot, which is not a valid Python
identifier, and its modules use relative imports (e.g.
`from ..router.types import …`). This helper bootstraps a synthetic top-level
package `_agents_pkg` mapped to `.agents/` so test modules can do:

    from _agents_loader import bayyinah_gate, router_types
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".agents"


def _ensure_pkg(qualified: str, dir_path: Path) -> None:
    if qualified in sys.modules:
        return
    pkg = types.ModuleType(qualified)
    pkg.__path__ = [str(dir_path)]
    sys.modules[qualified] = pkg


def _load_module(qualified: str, file_path: Path):
    if qualified in sys.modules:
        return sys.modules[qualified]
    spec = importlib.util.spec_from_file_location(qualified, file_path)
    assert spec is not None and spec.loader is not None, qualified
    mod = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = mod
    spec.loader.exec_module(mod)
    return mod


_ensure_pkg("_agents_pkg", AGENTS_DIR)
_ensure_pkg("_agents_pkg.router", AGENTS_DIR / "router")
_ensure_pkg("_agents_pkg.validators", AGENTS_DIR / "validators")

# Order matters: load `types` before modules that import from it.
router_types = _load_module(
    "_agents_pkg.router.types", AGENTS_DIR / "router" / "types.py"
)
task_classifier = _load_module(
    "_agents_pkg.router.task_classifier", AGENTS_DIR / "router" / "task_classifier.py"
)
model_policy_engine = _load_module(
    "_agents_pkg.router.model_policy_engine",
    AGENTS_DIR / "router" / "model_policy_engine.py",
)
model_router = _load_module(
    "_agents_pkg.router.model_router", AGENTS_DIR / "router" / "model_router.py"
)
bayyinah_gate = _load_module(
    "_agents_pkg.validators.bayyinah_validation_gate",
    AGENTS_DIR / "validators" / "bayyinah_validation_gate.py",
)
