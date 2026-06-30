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
import subprocess
import sys

# Allow running as a script from the src/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import PipelineConfig, add_common_args, build_config

# Files that must exist inside the gtmpvc output directory before the step is
# considered complete (used both for "already done" detection and as the
# required inputs for the surface_analysis step).
GTMPVC_OUTPUT_FILES = [
    'input.rescaled.nii.gz',
    'aux/bbpet2anat.lta',
]


def run_gtmpvc(config: PipelineConfig, logger: logging.Logger | None = None) -> None:
    if logger is None:
        logger = logging.getLogger(__name__)

    for patient_id, timestamp in config.patients:
        label = f'patient {patient_id} / {timestamp}'
        subject_dir = config.subject_path(patient_id, timestamp)
        data_dir = config.data_path(patient_id, timestamp)

        output_dir = os.path.join(subject_dir, 'mri/gtmpvc.no.tfe.cerebellum.cortex.output')

        # Skip if output is already complete.
        output_files = [os.path.join(output_dir, f) for f in GTMPVC_OUTPUT_FILES]
        if all(os.path.exists(p) for p in output_files):
            logger.info('[SKIPPED] gtmpvc — %s — output already present at %s', label, output_dir)
            continue

        # Verify required inputs before launching the command.
        pet_path = os.path.join(data_dir, 'PET.nii')
        reg_path = os.path.join(subject_dir, 'mri/template.reg.tau.lta')
        gtmseg_path = os.path.join(subject_dir, 'mri/gtmseg.mgz')

        missing = [p for p in (pet_path, reg_path, gtmseg_path) if not os.path.exists(p)]
        if missing:
            logger.warning(
                '[FAILED] gtmpvc — %s — missing input file(s): %s',
                label, ', '.join(missing)
            )
            continue

        logger.info('[RUNNING] gtmpvc — %s', label)
        subprocess.run([
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
        ], check=True)


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
