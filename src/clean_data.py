"""Compatibility entry point for shared observation cleaning and run publication.

Original implementation is retained in the pre-upgrade source archive.
"""
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.run_pipeline import main

if __name__ == '__main__':
    main()
