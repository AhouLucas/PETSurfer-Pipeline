# PETSurfer Pipeline

<p align="center">
  <a href="https://petsurfer-pipeline.readthedocs.io">
    <img src="https://img.shields.io/badge/docs-readthedocs-blue?logo=readthedocs&logoColor=white" alt="Documentation">
  </a>
  <a href="https://petsurfer-pipeline.readthedocs.io/en/latest/pdf/petsurfer-pipeline.pdf">
    <img src="https://img.shields.io/badge/docs-PDF-red?logo=adobeacrobatreader&logoColor=white" alt="PDF">
  </a>
  <img src="https://img.shields.io/badge/python-3.x-blue?logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/FreeSurfer-PETSurfer-green" alt="PETSurfer">
</p>

> Automated CLI/TUI pipeline for **tau PET neuroimaging research on
> Alzheimer's disease biomarkers** (Braak staging across diagnostic groups)
> at IoNS, built around [PETSurfer](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer).

A guided interactive launcher (`run_interactive.py`) walks researchers through
every step without requiring programming knowledge. The underlying command-line
scripts remain available for automation and scripting.

📖 **Full documentation:** https://petsurfer-pipeline.readthedocs.io

---

## Table of contents

1. [The pipeline at a glance](#the-pipeline-at-a-glance)
2. [Prerequisites](#prerequisites)
3. [Project structure](#project-structure)
4. [Usage](#usage)
5. [Input & output formats](#input--output-formats)
6. [Notes & references](#notes--references)
7. [Contributing](#contributing)
8. [Building the documentation locally](#building-the-documentation-locally)

---

## The pipeline at a glance

The pipeline **assumes that `recon-all` and coregistration (`mri_coreg`) have
already been run** for each patient. It picks up from partial-volume correction
onward. The data flow is:

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
   partial-volume effects and rescales/calibrates the signal against the
   cerebellum. Implemented in `src/steps/gtmpvc.py`.
   ([reference](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#ROI_Analysis.2C_Setting_Up_Reference_Regions_for_KM.2C_and_Apply_Partial_Volume_Correction_.28if_using.29))

2. **Surface projection** — `mri_vol2surf` projects the corrected PET volume
   onto the `fsaverage` cortical surface, per hemisphere. Implemented in
   `src/steps/vol2surf.py`.
   ([reference](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis))

3. **Group-level analysis** — `src/run_analysis.py` concatenates all subjects'
   surface maps (`mri_concat`), smooths them (`mris_fwhm`), and fits a GLM
   (`mri_glmfit`) using an FSGD design and one or more contrast matrices. The
   FSGD can be provided or **auto-generated from the Excel file** by
   `src/utils/excel_to_fsgd.py`.
   (references: [PETSurfer Wiki](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer#Surface-based_analysis), [GLM Tutorial](https://www.nmr.mgh.harvard.edu/~jbm/jip/jip-glm/glm-tutorial.html))

4. **Visualization** — `src/visualize_glmfit.py` opens the resulting
   significance maps (`sig.mgh`) in `freeview` on the inflated `fsaverage`
   surface.

Steps 1–2 are the **preprocessing** stage (run per patient). Step 3 is the
**analysis** stage (run once over a whole group). Step 4 is optional
**visualization**.

---

## Prerequisites

### External tools

FreeSurfer / PETSurfer must be installed and sourced so the following commands
are on your `PATH`:

`mri_gtmpvc`, `mri_vol2surf`, `mri_concat`, `mris_fwhm`, `mri_glmfit`,
`freeview`.

You also need a valid `$SUBJECTS_DIR` and the **`fsaverage`** subject present in
it (the surface steps project onto `fsaverage`).

### Python environment

Python 3 is required. The main third-party packages are:

```
numpy
pandas
openpyxl        # .xlsx / .xls reading and writing
odfpy           # .ods reading
nibabel         # NIfTI I/O (validation scripts)
rich            # interactive launcher UI
prompt_toolkit  # interactive launcher prompts (tab-completion)
```

Create and activate a virtual environment:

```bash
python -m venv .env
source .env/bin/activate
```

Then install the pinned versions (recommended):

```bash
pip install -r requirements.txt
```

> **Note:** `run_interactive.py` depends on `rich` and `prompt_toolkit`; both are
> pinned in `requirements.txt`.

### Per-patient data

`recon-all` and coregistration (`mri_coreg`) are assumed to be done before using
this pipeline. For each patient, you need at least:

1. `DATA_DIR/SUBJECT/PET.nii` — the original PET scan (in the raw PET data
   directory).
2. `SUBJECTS_DIR/SUBJECT/mri/template.reg.tau.lta` — the registration file
   produced during coregistration on `PET.nii` (in the FreeSurfer subject
   directory).
3. `SUBJECTS_DIR/SUBJECT/mri/gtmseg.mgz` — the GTM segmentation, produced with
   `gtmseg --s SUBJECT`.

`SUBJECT` directory names are built from the patient ID and timestamp via the
`--subjects-template` (default `YASMINE_TAU_%d_%s`) and `--data-template`
(default `TAU_%d_%s`) flags.

> **Registration files are geometry-specific.** An `.lta` is only valid for the
> exact volume geometries it was computed from. `template.reg.tau.lta` (original
> PET space) is used for PVC; the `aux/bbpet2anat.lta` produced *inside* the
> gtmpvc output (bbpet space) is what the surface projection uses. They must
> never be swapped.

---

## Project structure

```bash
.
├── README.md            # This document
├── requirements.txt     # Pinned Python dependencies
├── run_interactive.py   # Guided interactive launcher for all pipeline steps
├── scripts/             # Auxiliary one-off scripts (not part of the pipeline)
│   ├── compare_nifti.py
│   ├── flag_warned_patients.py
│   ├── match_tests_to_pet.py
│   └── scan_pet_dirs.py
└── src/                 # Main pipeline code
    ├── run_preprocessing.py   # Entry point: gtmpvc → vol2surf (per patient)
    ├── run_analysis.py        # Entry point: concat → smooth → GLM (group)
    ├── visualize_glmfit.py    # Entry point: open results in freeview
    ├── steps/                 # Individual preprocessing steps
    │   ├── gtmpvc.py
    │   └── vol2surf.py
    └── utils/                 # Shared helpers
        ├── config.py
        ├── excel_to_fsgd.py
        └── utils.py
```

### Entry points

- **`run_interactive.py`** — a guided TUI (built with `rich` and
  `prompt_toolkit`) that wraps all three stages behind a menu (1 preprocess /
  2 analyse / 3 visualize / q quit). It validates paths, prompts for the
  required inputs, and calls the same functions the CLI scripts use. This is the
  recommended entry point for non-developer users. `Ctrl+C` returns to the main
  menu.

- **`src/run_preprocessing.py`** — non-interactive entry point that runs the
  preprocessing stage for every included patient: `gtmpvc` then (on success)
  `vol2surf`. Writes a `pipeline_<timestamp>.log` next to the Excel file.
  Already-present outputs are skipped unless `--force` is passed.

- **`src/run_analysis.py`** — group-level analysis. Auto-discovers its inputs
  from an analysis directory, resolves/generates the FSGD, validates the
  contrast matrices against the design, then per hemisphere runs
  `mri_concat --prune` → `mris_fwhm --smooth-only` → `mri_glmfit`. Writes an
  `analysis_<timestamp>.log` into the analysis directory.

- **`src/visualize_glmfit.py`** — locates the glmfit output directory,
  finds the contrast `sig.mgh` maps, and launches `freeview` with them overlaid
  on the `fsaverage` inflated surface. Writes a `visualize.log`.

### Steps

- **`src/steps/gtmpvc.py`** — `run_gtmpvc_patient()` runs `mri_gtmpvc` for one
  patient. It requires `PET.nii`, `template.reg.tau.lta`, and `gtmseg.mgz`, and
  produces the `gtmpvc.no.tfe.cerebellum.cortex.output/` directory containing the
  rescaled PET volume (`input.rescaled.nii.gz`) and `aux/bbpet2anat.lta`. Runs
  standalone via its own `__main__` block.

- **`src/steps/vol2surf.py`** — `run_vol2surf_patient()` runs `mri_vol2surf` for
  both hemispheres, projecting `input.rescaled.nii.gz` (using
  `aux/bbpet2anat.lta`) onto `fsaverage`, producing
  `{hemi}.pet.fsaverage.sm00.nii.gz`. Also runs standalone.

### Utilities

- **`src/utils/config.py`** — the shared configuration layer. Defines the
  `PipelineConfig` dataclass (all user-supplied parameters + the resolved
  patient list), the shared pipeline constants (output directory/file name
  patterns, hemispheres, default paths), `add_common_args()` (registers the
  common CLI flags in one place so every script's `--help` stays consistent), and
  `build_config()` (reads the Excel file, validates directories, and populates
  the patient list). Paths to each patient's subject/data directory are computed
  on demand by `PipelineConfig.subject_path()` / `.data_path()`.

- **`src/utils/utils.py`** — low-level shared helpers: logger setup with
  indented multi-line formatting (`setup_logger`), subprocess execution with
  logging (`run_command`), and Excel/ODS reading with validation of the
  positional column contract (`load_included_rows`, `read_patients_from_excel`).

- **`src/utils/excel_to_fsgd.py`** — converts an Excel spreadsheet into a
  FreeSurfer Group Descriptor (`.fsgd`) file. It classifies variable columns as
  discrete (→ FSGD classes) or continuous (→ FSGD variables), validates the
  data, and emits the FSGD. It is both a **standalone CLI tool** and a module
  imported by `run_analysis.py` for FSGD auto-generation.

### Auxiliary scripts

These live in `scripts/` and are **not part of the pipeline**; they are small
one-off or validation utilities.

| Script | Purpose |
|--------|---------|
| `compare_nifti.py` | Threshold-based comparison of two `.nii.gz` volumes (shape, affine, correlation, relative diff) — used to validate reproductions across machines/runs. |
| `flag_warned_patients.py` | Reads a pipeline log and sets the include flag to 0 in the Excel file for any patient that produced a WARNING, so they can be excluded from analysis. |
| `match_tests_to_pet.py` | Data-prep: matches each patient's cognitive/tau test results to the closest PET-scan date and emits a pipeline-format spreadsheet. Configured via module-level constants. |
| `scan_pet_dirs.py` | Scans the raw PET directory tree for valid subjects (matching the naming pattern with a present `PET.nii`) and writes a spreadsheet of IDs/timestamps. |

---

## Usage

All examples assume the virtual environment is activated and FreeSurfer is
sourced.

### Interactive launcher (recommended)

```bash
python run_interactive.py
```

Menu-driven; it prompts for every input and runs the appropriate stage.

### Preprocessing (per patient)

```bash
python src/run_preprocessing.py --excel-path patients.xlsx \
    [--subjects-dir DIR] [--data-dir DIR] \
    [--projfrac 0.5] [--fwhm 5] \
    [--subjects-template 'YASMINE_TAU_%d_%s'] [--data-template 'TAU_%d_%s'] \
    [--force]
```

`--excel-path` is required. Outputs already present are skipped unless `--force`.
Individual steps can also be run on their own, e.g.
`python src/steps/gtmpvc.py --excel-path ...` (same flags).

### Group analysis

```bash
python src/run_analysis.py ANALYSIS_DIR \
    [--excel-path patients.xlsx] \
    [--contrast-matrix-path c1.mtx c2.mtx] \
    [--subjects-dir DIR] [--fwhm 5] \
    [--fsgd-path existing.fsgd] [--title TITLE] \
    [--default-var Age] [--mean-center] [--design dods|doss]
```

`ANALYSIS_DIR` is the only required argument. When the input flags are omitted,
they are **auto-discovered** from that directory: exactly one spreadsheet
(`.xlsx`/`.ods`), one or more `.mtx` contrast matrices, and at most one
`.fsgd` (if absent, one is auto-generated into `analysis.fsgd`). All outputs are
written into `ANALYSIS_DIR`.

### Visualization

```bash
python src/visualize_glmfit.py ANALYSIS_DIR \
    [--hemi lh|rh] [--contrast NAME] [--overlay-threshold 2,5] [--subjects-dir DIR]
```

Both hemispheres and all contrasts are loaded by default (as stacked overlay
layers in freeview).

### Standalone FSGD generation

```bash
python src/utils/excel_to_fsgd.py input.xlsx -o design.fsgd \
    [--title TITLE] [--default-var VAR] [--mean-center] \
    [--subjects-template 'YASMINE_TAU_%d_%s'] [--sheet SHEET] [-v]
```

### Logs

Each stage writes a timestamped log: `pipeline_<timestamp>.log` (next to the
Excel file) for preprocessing, `analysis_<timestamp>.log` (in the analysis
directory) for analysis, and `visualize.log` for visualization. Check these to
see which patients succeeded, were skipped, or failed.

---

## Input & output formats

### Excel patient list

Columns are read **by position, not by name**. Do not add or reorder columns
before index 2.

| Index | Content | Type | Notes |
|-------|---------|------|-------|
| 0 | Include flag | int (0 or 1) | 1 = process this patient, 0 = skip |
| 1 | Patient ID | int | Used to build directory names |
| 2 | Timestamp | string (`"T0"`, `"T1"`, …) | Used to build directory names |
| 3+ | Class / variable columns | mixed | See below |

For columns at index 3 and beyond, the type is **inferred from the data**:

- A column whose values are **all numeric** → a **continuous variable**
  (an FSGD `Variables` entry / GLM covariate).
- A column with **any non-numeric value** → a **discrete factor**. Multiple
  discrete factors are combined into compound FSGD **class** labels via a
  Cartesian product (e.g. `AD-F`).

`.xlsx` and `.ods` files are supported. A patient with repeat scans
(same ID, different timestamps) appears once per scan row so each scan is
processed independently.

### FSGD (`.fsgd`)

The FSGD is the GLM design. `excel_to_fsgd.py` / `run_analysis.py` emit a file
containing:

- `GroupDescriptorFile 1` header (and an optional `Title`)
- one `Class` line per discrete group (in first-occurrence order)
- a `Variables` line listing the continuous variables
- one `Input <subject_id> <class> <var values…>` line per included subject
- an optional `DefaultVariable`
- optional mean-centering of continuous variables (`--mean-center`)

Two designs are supported (passed to `mri_glmfit` and used to size the contrast
matrices):

- **DODS** — Different Offset, Different Slope: separate intercept + slope per
  group. Number of regressors = `n_classes × (n_variables + 1)`.
- **DOSS** — Different Offset, Same Slope: pooled slopes across groups. Number
  of regressors = `n_classes + n_variables`.

Auto-generated FSGDs end with a marker line (`# Generated by run_analysis.py`).
On re-runs, `run_analysis.py` detects that marker and regenerates the file so it
stays in sync with the Excel input; a user-provided FSGD (without the marker) is
used as-is.

See the [FSGD format reference](https://surfer.nmr.mgh.harvard.edu/fswiki/FsgdFormat).

### Contrast matrix (`.mtx`)

Plain-text file with one contrast per row. Every value must be numeric, and each
row must have **exactly `n_regressors` columns**, matching the FSGD design (see
formulas above). `run_analysis.py` validates every `.mtx` against the FSGD
before running any analysis and reports all problems at once.

The contrast is applied during inference only (not during $\hat{\beta}$ estimation).
Zeroing a column controls for a variable without testing it; dropping a
regressor entirely is not equivalent.

### Produced outputs

| Path (relative to subject or analysis dir) | Produced by | Contents |
|--------------------------------------------|-------------|----------|
| `mri/gtmpvc.no.tfe.cerebellum.cortex.output/input.rescaled.nii.gz` | gtmpvc | Rescaled, cerebellum-calibrated PET volume (bbpet space) |
| `mri/gtmpvc.no.tfe.cerebellum.cortex.output/aux/bbpet2anat.lta` | gtmpvc | Registration for the rescaled volume (used by vol2surf) |
| `mri/{lh,rh}.pet.fsaverage.sm00.nii.gz` | vol2surf | PET projected onto `fsaverage`, per hemisphere |
| `all.{hemi}.pet.fsaverage.sm00.nii.gz` | analysis (concat) | All subjects concatenated, per hemisphere |
| `all.{hemi}.pet.fsaverage.sm{fwhm}.nii.gz` | analysis (smooth) | Smoothed concatenated map |
| `all.{hemi}.pet.fsaverage.sm{fwhm}.glmfit/` | analysis (GLM) | GLM output; one subfolder per contrast, each with `sig.mgh` |
| `analysis.fsgd` | analysis | Auto-generated FSGD (if none provided) |

---

## Notes & references

- **Reproducibility / validation.** Floating-point non-determinism across
  machines and runs is expected in FreeSurfer tools. Validation should be
  threshold-based (e.g. correlation > 0.99, max relative difference < ~5%), not
  bitwise. `scripts/compare_nifti.py` implements this kind of comparison.

- **Skips are safe.** The preprocessing steps check for their outputs and skip
  work that is already done, so re-running the pipeline only fills in what's
  missing (use `--force` to recompute).

### Reference links

- [PETSurfer wiki](https://surfer.nmr.mgh.harvard.edu/fswiki/PetSurfer)
- [FreeSurfer wiki](https://surfer.nmr.mgh.harvard.edu/fswiki/FreeSurferWiki)
- [`recon-all`](https://surfer.nmr.mgh.harvard.edu/fswiki/recon-all)
- [`mri_coreg`](https://surfer.nmr.mgh.harvard.edu/fswiki/mri_coreg)
- [FSGD format](https://surfer.nmr.mgh.harvard.edu/fswiki/FsgdFormat)
- [DODS vs DOSS](https://surfer.nmr.mgh.harvard.edu/fswiki/DodsDoss)

---

## Contributing

When modifying the pipeline, keep the documentation in sync:

- Update the relevant page under `docs/` alongside any code change (CLI flags,
  new steps, changed behaviour, etc.).
- Run `mkdocs serve` locally to check that the page renders correctly before pushing.
- If you add or change a TUI screen, update the screenshot list in
  `docs/assets/screenshots/README.md` with the new expected filename and caption.

---

## Building the documentation locally

The docs are built with [MkDocs](https://www.mkdocs.org/) (Material theme) and
live in the `docs/` folder. They are separate from the pipeline's Python
environment, so set up a dedicated virtual environment:

```bash
python -m venv .docs-venv
source .docs-venv/bin/activate
pip install -r docs/requirements.txt
```

### Live preview

```bash
mkdocs serve
```

Opens a live-reloading preview at http://127.0.0.1:8000. The PDF is **not**
generated during serve (it would slow down every reload); only the HTML site is
built.

### Build the HTML site

```bash
mkdocs build
```

Output goes to `site/` (git-ignored).

### Build with PDF export

```bash
ENABLE_PDF_EXPORT=1 mkdocs build
```

Produces `site/pdf/petsurfer-pipeline.pdf` in addition to the HTML site.
Requires [WeasyPrint](https://doc.courtbouillon.org/weasyprint/) system
dependencies (installed automatically with `docs/requirements.txt` on most
systems).
</content>
