"""Compatibility entry point for the consolidated CIVISCOPE pipeline.

Original implementation is retained in data/archive/pre_upgrade_source_20260929.zip.
"""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.pipeline.run_pipeline import main

if __name__ == "__main__":
    main()
