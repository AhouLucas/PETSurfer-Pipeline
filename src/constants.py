"""
File containing the parameters for the PET analysis pipeline.
"""


# Parameter dict
import os

from utils.utils import (
        read_all_ids_from_excel, 
        read_timestamps_from_excel
    )


params = {
    'SUBJECTS_DIR': './data',               # Directory containing folders of each patient to process
    'DATA_DIR': './dataPET',                # Directory containing the PET images
    'EXCEL_PATH': 'data/matched_results.xlsx',              # Path to the Excel file containing patient information
    'FSGD_PATH': 'Test.fsgd',               # Path to the FreeSurfer Group Descriptor (FSGD) file for group analysis
    # 'IDs': [1, 2, 3, 4, 5, 101],            # List of patient IDs to process
    # 'TIMESTAMPS': {                         # Timestamp of the PET image for each patient ID
    #     1: 0,
    #     2: 0,
    #     3: 0,
    #     4: 0,
    #     5: 0,
    #     101: 0,
    # },
    'PROJFRAC': 0.5,                        # Sampling parameter for `mpi_vol2surf`
    'FWHM': 5,                              # Smoothness parameter
    'SUBJECTS_TEMPLATE': "YASMINE_TAU_%d_%s",  # Template for subject directory names
    'DATA_TEMPLATE': "TAU_%d_%s",      # Template for data directory names
}


# params['IDs'] = read_all_ids_from_excel(params['EXCEL_PATH'], 'PatientID')
# params['TIMESTAMPS'] = read_timestamps_from_excel(params['EXCEL_PATH'], 'PatientID', 'Timestamp')

# missing_timestamp_ids = [patient_id for patient_id in params['IDs'] if patient_id not in params['TIMESTAMPS']]
# if missing_timestamp_ids:
#     raise ValueError(f"Missing timestamp(s) for patient ID(s): {missing_timestamp_ids}")

# ALL_SUBJECTS_PATHS = {
#     patient_id: os.path.join(
#         params['SUBJECTS_DIR'],
#         params['SUBJECTS_TEMPLATE'] % (patient_id, params['TIMESTAMPS'][patient_id])
#     )
#     for patient_id in params['IDs']
# }

# ALL_DATA_PATHS = {
#     patient_id: os.path.join(
#         params['DATA_DIR'],
#         params['DATA_TEMPLATE'] % (patient_id, params['TIMESTAMPS'][patient_id])
#     )
#     for patient_id in params['IDs']
# }