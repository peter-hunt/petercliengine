"""Shared pytest configuration — adds workspace root to sys.path."""
import sys
from pathlib import Path

# Ensure root package imports work from the tests/ subdirectory
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
