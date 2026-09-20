"""Root conftest — put THIS checkout's src/ first, before any test imports.

Several test files import ``ruwritingstyles`` without inserting ``src/``
themselves; on a machine with an editable install (``__editable__.*.pth``)
pointing at ANOTHER checkout, the first such import caches that foreign copy
in ``sys.modules`` and every later test — including ones that do insert
``src/`` — reuses it. Observed 20-09-2026: a full-suite run executed the
stale main-tree ``harvest`` (no ``selection`` parameter) while the isolated
run used this worktree's, so the new selection-gate tests failed only in
full-suite order. Inserting here, before the first test module loads, makes
the resolution deterministic for the whole session.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
