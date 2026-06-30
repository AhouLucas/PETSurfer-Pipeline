"""
PETSurfer preprocessing pipeline — main entry point.

Runs gtmpvc then vol2surf for each patient in sequence.
Usage:
    python src/run_preprocessing.py --excel-path data/matched_results.xlsx [options]

Run with --help for the full list of options.
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import add_common_args, build_config
from steps.gtmpvc import _run_gtmpvc_patient
from steps.vol2surf import _run_vol2surf_patient

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
        description='PETSurfer preprocessing pipeline.'
    )
    add_common_args(parser)
    args = parser.parse_args()

    config = build_config(args)
    logger = setup_logger()

    logger.info('Preprocessing started. Log file: %s', os.path.abspath(LOG_FILE))

    for patient_id, timestamp in config.patients:
        ok = _run_gtmpvc_patient(config, patient_id, timestamp, logger)
        if ok:
            _run_vol2surf_patient(config, patient_id, timestamp, logger)
        else:
            logger.warning(
                '[SKIPPED] vol2surf — patient %s / %s — gtmpvc did not succeed',
                patient_id, timestamp
            )

    logger.info('Preprocessing finished.')
