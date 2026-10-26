"""Shared bootstrap for CLI scripts: make ``backend`` importable as ``app``.

Every script imports this first so ``from app...`` resolves regardless of the
current working directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND = PROJECT_ROOT / "backend"

for p in (PROJECT_ROOT, BACKEND):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
