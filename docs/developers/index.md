# For Developers — Overview

This section is for people working on the **code**. It explains the pipeline's
goal, its stages, the role of each file, and the exact input/output formats. It is
a restructured version of the repository `README.md`.

The pipeline is built around
[PETSurfer](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer) and targets **tau
PET neuroimaging research on Alzheimer's disease biomarkers** (Braak staging across
diagnostic groups) at IoNS. A guided TUI (`run_interactive.py`) wraps the
underlying command-line scripts, which remain available for scripting and
automation.

## The pipeline at a glance

The pipeline **assumes `recon-all` and coregistration (`mri_coreg`) are already
done** for each patient. It picks up from partial-volume correction onward:

```
  Excel patient list ─┐
                      ▼
  PET.nii + MRI  ──► [1] gtmpvc  ──►  [2] vol2surf  ──►  {lh,rh}.pet.fsaverage.sm00.nii.gz
  (per patient)        (PVC)         (surface proj)              │
                                                                 ▼
  Excel ──► FSGD  ─────────────────────────────►  [3] concat ─► smooth ─► GLM  ──►  sig.mgh
  + .mtx contrasts                                    (group-level analysis)           │
                                                                                       ▼
                                                                                [4] freeview
```

1. **Partial Volume Correction (PVC)** — `mri_gtmpvc` corrects PET signal for
   partial-volume effects and rescales it against the cerebellum
   (`src/steps/gtmpvc.py`).
2. **Surface projection** — `mri_vol2surf` projects the corrected volume onto the
   `fsaverage` cortical surface, per hemisphere (`src/steps/vol2surf.py`).
3. **Group-level analysis** — `src/run_analysis.py` concatenates subjects
   (`mri_concat`), smooths (`mris_fwhm`), and fits a GLM (`mri_glmfit`) using an
   FSGD design and contrast matrices. The FSGD may be provided or auto-generated
   from the Excel file by `src/utils/excel_to_fsgd.py`.
4. **Visualization** — `src/visualize_glmfit.py` opens the `sig.mgh` maps in
   `freeview` on the inflated `fsaverage` surface.

Steps 1–2 are the **preprocessing** stage (per patient). Step 3 is the **analysis**
stage (once per group). Step 4 is optional **visualization**.

## Prerequisites

### External tools

FreeSurfer / PETSurfer must be installed and sourced so these commands are on the
`PATH`: `mri_gtmpvc`, `mri_vol2surf`, `mri_concat`, `mris_fwhm`, `mri_glmfit`,
`freeview`. A valid `$SUBJECTS_DIR` with the **`fsaverage`** subject present is
also required.

### Python environment

Python 3 is required. Create and activate a virtual environment, then install the
pinned dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Key third-party packages: `numpy`, `pandas`, `openpyxl` (`.xlsx`), `odfpy`
(`.ods`), `nibabel` (NIfTI I/O), `rich` and `prompt_toolkit` (the interactive
launcher UI).

### Per-patient data

`recon-all` and coregistration are assumed done. For each patient you need:

1. `DATA_DIR/SUBJECT/PET.nii` — the original PET scan.
2. `SUBJECTS_DIR/SUBJECT/mri/template.reg.tau.lta` — the registration file from
   coregistration on `PET.nii`.
3. `SUBJECTS_DIR/SUBJECT/mri/gtmseg.mgz` — the GTM segmentation
   (`gtmseg --s SUBJECT`).

`SUBJECT` directory names are built from the patient ID and timestamp via
`--subjects-template` (default `YASMINE_TAU_%d_%s`) and `--data-template` (default
`TAU_%d_%s`).

!!! danger "Registration files are geometry-specific"
    An `.lta` is only valid for the exact volume geometries it was computed from.
    `template.reg.tau.lta` (original PET space) is used for PVC; the
    `aux/bbpet2anat.lta` produced *inside* the gtmpvc output (bbpet space) is what
    the surface projection uses. **They must never be swapped.** See
    [Pipeline stages](pipeline-stages.md).

## Building this documentation

The docs are built with [MkDocs](https://www.mkdocs.org/) + the Material theme.

```bash
python -m venv .docs-venv
source .docs-venv/bin/activate
pip install -r docs/requirements.txt
mkdocs serve          # live preview at http://127.0.0.1:8000
mkdocs build --strict # production build
```

The **PDF export** is produced by the `mkdocs-with-pdf` plugin and is only enabled
when the `ENABLE_PDF_EXPORT` environment variable is set (so `mkdocs serve` stays
fast). Read the Docs sets it automatically via `.readthedocs.yaml`:

```bash
ENABLE_PDF_EXPORT=1 mkdocs build
```

To publish, import the GitHub repository on
[readthedocs.org](https://readthedocs.org/); the `.readthedocs.yaml` at the repo
root is detected automatically. Replace the `YOUR_USERNAME` placeholders in
`mkdocs.yml` first.
