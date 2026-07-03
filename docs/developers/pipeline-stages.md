# Pipeline stages

The pipeline automates the PETSurfer processing steps in order. Steps 1–2 run per
patient (preprocessing); step 3 runs once per group (analysis); step 4 is optional.

## 1. Partial Volume Correction — `mri_gtmpvc`

Corrects PET signal for partial-volume effects and rescales/calibrates it against
the cerebellum. Implemented in `src/steps/gtmpvc.py`
([reference](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#ROI_Analysis.2C_Setting_Up_Reference_Regions_for_KM.2C_and_Apply_Partial_Volume_Correction_.28if_using.29)).

!!! warning "The `mri_gtmpvc` flag set is load-bearing"
    The pipeline invokes `mri_gtmpvc` with:

    ```
    --default-seg-merge --auto-mask 1 .01 --no-tfe --rescale 8 47 --save-input
    ```

    `input.rescaled.nii.gz` (consumed by the surface projection) is produced by
    combining `--rescale 8 47` (cerebellum calibration) with `--save-input`.
    Changing this flag set changes the downstream inputs — keep it in sync with
    `GTMPVC_OUTPUT_FILES` in `src/utils/config.py`.

Outputs land in `gtmpvc.no.tfe.cerebellum.cortex.output/`, including
`input.rescaled.nii.gz` (bbpet space) and `aux/bbpet2anat.lta`.

## 2. Surface projection — `mri_vol2surf`

Projects the corrected PET volume onto the `fsaverage` cortical surface, per
hemisphere, producing `{hemi}.pet.fsaverage.sm00.nii.gz`. Implemented in
`src/steps/vol2surf.py`
([reference](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis)).

!!! danger "Registration (`.lta`) rules"
    - An `.lta` is only valid for the exact volume geometries it was computed
      from. Any rescaling or resampling after registration invalidates the
      transform.
    - `bbpet2anat.lta` (bbpet space) and `template.reg.tau.lta` (original PET
      space) must **never** be swapped.
    - Any volume from the `gtmpvc/` output directory (bbpet space) must use
      `aux/bbpet2anat.lta`, **not** `template.reg.tau.lta`.

## 3. Group-level analysis

`src/run_analysis.py` concatenates all subjects' surface maps (`mri_concat`),
smooths them (`mris_fwhm`), and fits a GLM (`mri_glmfit`) using an FSGD design and
one or more contrast matrices. The FSGD can be provided or auto-generated from the
Excel file by `src/utils/excel_to_fsgd.py`.

References:
[PETSurfer Wiki](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis),
[GLM Tutorial](https://www.nmr.mgh.harvard.edu/~jbm/jip/jip-glm/glm-tutorial.html).
See [FSGD & GLM](fsgd-and-glm.md) for design and contrast details.

## 4. Visualization

`src/visualize_glmfit.py` opens the resulting significance maps (`sig.mgh`) in
`freeview` on the inflated `fsaverage` surface.

## Validation & reproducibility

!!! note "Use threshold-based validation"
    Floating-point non-determinism across machines and runs is expected in
    FreeSurfer tools. Validation should be threshold-based (e.g. correlation
    > 0.99, max relative difference < ~5%), **not bitwise**.
    `scripts/compare_nifti.py` implements this kind of comparison.

The preprocessing steps check for their outputs and skip work that is already
done, so re-running only fills in what's missing (use `--force` to recompute).
