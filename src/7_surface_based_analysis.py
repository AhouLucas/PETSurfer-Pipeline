"""
https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis
"""

import subprocess
import os

from constants import params, ALL_SUBJECTS_PATHS, ALL_DATA_PATHS

if __name__ == '__main__':
    # Dict containging two lists of all the fsaverage paths for each hemisphere for all subjects
    all_fsaverage_dict = {
        'lh': [],
        'rh': []
    }

    # Iterate over each subject/data pair and execute `mri_vol2surf` for each hemisphere
    for patient_id in params['IDs']:
        subject_dir = ALL_SUBJECTS_PATHS[patient_id]
        data_dir = ALL_DATA_PATHS[patient_id]

        pet_path = os.path.join(data_dir, 'PET.nii')
        template_tau_path = os.path.join(subject_dir, 'mri/template.reg.tau.lta')

        for hemi in ['lh', 'rh']:
            output_path = os.path.join(subject_dir, 'mri', f'{hemi}.pet.fsaverage.sm00.nii.gz')

            # Execute mri_vol2surf for each hemisphere
            subprocess.run([
                'mri_vol2surf',
                '--mov',        pet_path,
                '--reg',        template_tau_path,
                '--hemi',       hemi,
                '--projfrac',   str(params['PROJFRAC']),
                '--o',          output_path,
                '--cortex',
                '--trgsubject', 'fsaverage'
            ], check=True)

            # Add fsaverage path to corresponding list
            all_fsaverage_dict[hemi].append(output_path)

    for hemi in ['lh', 'rh']:
        # Concatenate every patient fsaverage
        all_fsaverage_path = os.path.join(params['DATA_DIR'], f'all.{hemi}.pet.fsaverage.sm00.nii.gz')
        subprocess.run(['mri_concat'] + all_fsaverage_dict[hemi] + ['--o', all_fsaverage_path, '--prune'], check=True)

        # Smooth on the surface
        all_fsaverage_smoothed_path = os.path.join(params['DATA_DIR'], f'all.{hemi}.pet.fsaverage.sm{"%02d" % params["FWHM"]}.nii.gz')

        subprocess.run([
            'mris_fwhm',
            '--smooth-only',
            '--i',              all_fsaverage_path,
            '--fwhm',           str(params['FWHM']),
            '--o',              all_fsaverage_smoothed_path,
            '--cortex',
            '--s',              'fsaverage',
            '--hemi',           hemi
        ], check=True)


        # TODO: Group analysis (mri_glmfit)