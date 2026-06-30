"""
Step: Surface-based analysis via mri_vol2surf, mri_concat, mris_fwhm.

Reference:
https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis

Projects PET data onto the fsaverage surface for each patient and hemisphere,
concatenates all subjects into a single volume, then smooths on the surface.
"""

import argparse
import logging
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import PipelineConfig, add_common_args, build_config
from steps.gtmpvc import GTMPVC_OUTPUT_FILES


def run_surface_analysis(config: PipelineConfig, logger: logging.Logger | None = None) -> None:
    if logger is None:
        logger = logging.getLogger(__name__)

    # Collect per-hemisphere output paths across all subjects
    all_fsaverage: dict[str, list[str]] = {'lh': [], 'rh': []}

    # Run mri_vol2surf for each patient and hemisphere
    for patient_id, timestamp in config.patients:
        label = f'patient {patient_id} / {timestamp}'
        subject_dir = config.subject_path(patient_id, timestamp)

        gtmpvc_dir = os.path.join(subject_dir, 'mri/gtmpvc.no.tfe.cerebellum.cortex.output')
        pet_path = os.path.join(gtmpvc_dir, 'input.rescaled.nii.gz')
        reg_path = os.path.join(gtmpvc_dir, 'aux/bbpet2anat.lta')

        # Verify gtmpvc outputs are present before projecting to surface.
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
            continue

        patient_done = True
        for hemi in ('lh', 'rh'):
            output_path = os.path.join(subject_dir, 'mri', f'{hemi}.pet.fsaverage.sm00.nii.gz')

            if os.path.exists(output_path):
                logger.info('[SKIPPED] vol2surf %s — %s — output already present', hemi, label)
                all_fsaverage[hemi].append(output_path)
                continue

            patient_done = False
            logger.info('[RUNNING] vol2surf %s — %s', hemi, label)
            subprocess.run([
                'mri_vol2surf',
                '--mov',        pet_path,
                '--reg',        reg_path,
                '--hemi',       hemi,
                '--projfrac',   str(config.projfrac),
                '--o',          output_path,
                '--cortex',
                '--trgsubject', 'fsaverage'
            ], check=True)

            all_fsaverage[hemi].append(output_path)

    # Concatenate, smooth and perform glmfit across all subjects for each hemisphere
    for hemi in ('lh', 'rh'):
        if not all_fsaverage[hemi]:
            logger.warning('[SKIPPED] concat+smooth %s — no subjects with vol2surf output', hemi)
            continue

        concat_path = os.path.join(config.data_dir, f'all.{hemi}.pet.fsaverage.sm00.nii.gz')
        subprocess.run(
            ['mri_concat'] + all_fsaverage[hemi] + ['--o', concat_path, '--prune'],
            check=True
        )

        smoothed_path = os.path.join(
            config.data_dir,
            f'all.{hemi}.pet.fsaverage.sm{config.fwhm:02d}.nii.gz'
        )
        subprocess.run([
            'mris_fwhm',
            '--smooth-only',
            '--i',      concat_path,
            '--fwhm',   str(config.fwhm),
            '--o',      smoothed_path,
            '--cortex',
            '--s',      'fsaverage',
            '--hemi',   hemi
        ], check=True)


        # Comment glmfit out for now while to first generate all the preparation files

        # subprocess.run([
        #     'mri_glmfit',
        #     '--y',      smoothed_path,
        #     '--fsgd',   config.fsgd_path,
        #     '--C',      config.contrast_matrix_path,
        #     '--surf',   'fsaverage', hemi,
        #     '--cortex',
        #     '--o',      os.path.join(config.subjects_dir, f'all.{hemi}.pet.fsaverage.sm{config.fwhm:02d}.glmfit')
        # ], check=True)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s  %(levelname)-8s  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    parser = argparse.ArgumentParser(
        description='Run surface-based analysis (mri_vol2surf + concat + smooth + glmfit) for all included patients.'
    )
    add_common_args(parser)
    args = parser.parse_args()
    run_surface_analysis(build_config(args))
