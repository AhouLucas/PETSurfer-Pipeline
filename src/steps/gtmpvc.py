"""
Step: Partial Volume Correction via mri_gtmpvc.

Reference:
https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#ROI_Analysis.2C_Setting_Up_Reference_Regions_for_KM.2C_and_Apply_Partial_Volume_Correction_.28if_using.29

Runs mri_gtmpvc for each patient. Inputs come from the patient's PET data
directory and FreeSurfer subject directory; output is written under mri/ in
the subject directory.
"""

import argparse
import os
import subprocess
import sys

# Allow running as a script from the src/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import PipelineConfig, add_common_args, build_config


def run_gtmpvc(config: PipelineConfig) -> None:
    for patient_id in config.ids:
        subject_dir = config.subject_path(patient_id)
        data_dir = config.data_path(patient_id)

        pet_path = os.path.join(data_dir, 'PET.nii')
        registration_file_path = os.path.join(subject_dir, 'mri/template.reg.tau.lta')
        gtmseg_path = os.path.join(subject_dir, 'mri/gtmseg.mgz')
        output_path = os.path.join(subject_dir, 'mri/gtmpvc.no.tfe.cerebellum.cortex.output')

        subprocess.run([
            'mri_gtmpvc',
            '--i',             pet_path,
            '--reg',           registration_file_path,
            '--seg',           gtmseg_path,
            '--default-seg-merge',
            '--auto-mask',     '1', '.01',
            '--no-tfe',
            '--rescale',       '8', '47',
            '--mgx',           '.01',   # required to produce input.rescaled.nii.gz and mgx.ctxgm.nii.gz
            '--save-input',
            '--o',             output_path
        ], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run mri_gtmpvc (partial volume correction) for all included patients.'
    )
    add_common_args(parser)
    args = parser.parse_args()
    run_gtmpvc(build_config(args))
