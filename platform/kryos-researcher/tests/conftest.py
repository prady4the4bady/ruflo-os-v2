from __future__ import annotations

import sys
from pathlib import Path

# Make the service module importable by its flat name when running from
# the repo root or from the platform/kryos-researcher directory.
_SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVICE_DIR))
