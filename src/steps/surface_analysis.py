"""
Step: Surface-based analysis via mri_vol2surf, mri_concat, mris_fwhm.

Reference:
https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis

Projects PET data onto the fsaverage surface for each patient and hemisphere,
concatenates all subjects into a single volume, then smooths on the surface.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import PipelineConfig, add_common_args, build_config


def run_surface_analysis(config: PipelineConfig) -> None:
    # Collect per-hemisphere output paths across all subjects
    all_fsaverage: dict[str, list[str]] = {'lh': [], 'rh': []}

    # Run mri_vol2surf for each patient and hemisphere
    for patient_id in config.ids:
        subject_dir = config.subject_path(patient_id)
        data_dir = config.data_path(patient_id)

        # Use the rescaled image generated from mri_gtmpvc as input for mri_vol2surf
        pet_path = os.path.join(subject_dir, 'mri/gtmpvc.no.tfe.cerebellum.cortex.output/input.rescaled.nii.gz')
        reg_path = os.path.join(subject_dir, 'mri/gtmpvc.no.tfe.cerebellum.cortex.output/aux/bbpet2anat.lta')

        for hemi in ('lh', 'rh'):
            output_path = os.path.join(subject_dir, 'mri', f'{hemi}.pet.fsaverage.sm00.nii.gz')

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

        subprocess.run([
            'mri_glmfit',
            '--y',      smoothed_path,
            '--fsgd',   config.fsgd_path,
            '--C',      config.contrast_matrix_path,
            '--surf',   'fsaverage', hemi,
            '--cortex',
            '--o',      os.path.join(config.data_dir, f'all.{hemi}.pet.fsaverage.sm{config.fwhm:02d}.glmfit')
        ], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run surface-based analysis (mri_vol2surf + concat + smooth + glmfit) for all included patients.'
    )
    add_common_args(parser)
    args = parser.parse_args()
    run_surface_analysis(build_config(args))
