"""
Match closest test results to PET scan dates.

For each patient in the checklist, finds the test result (from a separate
Excel file) whose date is closest to the PET scan date. Outputs an Excel
file with: patient ID, timestamp, test result, and test date.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────── CONFIGURATION ────────────────────────────

# Input files
TESTS_FILE = "data/braak_cognition.xlsx"  # Excel file containing test results
CHECKLIST_FILE = "data/check_liste_FS_T0.xlsx"  # Excel file containing patient IDs and PET scan dates

# Column names in the tests file
TESTS_ID_COL = "tau_id"
TESTS_RESULT_COL = "pet_tau_braak"
TESTS_DATE_COL = "pet_tau_date"

# Column names in the checklist file
CHECKLIST_ID_COL = "ID"
CHECKLIST_PET_DATE_COL = "date_PET"
CHECKLIST_INCLUDE_COL = "select_PET"  # Set to a column name (str) to filter rows, or None to include all

# Output
OUTPUT_FILE = "data/matched_results.xlsx"
TIMESTAMP_LABEL = "T0"

# ──────────────────────────── PROCESSING ──────────────────────────────

def main():
    tests_df = pd.read_excel(TESTS_FILE, parse_dates=[TESTS_DATE_COL], skiprows=1)  # Skip first row if it contains metadata
    checklist_df = pd.read_excel(CHECKLIST_FILE, parse_dates=[CHECKLIST_PET_DATE_COL])

    tests_df[TESTS_DATE_COL] = pd.to_datetime(tests_df[TESTS_DATE_COL], dayfirst=True, format='mixed')
    checklist_df[CHECKLIST_PET_DATE_COL] = pd.to_datetime(checklist_df[CHECKLIST_PET_DATE_COL], dayfirst=True, format='mixed')

    # Filter checklist if an include column is specified
    if CHECKLIST_INCLUDE_COL is not None:
        checklist_df = checklist_df[checklist_df[CHECKLIST_INCLUDE_COL] == 1]

    results = []
    skipped_no_test = 0
    skipped_not_in_tests = 0

    for _, row in checklist_df.iterrows():
        pid = row[CHECKLIST_ID_COL]
        pet_date = row[CHECKLIST_PET_DATE_COL]

        # Get all tests for this patient that actually have a result
        patient_tests = tests_df[
            (tests_df[TESTS_ID_COL] == pid)
            & tests_df[TESTS_RESULT_COL].notna()
            & tests_df[TESTS_DATE_COL].notna()
        ]

        if patient_tests.empty:
            if pid in tests_df[TESTS_ID_COL].values:
                skipped_no_test += 1
            else:
                skipped_not_in_tests += 1
            continue

        # Compute absolute time difference; on tie, earliest wins
        diffs = (patient_tests[TESTS_DATE_COL] - pet_date).abs()
        # Among rows with the minimum difference, pick the earliest date
        min_diff = diffs.min()
        candidates = patient_tests[diffs == min_diff]
        best = candidates.sort_values(TESTS_DATE_COL).iloc[0]

        results.append({
            TESTS_ID_COL: pid,
            "Timestamp": TIMESTAMP_LABEL,
            TESTS_RESULT_COL: best[TESTS_RESULT_COL],
            # TESTS_DATE_COL: best[TESTS_DATE_COL], # Add date if you want to see the test date in the output excel file    
            # CHECKLIST_PET_DATE_COL: pet_date,
        })

    out_df = pd.DataFrame(results)
    for col in [TESTS_DATE_COL, CHECKLIST_PET_DATE_COL]:
        if col in out_df.columns:
            out_df[col] = out_df[col].dt.strftime("%d/%m/%Y")
    out_df.to_excel(OUTPUT_FILE, index=False)

    # Summary
    total = len(checklist_df)
    matched = len(results)
    print(f"Done — {matched}/{total} patients matched.")
    if skipped_not_in_tests:
        print(f"  {skipped_not_in_tests} patient(s) not found in tests file.")
    if skipped_no_test:
        print(f"  {skipped_no_test} patient(s) found but had no valid test result.")
    print(f"Output written to: {OUTPUT_FILE}")
 


if __name__ == "__main__":
    main()
