"""
Match closest test results to PET scan dates.

For each patient in the checklist, finds the test result whose date is closest
to the PET scan date for each configured test group. Results from all groups
are combined into a single wide-format row per patient. Test results more than
1 year away from the PET scan date are excluded (left as NaN).

Output columns follow the pipeline input spec:
  col 0: include flag (always 1)
  col 1: patient ID
  col 2: timestamp
  col 3+: all result columns from all test groups
"""

import pandas as pd
from pathlib import Path

# ─────────────────────────── CONFIGURATION ────────────────────────────

# Input files
TESTS_FILE = "data/braak_cognition.xlsx"        # Excel file with test results
CHECKLIST_FILE = "data/check_liste_FS_T0.xlsx"  # Excel file with patient IDs and PET scan dates
TESTS_SKIPROWS = 1  # Number of header rows to skip in the tests file (0 = none)

# Column name for patient ID in both files
TESTS_ID_COL = "tau_id"
TESTS_DOB_COL = "dob"  # Date of birth column in the tests file; age at PET scan is computed from this; set to None to omit
CHECKLIST_ID_COL = "ID"
CHECKLIST_PET_DATE_COL = "date_PET"
CHECKLIST_INCLUDE_COL = "select_PET"  # Column to filter rows by (must equal 1); set to None to include all

# Test groups: list of (date_column, [result_columns]) tuples.
# Each group shares a single date column. The row closest to the PET scan date
# is selected for each group independently.
TEST_GROUPS = [
    ("pet_tau_date", ["pet_tau_braak"]),
    ("date_cognitive_assessment",     ["mmse", 
                                       "memory_composite", 
                                       "language_composite", 
                                       "executive_composite", 
                                       "visuospatial_composite", 
                                       "global_cognitive_composite", 
                                       "pacc"]),
]

# Maximum allowed time difference between test date and PET scan date.
MAX_DAYS = 365

# Output
OUTPUT_FILE = "data/all_matched_results.xlsx"
TIMESTAMP_LABEL = "T0"

# ──────────────────────────── PROCESSING ──────────────────────────────

def find_best_match(patient_df, date_col, result_cols, pet_date, max_days):
    """Return a dict of {result_col: value} for the closest valid row, or NaNs."""
    subset = patient_df[
        patient_df[date_col].notna()
        & patient_df[result_cols].notna().any(axis=1)
    ].copy()

    if subset.empty:
        return {col: float("nan") for col in result_cols}

    diffs = (subset[date_col] - pet_date).abs()
    min_diff = diffs.min()

    if min_diff.days > max_days:
        return {col: float("nan") for col in result_cols}

    candidates = subset[diffs == min_diff]
    best = candidates.sort_values(date_col).iloc[0]
    return {col: best[col] for col in result_cols}


def main():
    all_date_cols = list({date_col for date_col, _ in TEST_GROUPS})
    tests_df = pd.read_excel(TESTS_FILE, skiprows=TESTS_SKIPROWS)
    checklist_df = pd.read_excel(CHECKLIST_FILE)

    for col in all_date_cols:
        tests_df[col] = pd.to_datetime(tests_df[col], dayfirst=True, format="mixed")
    if TESTS_DOB_COL is not None:
        tests_df[TESTS_DOB_COL] = pd.to_datetime(tests_df[TESTS_DOB_COL], dayfirst=True, format="mixed")
    checklist_df[CHECKLIST_PET_DATE_COL] = pd.to_datetime(
        checklist_df[CHECKLIST_PET_DATE_COL], dayfirst=True, format="mixed"
    )

    if CHECKLIST_INCLUDE_COL is not None:
        checklist_df = checklist_df[checklist_df[CHECKLIST_INCLUDE_COL] == 1]

    all_result_cols = [col for _, result_cols in TEST_GROUPS for col in result_cols]

    rows = []
    for _, row in checklist_df.iterrows():
        pid = row[CHECKLIST_ID_COL]
        pet_date = row[CHECKLIST_PET_DATE_COL]

        patient_df = tests_df[tests_df[TESTS_ID_COL] == pid]

        out_row = {
            "select": 1,
            CHECKLIST_ID_COL: pid,
            "Timestamp": TIMESTAMP_LABEL,
        }

        if TESTS_DOB_COL is not None:
            dob_values = patient_df[TESTS_DOB_COL].dropna()
            if not dob_values.empty:
                dob = dob_values.iloc[0]
                # Age in fractional years at the time of the PET scan
                out_row["age"] = (pet_date - dob).days / 365.25
            else:
                out_row["age"] = float("nan")

        for date_col, result_cols in TEST_GROUPS:
            matches = find_best_match(patient_df, date_col, result_cols, pet_date, MAX_DAYS)
            out_row.update(matches)

        rows.append(out_row)

    age_cols = ["age"] if TESTS_DOB_COL is not None else []
    out_df = pd.DataFrame(rows, columns=["select", CHECKLIST_ID_COL, "Timestamp"] + age_cols + all_result_cols)
    out_df.to_excel(OUTPUT_FILE, index=False)

    total = len(rows)
    fully_matched = sum(
        all(row[col] == row[col] for col in all_result_cols)  # NaN != NaN
        for row in rows
    )
    print(f"Done — {fully_matched}/{total} patients with all results matched.")
    print(f"Output written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
