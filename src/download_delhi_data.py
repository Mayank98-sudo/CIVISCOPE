"""Compatibility entry point for bounded official-source collection."""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.collect_historical import collect_snapshot, main

if __name__ == "__main__":
    main()
