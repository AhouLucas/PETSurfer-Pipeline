"""
Step: Partial Volume Correction via mri_gtmpvc.

Reference:
https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#ROI_Analysis.2C_Setting_Up_Reference_Regions_for_KM.2C_and_Apply_Partial_Volume_Correction_.28if_using.29

Runs mri_gtmpvc for each patient. Inputs come from the patient's PET data
directory and FreeSurfer subject directory; output is written under mri/ in
the subject directory.
"""

import argparse
import logging
import os
import sys

# Allow running as a script from the src/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.config import (
    GTMPVC_OUTPUT_DIRNAME,
    GTMPVC_OUTPUT_FILES,
    PipelineConfig,
    add_common_args,
    build_config,
)
from utils.utils import run_command


def run_gtmpvc_patient(
    config: PipelineConfig,
    patient_id: int,
    timestamp: str,
    logger: logging.Logger,
) -> bool:
    """Run gtmpvc for a single patient. Returns True on success, False on any failure."""
    label = f'patient {patient_id} / {timestamp}'
    subject_dir = config.subject_path(patient_id, timestamp)
    data_dir = config.data_path(patient_id, timestamp)

    output_dir = os.path.join(subject_dir, GTMPVC_OUTPUT_DIRNAME)

    output_files = [os.path.join(output_dir, f) for f in GTMPVC_OUTPUT_FILES]
    if not config.force and all(os.path.exists(p) for p in output_files):
        logger.info('[SKIPPED] gtmpvc — %s — output already present at %s', label, output_dir)
        return True

    pet_path = os.path.join(data_dir, 'PET.nii')
    reg_path = os.path.join(subject_dir, 'mri/template.reg.tau.lta')
    gtmseg_path = os.path.join(subject_dir, 'mri/gtmseg.mgz')

    missing = [p for p in (pet_path, reg_path, gtmseg_path) if not os.path.exists(p)]
    if missing:
        logger.warning(
            '[FAILED] gtmpvc — %s — missing input file(s): %s',
            label, ', '.join(missing)
        )
        return False

    logger.info('[RUNNING] gtmpvc — %s', label)
    returncode = run_command([
        'mri_gtmpvc',
        '--i',             pet_path,
        '--reg',           reg_path,
        '--seg',           gtmseg_path,
        '--default-seg-merge',
        '--auto-mask',     '1', '.01',
        '--no-tfe',
        '--rescale',       '8', '47',
        '--save-input',
        '--o',             output_dir
    ], f'mri_gtmpvc {label}', logger)
    if returncode != 0:
        logger.warning(
            '[FAILED] gtmpvc — %s — exit code %d. See the log file for details.',
            label, returncode,
        )
        return False

    return True


def run_gtmpvc(config: PipelineConfig, logger: logging.Logger | None = None) -> None:
    if logger is None:
        logger = logging.getLogger(__name__)

    for patient_id, timestamp in config.patients:
        run_gtmpvc_patient(config, patient_id, timestamp, logger)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s  %(levelname)-8s  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    parser = argparse.ArgumentParser(
        description='Run mri_gtmpvc (partial volume correction) for all included patients.'
    )
    add_common_args(parser)
    args = parser.parse_args()
    run_gtmpvc(build_config(args))
