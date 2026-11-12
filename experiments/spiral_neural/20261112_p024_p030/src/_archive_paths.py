"""Portable filesystem bindings only; no learning/data-generation changes."""
import sys
sys.dont_write_bytecode=True
import os
from pathlib import Path

SRC_DIR=Path(__file__).resolve().parent
ARCHIVE_ROOT=SRC_DIR.parent
REPO_ROOT=next(p for p in ARCHIVE_ROOT.parents if (p/'experiments/spiral_parser').is_dir() and (p/'docs').is_dir())
RUNS_ROOT=Path(os.environ.get('SLE_RESEARCH_WORK',str(Path.cwd()/'work/sle-neural-reproduction-20261112'))).resolve()
PLOTS_ROOT=RUNS_ROOT/'plots'
