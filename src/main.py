"""
PETSurfer automated pipeline — main entry point.

Runs all pipeline steps in sequence for all included patients.
Usage:
    python src/main.py --excel-path data/matched_results.xlsx [options]

Run with --help for the full list of options.
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import add_common_args, build_config
from steps.gtmpvc import run_gtmpvc
from steps.surface_analysis import run_surface_analysis

LOG_FILE = 'src/pipeline.log'


def setup_logger() -> logging.Logger:
    logger = logging.getLogger('petsurfer')
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter('%(asctime)s  %(levelname)-8s  %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

    fh = logging.FileHandler(LOG_FILE, mode='a')
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='PETSurfer automated pipeline.'
    )
    add_common_args(parser)
    args = parser.parse_args()

    config = build_config(args)
    logger = setup_logger()

    logger.info('Pipeline started. Log file: %s', os.path.abspath(LOG_FILE))

    # Pipeline steps in order
    run_gtmpvc(config, logger=logger)
    run_surface_analysis(config, logger=logger)
    # Future steps: run_coreg(config), run_glmfit(config), ...

    logger.info('Pipeline finished.')
