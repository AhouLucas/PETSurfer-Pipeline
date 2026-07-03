"""
Step: Project PET data onto the fsaverage surface via mri_vol2surf.

Reference:
https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis

Projects PET data onto the fsaverage surface for each patient and hemisphere.
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.config import (
    GTMPVC_OUTPUT_DIRNAME,
    GTMPVC_OUTPUT_FILES,
    HEMISPHERES,
    VOL2SURF_FILENAME,
    PipelineConfig,
    add_common_args,
    build_config,
)
from utils.utils import run_command


def run_vol2surf_patient(
    config: PipelineConfig,
    patient_id: int,
    timestamp: str,
    logger: logging.Logger,
) -> bool:
    """Run mri_vol2surf for a single patient. Returns True if all hemispheres succeeded."""
    label = f'patient {patient_id} / {timestamp}'
    subject_dir = config.subject_path(patient_id, timestamp)

    gtmpvc_dir = os.path.join(subject_dir, GTMPVC_OUTPUT_DIRNAME)
    pet_path = os.path.join(gtmpvc_dir, 'input.rescaled.nii.gz')
    reg_path = os.path.join(gtmpvc_dir, 'aux/bbpet2anat.lta')

    missing_inputs = [
        os.path.join(gtmpvc_dir, f)
        for f in GTMPVC_OUTPUT_FILES
        if not os.path.exists(os.path.join(gtmpvc_dir, f))
    ]
    if missing_inputs:
        logger.warning(
            '[FAILED] vol2surf — %s — missing gtmpvc output(s): %s',
            label, ', '.join(missing_inputs)
        )
        return False

    success = True
    for hemi in HEMISPHERES:
        output_path = os.path.join(subject_dir, 'mri', VOL2SURF_FILENAME.format(hemi=hemi))

        if not config.force and os.path.exists(output_path):
            logger.info('[SKIPPED] vol2surf %s — %s — output already present', hemi, label)
            continue

        logger.info('[RUNNING] vol2surf %s — %s', hemi, label)
        returncode = run_command([
            'mri_vol2surf',
            '--mov',        pet_path,
            '--reg',        reg_path,
            '--hemi',       hemi,
            '--projfrac',   str(config.projfrac),
            '--o',          output_path,
            '--cortex',
            '--trgsubject', 'fsaverage'
        ], f'mri_vol2surf {hemi} {label}', logger)
        if returncode != 0:
            logger.warning(
                '[FAILED] vol2surf %s — %s — exit code %d. See the log file for details.',
                hemi, label, returncode,
            )
            success = False

    return success


def run_vol2surf(config: PipelineConfig, logger: logging.Logger | None = None) -> None:
    if logger is None:
        logger = logging.getLogger(__name__)

    for patient_id, timestamp in config.patients:
        run_vol2surf_patient(config, patient_id, timestamp, logger)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s  %(levelname)-8s  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    parser = argparse.ArgumentParser(
        description='Run mri_vol2surf for all included patients.'
    )
    add_common_args(parser)
    args = parser.parse_args()
    run_vol2surf(build_config(args))
