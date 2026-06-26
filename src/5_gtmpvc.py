"""
https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#ROI_Analysis.2C_Setting_Up_Reference_Regions_for_KM.2C_and_Apply_Partial_Volume_Correction_.28if_using.29
"""

# MAIN CMD:
# `mri_gtmpvc --i coreg_tau_PET.nii --reg template.reg.tau.lta --seg gtmseg.mgz 
# --default-seg-merge --auto-mask 1 .01 --no-tfe --rescale 8 47 
# --save-input --o gtmpvc.no.tfe.cerebellum.cortex.output`

import subprocess
import os

from constants import params, ALL_SUBJECTS_PATHS, ALL_DATA_PATHS

if __name__ == '__main__':
    for patient_id in params['IDs']:
        subject_dir = ALL_SUBJECTS_PATHS[patient_id]
        data_dir = ALL_DATA_PATHS[patient_id]

        pet_path = os.path.join(data_dir, 'PET.nii')
        registration_file_path = os.path.join(subject_dir, 'mri/template.reg.tau.lta')
        gtmseg_path = os.path.join(subject_dir, 'mri/gtmseg.mgz')

        output_path = os.path.join(subject_dir, 'mri/gtmpvc.no.tfe.cerebellum.cortex.output')

        subprocess.run([
            'mri_gtmpvc',
            '--i',          pet_path,
            '--reg',        registration_file_path,
            '--seg',        gtmseg_path,
            '--default-seg-merge',
            '--auto-mask',  '1', '.01',
            '--no-tfe',
            '--rescale',    '8', '47',
            '--save-input',
            '--o',          output_path
        ], check=True)