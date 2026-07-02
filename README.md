# PETSurfer Pipeline

This repository contains the code to run some pre-processing steps, run the analysis and visualize the results
using [PETSurfer](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer).

In this document, you will find explanations about the structure of this project, the role of the different files/directories, how to use the commands, and what inputs and prerequisites you will need to use those.

## Prerequisites


### Preparing Python's environment
You will need Python3 installed on your system and an environment with the following packages:

```
numpy
openpyxl
pandas
nibabel
```

To create an environment, first make sure Python3 is installed, then run:

`python -m venv .env`

This creates an environment named `.env` in your current directory. Then, activate it:

`source .env/bin/activate`

Now, you can install the aforementioned packages by running:

`pip install numpy openpyxl pandas nibabel` 

or use the `requirements.txt` file to make sure you install the correct versions of those packages:

`pip install -r requirements.txt`


### Preparing patients' data

Recon-all ([`recon-all`](https://surfer.nmr.mgh.harvard.edu/fswiki/recon-all)) and coregistration ([`mri_coreg`](https://surfer.nmr.mgh.harvard.edu/fswiki/mri_coreg)) steps are assumed to be done before using the scripts in this project. For each patient, you need to have at least:

1. `DATA_DIR/SUBJECT/PET.nii` : Original PET scan for patient, which resides in the data directory

2. `SUBJECTS_DIR/SUBJECT/mri/template.reg.tau.lta`: Registration file that was generated during the coregistration step on the `PET.nii` scan. This should reside in the PETSurfer's subject's directory

3. `SUBJECTS_DIR/SUBJECT/mri/gtmseg.mgz`: Segmentation file. This should have been generated with the `gtmseg --s SUBJECT` command.


Also, make sure the `fsaverage` patient exists in your PETSurfer's patients' directory.

## Project's structure

Here is a description of the different files and directories in this project and their role:

```bash
.
├── README.md   # This document
├── requirements.txt    # Python requirements
├── scripts/            # Miscellaneous scripts
│   ├── flag_warned_patients.py
│   ├── match_tests_to_pet.py
│   └── scan_pet_dirs.py
└── src/                # Main python script
    ├── run_analysis.py
    ├── run_preprocessing.py
    ├── visualize_glmfit.py
    ├── steps/          # PETSurfer steps for preprocessing
    │   ├── gtmpvc.py
    │   └── vol2surf.py
    └── utils/          # Utils scripts
        ├── compare_nifti.py
        ├── config.py
        ├── excel_to_fsgd.py
        └── utils.py
```

Among those files, you will be mainly interested in the one in the `src/` directory. Especially, you will be interested in:

### `src/run_preprocessing.py`

This script runs the Partial Volume Correction (PVC - using `mri_gtmpvc` from PETSurfer) as well as the Volume-to-Surface projection (`mri_vol2surf`) steps on all patients in the list (more on that later...).

This will create:

1. A directory named `gtmpvc.no.tfe.cerebellum.cortex.output` in the subject's mri subdirectory, which is generated during the PVC step. This directory will contain the a rescaled version of the PET scan and calibrated with respect to the cerebellum (named `input.rescaled.nii.gz`). It also contains a subdirectory `aux/` with a registration file named `bbpet2anat.lta` which should be used for the Volume-to-Surface projection on the rescaled PET scan according to the [PETSurfer Wiki](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#ROI_Analysis.2C_Setting_Up_Reference_Regions_for_KM.2C_and_Apply_Partial_Volume_Correction_.28if_using.29).

2. During the Volume-to-Surface step, a file named `{hemi}.pet.fsaverage.sm00.nii.gz` for each hemisphere (i.e. "lh" and "rh") will be generated. Those files will then be used for the surface-based analysis later.

Don't worry if you launch this script and those folders/files were already present, it first checks for them and skips these steps if they are already present. A log file is also generated to get a history of the processing. You can check for patients for which the pipeline failed to troubleshoot or to know which one to ignore in your analysis.

### `src/run_analysis.py`

This script performs the [surface-based analysis](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis) using a GLM fit (`mri_glmfit`). This should be run only after the aforementioned files/directories were generated.

See the following sections for more details on the usage.

### `src/visualize_glmfit.py`

Once the analysis was run, this script allows you to visualize the results using `freeview`.

Again, more on the usage in the next sections.


