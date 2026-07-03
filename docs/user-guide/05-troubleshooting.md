# 6. Troubleshooting

Most problems are reported clearly on screen, and every run also writes a **log
file** you can check.

## Where the logs are

| Step | Log file | Location |
|------|----------|----------|
| Preprocess | `pipeline_<date_time>.log` | next to your Excel file |
| Analyse | `analysis_<date_time>.log` | inside the analysis folder |
| Visualize | `visualize.log` | inside the analysis folder |

The log lists which patients **succeeded**, were **skipped**, or **failed**, and
usually why.

## Common messages and what to do

| Message / symptom | What it means | What to do |
|-------------------|---------------|------------|
| *"That file/directory doesn't exist"* | The path you typed is wrong. | Retype it, using ++tab++ to auto-complete. |
| *"…is not a recognised spreadsheet format"* | The patient list isn't `.xlsx` or `.ods`. | Re-save it in a supported format. |
| *"No spreadsheet found in that folder"* | The analysis folder has no patient list. | Put exactly one spreadsheet in the folder. |
| *"Multiple spreadsheets found"* | More than one spreadsheet in the folder. | Keep only one; move or delete the others. |
| *"No contrast matrix (.mtx) found"* | The analysis folder has no `.mtx`. | Add at least one contrast file. |
| A contrast has the **wrong number of columns** | A `.mtx` line doesn't match the design size. | Fix that line's number of values and re-run. The message tells you the expected count. |
| *"No glmfit output found"* | You tried to visualize before analysing. | Run the group analysis (Step 3) first. |
| *"No fsaverage/ folder found"* | The subjects directory is missing `fsaverage`. | Use the correct subjects directory, or ask your admin. |

## General tips

- **Cancel and retry.** Press ++ctrl+c++ to abandon the current step and return to
  the menu — nothing is damaged.
- **Re-running is safe.** Preprocessing skips work that's already done, so you can
  re-run it to finish patients that failed the first time.
- **Still stuck?** Note the exact on-screen message and the relevant log file, and
  send them to whoever maintains the pipeline. The
  [developer documentation](../developers/index.md) explains what each step does
  in detail.
