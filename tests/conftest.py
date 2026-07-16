"""Shared pytest configuration.

The repository is organized as runnable scripts (etl/, models/) alongside an
installable-style package (api/). These path entries let the tests import the
real production functions rather than copies of them:

    api/     -> imported as a package (api.services.action_engine)
    etl/     -> scripts import each other by bare name (from common import ...)
    models/  -> same convention (from train_model import ...)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, REPO_ROOT / "etl", REPO_ROOT / "models"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
