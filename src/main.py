"""
PETSurfer automated pipeline — main entry point.

Runs all pipeline steps in sequence for all included patients.
Usage:
    python src/main.py --excel-path data/matched_results.xlsx [options]

Run with --help for the full list of options.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import add_common_args, build_config
from steps.gtmpvc import run_gtmpvc
from steps.surface_analysis import run_surface_analysis


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='PETSurfer automated pipeline.'
    )
    add_common_args(parser)
    args = parser.parse_args()

    config = build_config(args)

    # Pipeline steps in order
    run_gtmpvc(config)
    run_surface_analysis(config)
    # Future steps: run_coreg(config), run_glmfit(config), ...
