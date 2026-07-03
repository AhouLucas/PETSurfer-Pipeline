# Architecture

## Project structure

```text
.
├── README.md            # Source of the developer docs
├── requirements.txt     # Pinned Python dependencies
├── run_interactive.py   # Guided interactive launcher for all pipeline steps
├── mkdocs.yml           # Documentation site configuration
├── docs/                # This documentation
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

## Entry points

- **`run_interactive.py`** — a guided TUI (`rich` + `prompt_toolkit`) that wraps
  all three stages behind a menu (1 preprocess / 2 analyse / 3 visualize / q
  quit). It validates paths, prompts for inputs, and calls the same functions the
  CLI scripts use. Recommended for non-developer users. `Ctrl+C` returns to the
  main menu.
- **`src/run_preprocessing.py`** — non-interactive entry point that runs the
  preprocessing stage for every included patient: `gtmpvc` then (on success)
  `vol2surf`. Writes `pipeline_<timestamp>.log` next to the Excel file.
  Already-present outputs are skipped unless `--force` is passed.
- **`src/run_analysis.py`** — group-level analysis. Auto-discovers inputs from an
  analysis directory, resolves/generates the FSGD, validates contrast matrices
  against the design, then per hemisphere runs `mri_concat --prune` →
  `mris_fwhm --smooth-only` → `mri_glmfit`. Writes `analysis_<timestamp>.log` into
  the analysis directory.
- **`src/visualize_glmfit.py`** — locates the glmfit output directory, finds the
  contrast `sig.mgh` maps, and launches `freeview` with them overlaid on the
  `fsaverage` inflated surface. Writes `visualize.log`.

## Steps

- **`src/steps/gtmpvc.py`** — `run_gtmpvc_patient()` runs `mri_gtmpvc` for one
  patient. Requires `PET.nii`, `template.reg.tau.lta`, and `gtmseg.mgz`, and
  produces the `gtmpvc.no.tfe.cerebellum.cortex.output/` directory containing the
  rescaled PET volume (`input.rescaled.nii.gz`) and `aux/bbpet2anat.lta`. Runs
  standalone via its own `__main__` block.
- **`src/steps/vol2surf.py`** — `run_vol2surf_patient()` runs `mri_vol2surf` for
  both hemispheres, projecting `input.rescaled.nii.gz` (using
  `aux/bbpet2anat.lta`) onto `fsaverage`, producing
  `{hemi}.pet.fsaverage.sm00.nii.gz`. Also runs standalone.

## Utilities

- **`src/utils/config.py`** — the shared configuration layer. Defines the
  `PipelineConfig` dataclass (all user-supplied parameters + the resolved patient
  list), the shared pipeline constants (output directory/file-name patterns,
  hemispheres, default paths), `add_common_args()` (registers the common CLI flags
  in one place so every script's `--help` stays consistent), and `build_config()`
  (reads the Excel file, validates directories, and populates the patient list).
  Per-patient paths are computed on demand by `PipelineConfig.subject_path()` /
  `.data_path()`.
- **`src/utils/utils.py`** — low-level helpers: logger setup with indented
  multi-line formatting (`setup_logger`), subprocess execution with logging
  (`run_command`), and Excel/ODS reading with validation of the positional column
  contract (`load_included_rows`, `read_patients_from_excel`).
- **`src/utils/excel_to_fsgd.py`** — converts an Excel spreadsheet into a
  FreeSurfer Group Descriptor (`.fsgd`) file. Both a standalone CLI tool and a
  module imported by `run_analysis.py` for FSGD auto-generation. See
  [FSGD & GLM](fsgd-and-glm.md).
