"""
PETSurfer preprocessing pipeline — main entry point.

Runs gtmpvc then vol2surf for each patient in sequence.
Usage:
    python src/run_preprocessing.py --excel-path data/matched_results.xlsx [options]

Run with --help for the full list of options.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from utils.config import add_common_args, build_config
from utils.utils import setup_logger
from steps.gtmpvc import run_gtmpvc_patient
from steps.vol2surf import run_vol2surf_patient

LOG_FILE = 'src/pipeline_rerun.log'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='PETSurfer preprocessing pipeline.'
    )
    add_common_args(parser)
    args = parser.parse_args()

    logger = setup_logger('petsurfer', LOG_FILE, file_mode='a')
    logger.info('Preprocessing started. Log file: %s', os.path.abspath(LOG_FILE))

    try:
        config = build_config(args)
    except ValueError as e:
        logger.error('%s', e)
        sys.exit(1)

    try:
        for patient_id, timestamp in config.patients:
            ok = run_gtmpvc_patient(config, patient_id, timestamp, logger)
            if ok:
                run_vol2surf_patient(config, patient_id, timestamp, logger)
            else:
                logger.warning(
                    '[SKIPPED] vol2surf — patient %s / %s — gtmpvc did not succeed',
                    patient_id, timestamp
                )
    except Exception as e:
        logger.debug('Unexpected error:', exc_info=True)
        logger.error(
            'An unexpected error occurred. See the log file for details: %s',
            os.path.abspath(LOG_FILE),
        )
        sys.exit(1)

    logger.info('Preprocessing finished.')
