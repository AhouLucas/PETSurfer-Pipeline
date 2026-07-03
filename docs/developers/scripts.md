# Auxiliary scripts

These live in `scripts/` and are **not part of the pipeline**; they are small
one-off or validation utilities.

| Script | Purpose |
|--------|---------|
| `compare_nifti.py` | Threshold-based comparison of two `.nii.gz` volumes (shape, affine, correlation, relative diff) — used to validate reproductions across machines/runs. |
| `flag_warned_patients.py` | Reads a pipeline log and sets the include flag to 0 in the Excel file for any patient that produced a WARNING, so they can be excluded from analysis. |
| `match_tests_to_pet.py` | Data-prep: matches each patient's cognitive/tau test results to the closest PET-scan date and emits a pipeline-format spreadsheet. Configured via module-level constants. |
| `scan_pet_dirs.py` | Scans the raw PET directory tree for valid subjects (matching the naming pattern with a present `PET.nii`) and writes a spreadsheet of IDs/timestamps. |

## References

- [PETSurfer wiki](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer)
- [FreeSurfer wiki](https://surfer.nmr.mgh.harvard.edu/fswiki/FreeSurferWiki)
- [`recon-all`](https://surfer.nmr.mgh.harvard.edu/fswiki/recon-all)
- [`mri_coreg`](https://surfer.nmr.mgh.harvard.edu/fswiki/mri_coreg)
- [FSGD format](https://surfer.nmr.mgh.harvard.edu/fswiki/FsgdFormat)
- [DODS vs DOSS](https://surfer.nmr.mgh.harvard.edu/fswiki/DodsDoss)
