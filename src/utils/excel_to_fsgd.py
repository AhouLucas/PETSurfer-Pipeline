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
import os
import sys
from pathlib import Path

# Allow running as a script from src/utils/ (so `utils.utils` resolves).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    # When imported as part of the `utils` package (e.g. by run_analysis.py).
    from utils.utils import load_included_rows
except ModuleNotFoundError:
    # When run standalone from src/utils/, utils.py is a sibling module.
    from utils import load_included_rows

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
    Read the Excel or ODS file and return (headers, rows) for included rows only.

    Thin wrapper over utils.load_included_rows: keeps rows where the include flag
    (column 1) is 1, normalizes PatientID/Timestamp, and validates them (positive
    integer PatientID, "T<number>" timestamp). Raises ValueError on any problem so
    callers can report it and exit.
    """
    headers, data_rows = load_included_rows(path, sheet_name=sheet_name)
    if not data_rows:
        raise ValueError(
            "No included rows found. Check that at least one row has the include "
            "flag (column 1) set to 1."
        )
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
) -> None:
    """
    Run FSGD-specific validation checks and raise ValueError (listing every
    problem at once) if any fail.

    PatientID and Timestamp validity are guaranteed by the shared loader
    (utils.load_included_rows), so they are not re-checked here. This function
    covers only what FSGD generation needs: complete column layout, complete
    variable cells, and a well-formed set of classes/variables.
    """
    errors: list[str] = []

    # --- Minimum column count ---
    if len(headers) < 4:
        raise ValueError(
            "The spreadsheet must have at least 4 columns "
            "(Include, PatientID, Timestamp, and at least one variable)."
        )

    # --- No empty headers ---
    for i, h in enumerate(headers):
        if not h:
            errors.append(f"Column {i + 1} has an empty header.")

    # --- Duplicate headers ---
    seen_headers = set()
    for h in headers:
        if h in seen_headers:
            errors.append(f"Duplicate column header: '{h}'.")
        seen_headers.add(h)

    # --- Build full subject IDs and check for duplicates ---
    # PatientID is an int and Timestamp a clean string (loader-guaranteed), so
    # any whitespace in the generated ID can only come from --subjects-template.
    subject_ids = []
    for row_idx, row in enumerate(data_rows, start=2):
        full_id = build_subject_id(int(row[COL_PATIENT_ID]), str(row[COL_TIMESTAMP]), subjects_template)
        if " " in full_id or "\t" in full_id:
            errors.append(
                f"Row {row_idx}: generated SubjectID '{full_id}' contains whitespace "
                "(check --subjects-template)."
            )
        subject_ids.append(full_id)

    if len(subject_ids) != len(set(subject_ids)):
        dupes = [s for s in set(subject_ids) if subject_ids.count(s) > 1]
        errors.append(f"Duplicate generated SubjectIDs: {dupes}")

    # --- No empty cells in discrete columns ---
    missing_rows: set[int] = set()
    for col_idx in discrete_cols:
        col_name = headers[col_idx]
        for row_idx, row in enumerate(data_rows, start=2):
            if row[col_idx] is None or str(row[col_idx]).strip() == "":
                errors.append(f"Row {row_idx}, column '{col_name}': empty cell.")
                missing_rows.add(row_idx)

    # --- No empty cells in continuous columns ---
    for col_idx in continuous_cols:
        col_name = headers[col_idx]
        for row_idx, row in enumerate(data_rows, start=2):
            val = row[col_idx]
            if val is None or str(val).strip() == "":
                errors.append(
                    f"Row {row_idx}, column '{col_name}': empty cell (FSGD requires complete data)."
                )
                missing_rows.add(row_idx)
            elif not is_numeric(val):
                errors.append(
                    f"Row {row_idx}, column '{col_name}': non-numeric value '{val}' in continuous column."
                )
                missing_rows.add(row_idx)

    if missing_rows:
        sorted_rows = sorted(missing_rows)
        errors.append(
            f"Rows with missing or invalid variable data: {sorted_rows}. "
            "For each row, either fill in the missing values or set the include "
            "flag (column 1) to 0 to exclude that patient from the analysis."
        )

    # --- DefaultVariable must be among continuous variables ---
    if default_var:
        continuous_names = [headers[i] for i in continuous_cols]
        if default_var not in continuous_names:
            errors.append(
                f"--default-var '{default_var}' is not among the continuous "
                f"variables: {continuous_names}"
            )

    # --- Variable name collision check ---
    variable_names = [headers[i] for i in continuous_cols]
    if len(variable_names) != len(set(variable_names)):
        errors.append("Duplicate variable names detected.")

    # --- Warn if no discrete columns (single-group design) ---
    if not discrete_cols:
        logger.warning(
            "No discrete factor columns detected. All subjects will be in a "
            "single class ('Main'). If this is unintended, check that at least "
            "one column (3+) contains text values."
        )

    if errors:
        raise ValueError(
            "Spreadsheet validation failed — fix the following and retry:\n  "
            + "\n  ".join(errors)
        )


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
    logging.basicConfig(format="%(levelname)s: %(message)s")
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
    try:
        headers, data_rows = read_excel(str(input_path), sheet_name=args.sheet)
    except (ValueError, FileNotFoundError) as e:
        logger.error("%s", e)
        sys.exit(1)
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
    try:
        validate(headers, data_rows, discrete_cols, continuous_cols, args.default_var, subjects_template)
    except ValueError as e:
        logger.error("%s", e)
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
