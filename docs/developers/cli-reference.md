# CLI reference

All examples assume the virtual environment is activated and FreeSurfer is sourced.

## Interactive launcher (recommended)

```bash
python run_interactive.py
```

Menu-driven; it prompts for every input and runs the appropriate stage.

## Preprocessing (per patient)

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

## Group analysis

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
(`.xlsx`/`.ods`), one or more `.mtx` contrast matrices, and at most one `.fsgd`
(if absent, one is auto-generated into `analysis.fsgd`). All outputs are written
into `ANALYSIS_DIR`.

## Visualization

```bash
python src/visualize_glmfit.py ANALYSIS_DIR \
    [--hemi lh|rh] [--contrast NAME] [--overlay-threshold 2,5] [--subjects-dir DIR]
```

Both hemispheres and all contrasts are loaded by default (as stacked overlay
layers in freeview).

## Standalone FSGD generation

```bash
python src/utils/excel_to_fsgd.py input.xlsx -o design.fsgd \
    [--title TITLE] [--default-var VAR] [--mean-center] \
    [--subjects-template 'YASMINE_TAU_%d_%s'] [--sheet SHEET] [-v]
```

## Logs

Each stage writes a timestamped log: `pipeline_<timestamp>.log` (next to the Excel
file) for preprocessing, `analysis_<timestamp>.log` (in the analysis directory)
for analysis, and `visualize.log` for visualization. Check these to see which
patients succeeded, were skipped, or failed.
