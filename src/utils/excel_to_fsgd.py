#!/usr/bin/env python3
"""
excel_to_fsgd.py — Convert an Excel spreadsheet to a FreeSurfer Group Descriptor (FSGD) file.

Expected Excel format (single sheet):
    Column 1  : Include    — 1 to include this row, 0 to skip it
    Column 2  : PatientID  — integer identifier for the patient
    Column 3  : Timestamp  — session label (e.g. "T0", "T1", "T2")
    Columns 4+: variables — automatically classified:
                • All-numeric columns → continuous Variables in the FSGD
                • Columns with any non-numeric value → discrete factors,
                  combined into FSGD Class labels

The full FreeSurfer subject ID is built from the PatientID and Timestamp
using the --subjects-template flag:

    subjects_template % (patient_id, timestamp)

Example:
    Include | PatientID | Timestamp | Diagnosis | Age | Sex | MMSE
    1       | 1         | T0        | Normal    | 65  | F   | 29
    0       | 2         | T0        | AD        | 72  | M   | 24  ← skipped
    1       | 3         | T0        | AD        | 68  | F   | 22

With --subjects-template "YASMINE_%d_%s", produces:
    GroupDescriptorFile 1
    Class Normal
    Class AD
    Variables Age MMSE
    Input YASMINE_1_T0 Normal-F 65 29
    Input YASMINE_3_T0 AD-F     68 22

Usage:
    python excel_to_fsgd.py input.xlsx -o design.fsgd [--title TITLE]
                                                       [--default-var VAR]
                                                       [--mean-center]
                                                       [--sheet SHEET]

See https://surfer.nmr.mgh.harvard.edu/fswiki/FsgdFormat for the FSGD specification.
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Column indices (0-based)
COL_INCLUDE = 0           # 1 = include row, 0 = skip row
COL_PATIENT_ID = 1
COL_TIMESTAMP = 2
COL_VARIABLES_START = 3  # columns from this index onward are variables

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_numeric(value) -> bool:
    """Return True if *value* can be interpreted as a float."""
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def build_subject_id(patient_id: int, timestamp: str, subjects_template: str) -> str:
    """Build the full FreeSurfer subject ID from the template."""
    return subjects_template % (patient_id, timestamp)


def read_excel(path: str, sheet_name: str | None = None) -> tuple[list[str], list[list]]:
    """
    Read the Excel file and return (headers, rows).

    Each row is a list of cell values with length == len(headers).
    Rows where the include flag (column 1) is 0 are dropped.
    """
    try:
        df = pd.read_excel(path, sheet_name=sheet_name or 0, header=0)
    except ValueError as e:
        logger.error("Sheet not found: %s", e)
        sys.exit(1)

    if df.empty:
        logger.error("The spreadsheet must have at least a header row and one data row.")
        sys.exit(1)

    headers = [str(col).strip() for col in df.columns]

    # Replace pandas NA with None for consistent downstream handling
    df = df.where(df.notna(), other=None)

    # Drop completely empty rows
    df = df.dropna(how="all")

    # Drop rows where the include flag (column 1) is 0
    df = df[df.iloc[:, COL_INCLUDE].astype(str).str.strip() != "0"]

    data_rows = df.values.tolist()

    if not data_rows:
        logger.error("The spreadsheet must have at least a header row and one data row.")
        sys.exit(1)

    return headers, data_rows


def classify_columns(
    headers: list[str], data_rows: list[list]
) -> tuple[list[int], list[int]]:
    """
    Among columns from COL_VARIABLES_START onward, determine which are
    continuous (all numeric) and which are discrete (contain any non-numeric
    value).

    Returns (discrete_indices, continuous_indices), both sorted.
    """
    discrete = []
    continuous = []

    for col_idx in range(COL_VARIABLES_START, len(headers)):
        col_values = [row[col_idx] for row in data_rows]
        if all(is_numeric(v) for v in col_values):
            continuous.append(col_idx)
        else:
            discrete.append(col_idx)

    return discrete, continuous


def build_class_label(row: list, discrete_cols: list[int]) -> str:
    """
    Build the class label for a subject row from all discrete columns.

    If there is exactly one discrete column, the label is its value directly.
    If there are multiple, they are joined with hyphens.
    If there are none, returns "Main" (single-group design).
    """
    if not discrete_cols:
        return "Main"
    parts = [str(row[col_idx]).strip() for col_idx in discrete_cols]
    return "-".join(parts)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(
    headers: list[str],
    data_rows: list[list],
    discrete_cols: list[int],
    continuous_cols: list[int],
    default_var: str | None,
    subjects_template: str,
) -> bool:
    """
    Run validation checks.  Returns True if everything is fine, False (with
    logged errors) otherwise.
    """
    ok = True

    # --- Minimum column count ---
    if len(headers) < 4:
        logger.error(
            "The spreadsheet must have at least 4 columns "
            "(Include, PatientID, Timestamp, and at least one variable)."
        )
        return False

    # --- No empty headers ---
    for i, h in enumerate(headers):
        if not h:
            logger.error("Column %d has an empty header.", i + 1)
            ok = False

    # --- Duplicate headers ---
    seen_headers = set()
    for h in headers:
        if h in seen_headers:
            logger.error("Duplicate column header: '%s'.", h)
            ok = False
        seen_headers.add(h)

    # --- PatientID checks ---
    patient_ids_with_ts = []
    for row_idx, row in enumerate(data_rows, start=2):
        pid = row[COL_PATIENT_ID]
        if pid is None:
            logger.error("Row %d: empty PatientID.", row_idx)
            ok = False
            continue
        if not isinstance(pid, (int, float)) or (isinstance(pid, float) and pid != int(pid)):
            logger.error("Row %d: PatientID '%s' is not an integer.", row_idx, pid)
            ok = False
            continue

    # --- Timestamp checks ---
    for row_idx, row in enumerate(data_rows, start=2):
        ts = row[COL_TIMESTAMP]
        if ts is None or str(ts).strip() == "":
            logger.error("Row %d: empty Timestamp.", row_idx)
            ok = False
            continue
        ts_str = str(ts).strip()
        if " " in ts_str or "\t" in ts_str:
            logger.error("Row %d: Timestamp '%s' contains whitespace.", row_idx, ts_str)
            ok = False

    # --- Build full subject IDs and check for duplicates ---
    subject_ids = []
    for row_idx, row in enumerate(data_rows, start=2):
        pid = row[COL_PATIENT_ID]
        ts = row[COL_TIMESTAMP]
        if pid is None or ts is None:
            continue
        try:
            full_id = build_subject_id(int(pid), str(ts).strip(), subjects_template)
        except (TypeError, ValueError) as e:
            logger.error("Row %d: cannot build subject ID: %s", row_idx, e)
            ok = False
            continue
        if " " in full_id or "\t" in full_id:
            logger.error(
                "Row %d: generated SubjectID '%s' contains whitespace "
                "(check --subjects-template).",
                row_idx, full_id,
            )
            ok = False
        subject_ids.append(full_id)

    if len(subject_ids) != len(set(subject_ids)):
        dupes = [s for s in set(subject_ids) if subject_ids.count(s) > 1]
        logger.error("Duplicate generated SubjectIDs: %s", dupes)
        ok = False

    # --- No empty cells in discrete columns ---
    missing_rows: set[int] = set()
    for col_idx in discrete_cols:
        col_name = headers[col_idx]
        for row_idx, row in enumerate(data_rows, start=2):
            if row[col_idx] is None or str(row[col_idx]).strip() == "":
                logger.error("Row %d, column '%s': empty cell.", row_idx, col_name)
                ok = False
                missing_rows.add(row_idx)

    # --- No empty cells in continuous columns ---
    for col_idx in continuous_cols:
        col_name = headers[col_idx]
        for row_idx, row in enumerate(data_rows, start=2):
            val = row[col_idx]
            if val is None or str(val).strip() == "":
                logger.error(
                    "Row %d, column '%s': empty cell (FSGD requires complete data).",
                    row_idx, col_name,
                )
                ok = False
                missing_rows.add(row_idx)
            elif not is_numeric(val):
                logger.error(
                    "Row %d, column '%s': non-numeric value '%s' in continuous column.",
                    row_idx, col_name, val,
                )
                ok = False
                missing_rows.add(row_idx)

    if missing_rows:
        sorted_rows = sorted(missing_rows)
        logger.error(
            "Rows with missing or invalid variable data: %s. "
            "For each row, either fill in the missing values or set the include "
            "flag (column 1) to 0 to exclude that patient from the analysis.",
            sorted_rows,
        )

    # --- DefaultVariable must be among continuous variables ---
    if default_var:
        continuous_names = [headers[i] for i in continuous_cols]
        if default_var not in continuous_names:
            logger.error(
                "--default-var '%s' is not among the continuous variables: %s",
                default_var,
                continuous_names,
            )
            ok = False

    # --- Variable name collision check ---
    variable_names = [headers[i] for i in continuous_cols]
    if len(variable_names) != len(set(variable_names)):
        logger.error("Duplicate variable names detected.")
        ok = False

    # --- Warn if no discrete columns (single-group design) ---
    if not discrete_cols:
        logger.warning(
            "No discrete factor columns detected. All subjects will be in a "
            "single class ('Main'). If this is unintended, check that at least "
            "one column (3+) contains text values."
        )

    return ok


# ---------------------------------------------------------------------------
# FSGD generation
# ---------------------------------------------------------------------------

def generate_fsgd(
    headers: list[str],
    data_rows: list[list],
    discrete_cols: list[int],
    continuous_cols: list[int],
    title: str | None,
    default_var: str | None,
    mean_center: bool,
    subjects_template: str,
) -> str:
    """Build the FSGD file content as a string."""

    lines: list[str] = []
    lines.append("GroupDescriptorFile 1")

    if title:
        lines.append(f"Title {title}")

    # --- Build class labels for every subject ---
    class_labels = []
    for row in data_rows:
        label = build_class_label(row, discrete_cols)
        class_labels.append(label)

    # Unique classes, preserving first-occurrence order
    unique_classes: list[str] = []
    for label in class_labels:
        if label not in unique_classes:
            unique_classes.append(label)

    for cls in unique_classes:
        lines.append(f"Class {cls}")

    # --- Variables line ---
    variable_names = [headers[i] for i in continuous_cols]
    if variable_names:
        lines.append("Variables " + " ".join(variable_names))

    # --- Mean-centering ---
    means: dict[int, float] = {}
    if mean_center and continuous_cols:
        for col_idx in continuous_cols:
            values = [float(row[col_idx]) for row in data_rows]
            col_mean = sum(values) / len(values)
            means[col_idx] = col_mean

        # Log the centering
        logger.info("Mean-centering applied:")
        for col_idx, col_mean in means.items():
            logger.info("  %s: mean = %.4f", headers[col_idx], col_mean)

        # Add centering info as comments in the FSGD
        lines.append("# Mean-centering was applied to continuous variables:")
        for col_idx, col_mean in means.items():
            lines.append(f"#   {headers[col_idx]}: mean = {col_mean:.4f}")

    # --- Input lines ---
    for row, cls_label in zip(data_rows, class_labels):
        patient_id = int(row[COL_PATIENT_ID])
        timestamp = str(row[COL_TIMESTAMP]).strip()
        subject_id = build_subject_id(patient_id, timestamp, subjects_template)

        parts = [f"Input {subject_id} {cls_label}"]
        for col_idx in continuous_cols:
            val = float(row[col_idx])
            if col_idx in means:
                val -= means[col_idx]
            # Format: use integer representation if the value is whole
            if val == int(val):
                parts.append(str(int(val)))
            else:
                parts.append(f"{val:.6g}")

        lines.append(" ".join(parts))

    # --- DefaultVariable ---
    if not default_var and continuous_cols:
        default_var = headers[continuous_cols[0]]
    if default_var:
        lines.append(f"DefaultVariable {default_var}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an Excel spreadsheet to a FreeSurfer FSGD file.",
        epilog=(
            "Excel format: Column 1 = Include flag (1=include, 0=skip), "
            "Column 2 = PatientID (integer), "
            "Column 3 = Timestamp (e.g. T0, T1), "
            "Columns 4+ = variables. All-numeric columns are treated as "
            "continuous variables; columns containing any text are treated "
            "as discrete factors and combined into class labels. "
            "The full subject ID is built using --subjects-template."
        ),
    )
    parser.add_argument("input", help="Path to the input Excel file (.xlsx)")
    parser.add_argument(
        "-o", "--output", required=True, help="Path for the output FSGD file"
    )
    parser.add_argument("--title", help="Title for the FSGD file (optional)")
    parser.add_argument(
        "--default-var",
        help="Default variable for display (must be a continuous variable)",
    )
    parser.add_argument(
        "--mean-center",
        action="store_true",
        help="Mean-center all continuous variables before writing the FSGD",
    )
    parser.add_argument(
        "--subjects-template", default="YASMINE_TAU_%d_%s",
        help=(
            "printf-style template for FreeSurfer subject directory names. "
            "Must contain %%d (patient ID) then %%s (timestamp). "
            "Default: YASMINE_TAU_%%d_%%s"
        ),
    )
    parser.add_argument(
        "--sheet", help="Name of the Excel sheet to read (default: active sheet)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    subjects_template = args.subjects_template
    logger.info("Using subjects template: '%s'", subjects_template)

    # --- Read ---
    headers, data_rows = read_excel(str(input_path), sheet_name=args.sheet)
    logger.info("Read %d rows from '%s'.", len(data_rows), input_path.name)
    logger.info("Columns: %s", headers)

    # --- Classify columns ---
    discrete_cols, continuous_cols = classify_columns(headers, data_rows)

    if discrete_cols:
        logger.info(
            "Discrete factor columns (form class labels): %s",
            [headers[i] for i in discrete_cols],
        )
    logger.info(
        "Continuous variable columns: %s", [headers[i] for i in continuous_cols]
    )

    if not continuous_cols:
        logger.warning("No continuous variables detected (columns 3+).")

    # --- Validate ---
    if not validate(headers, data_rows, discrete_cols, continuous_cols, args.default_var, subjects_template):
        logger.error("Validation failed. Fix the errors above and retry.")
        sys.exit(1)

    # --- Generate ---
    fsgd_content = generate_fsgd(
        headers=headers,
        data_rows=data_rows,
        discrete_cols=discrete_cols,
        continuous_cols=continuous_cols,
        title=args.title,
        default_var=args.default_var,
        mean_center=args.mean_center,
        subjects_template=subjects_template,
    )

    # --- Write ---
    output_path = Path(args.output)
    output_path.write_text(fsgd_content)
    logger.info("FSGD written to '%s'.", output_path)

    # --- Summary ---
    class_labels = [build_class_label(row, discrete_cols) for row in data_rows]
    unique_classes = list(dict.fromkeys(class_labels))

    print(f"\nSummary:")
    print(f"  Template   : {subjects_template}")
    print(f"  Subjects   : {len(data_rows)}")
    print(f"  Classes    : {len(unique_classes)} — {unique_classes}")
    print(f"  Variables  : {len(continuous_cols)} — {[headers[i] for i in continuous_cols]}")
    if args.mean_center:
        print(f"  Mean-center: yes (all continuous variables)")
    print(f"  Output     : {output_path}")


if __name__ == "__main__":
    main()
