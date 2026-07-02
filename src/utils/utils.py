import logging
import os
import re

import pandas as pd

logger = logging.getLogger(__name__)

_TIMESTAMP_RE = re.compile(r'^T\d+$')

_SUPPORTED_EXTENSIONS = {'.xlsx', '.xls', '.ods'}


def _load_excel(excel_path: str) -> pd.DataFrame:
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Spreadsheet not found: {excel_path}")

    ext = os.path.splitext(excel_path)[1].lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: '{os.path.basename(excel_path)}'.\n"
            "Expected an .xlsx or .ods file. Re-save your spreadsheet in one of those formats."
        )

    kwargs = {'engine': 'odf'} if ext == '.ods' else {}
    try:
        return pd.read_excel(excel_path, header=0, **kwargs)
    except Exception as e:
        raise ValueError(f"Could not read spreadsheet '{excel_path}': {e}") from e


def read_patients_from_excel(excel_path: str) -> list[tuple[int, str]]:
    """
    Returns a list of (patient_id, timestamp) tuples for rows where the
    include flag (column index 0) is 1.

    Hard-fails (raises ValueError) if any included row has an invalid patient ID,
    invalid timestamp, or missing variable value. All errors are collected before
    failing so the user sees them all at once.
    """
    df = _load_excel(excel_path)

    if df.shape[1] < 3:
        raise ValueError(
            f"The spreadsheet must have at least 3 columns "
            f"(Include, PatientID, Timestamp). Found only {df.shape[1]}."
        )

    include_col = df.iloc[:, 0]
    id_col = df.iloc[:, 1]
    ts_col = df.iloc[:, 2]
    has_var_cols = df.shape[1] > 3

    errors_pid: list[str] = []
    errors_ts: list[str] = []
    errors_var: list[str] = []

    result: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()

    for i, (include, pid, ts) in enumerate(zip(include_col, id_col, ts_col)):
        row_idx = i + 2  # Excel row number (row 1 is the header)

        # --- Include flag ---
        if pd.isna(include):
            continue
        if include not in (0, 1, 0.0, 1.0):
            logger.warning(
                "Row %d: include flag is '%s' — expected 0 or 1. Treating as 0 (excluded).",
                row_idx, include,
            )
            continue
        if include != 1:
            continue

        row_has_error = False

        # --- Patient ID ---
        if not pd.notna(pid):
            errors_pid.append(f"  Row {row_idx}: missing PatientID")
            row_has_error = True
        else:
            try:
                pid_float = float(pid)
                if pid_float != int(pid_float) or int(pid_float) <= 0:
                    raise ValueError
                pid_int = int(pid_float)
            except (ValueError, TypeError):
                errors_pid.append(
                    f"  Row {row_idx}: PatientID '{pid}' is not a positive integer"
                )
                row_has_error = True
            else:
                pid = pid_int

        # --- Timestamp ---
        if not pd.notna(ts):
            errors_ts.append(f"  Row {row_idx}: missing Timestamp")
            row_has_error = True
        else:
            ts_str = str(ts).strip()
            if not _TIMESTAMP_RE.match(ts_str):
                hint = ""
                if ts_str and ts_str[0].lower() == 't' and ts_str[1:].isdigit():
                    hint = " (hint: use a capital T)"
                errors_ts.append(f"  Row {row_idx}: '{ts_str}'{hint}")
                row_has_error = True
            else:
                ts = ts_str

        # --- Variable columns (cols 3+) ---
        if has_var_cols:
            for col_pos in range(3, df.shape[1]):
                col_name = df.columns[col_pos]
                val = df.iloc[i, col_pos]
                if not pd.notna(val):
                    errors_var.append(
                        f"  Row {row_idx}, column '{col_name}': value is missing (NaN)"
                    )
                    row_has_error = True

        if row_has_error:
            continue

        # --- Duplicate check ---
        entry = (pid, ts)
        if entry in seen:
            logger.warning(
                "Row %d: duplicate entry (patient %s / %s) — already seen, skipping.",
                row_idx, pid, ts,
            )
            continue
        seen.add(entry)
        result.append(entry)

    # --- Hard fail if any errors were collected ---
    if errors_pid or errors_ts or errors_var:
        parts: list[str] = []
        if errors_pid:
            parts.append(
                "Invalid PatientID(s) — PatientIDs must be positive integers:\n"
                + "\n".join(errors_pid)
            )
        if errors_ts:
            parts.append(
                'Invalid timestamp(s) — Timestamps must be in the form "T0", "T1", "T2", etc.:\n'
                + "\n".join(errors_ts)
            )
        if errors_var:
            parts.append(
                "Missing variable value(s) for included patient(s) — fill in the value "
                "or set include=0 to exclude that patient:\n"
                + "\n".join(errors_var)
            )
        raise ValueError(
            "Fix the following errors in your spreadsheet before re-running:\n\n"
            + "\n\n".join(parts)
        )

    if not result:
        raise ValueError(
            "No patients to process. Check that at least one row has include=1 "
            "with a valid PatientID and Timestamp."
        )

    return result
