import logging
import os
import re
import subprocess
import sys

import pandas as pd

logger = logging.getLogger(__name__)

_TIMESTAMP_RE = re.compile(r'^T\d+$')

_LOG_FMT = '%(asctime)s  %(levelname)-8s  %(message)s'
_LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'


class _IndentFormatter(logging.Formatter):
    """Indent continuation lines of multi-line log messages with '│ '."""

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        lines = text.splitlines()
        if len(lines) <= 1:
            return text
        head, *rest = lines
        return head + '\n' + '\n'.join('│   ' + l for l in rest)


def make_formatter() -> _IndentFormatter:
    return _IndentFormatter(fmt=_LOG_FMT, datefmt=_LOG_DATEFMT)


def setup_logger(
    name: str, log_path: str, file_mode: str = 'a'
) -> logging.Logger:
    """
    Return a logger with a DEBUG file handler and an INFO stdout handler, both
    using the shared indent formatter. Idempotent: existing handlers are cleared
    first so repeated calls (e.g. from the interactive launcher) don't stack.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # let handlers decide what to show
    logger.propagate = False
    logger.handlers.clear()

    fmt = make_formatter()

    file_handler = logging.FileHandler(log_path, mode=file_mode)
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

    return logger


def run_command(argv: list[str], label: str, logger: logging.Logger) -> int:
    """
    Run a subprocess command, log its stdout/stderr at DEBUG, and return the
    exit code. Callers own the [RUNNING]/[DONE]/[FAILED] messages and decide how
    to react to a non-zero return code.
    """
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    logger.debug('[OUTPUT] %s stdout:\n%s\nstderr:\n%s', label, result.stdout, result.stderr)
    return result.returncode


_SUPPORTED_EXTENSIONS = {'.xlsx', '.xls', '.ods'}


def _load_excel(excel_path: str, sheet_name=None) -> pd.DataFrame:
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Spreadsheet not found: {excel_path}")

    ext = os.path.splitext(excel_path)[1].lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: '{os.path.basename(excel_path)}'.\n"
            "Expected an .xlsx or .ods file. Re-save your spreadsheet in one of those formats."
        )

    kwargs = {'engine': 'odf'} if ext == '.ods' else {}
    if sheet_name is not None:
        kwargs['sheet_name'] = sheet_name
    try:
        return pd.read_excel(excel_path, header=0, **kwargs)
    except Exception as e:
        raise ValueError(f"Could not read spreadsheet '{excel_path}': {e}") from e


def load_included_rows(excel_path: str, sheet_name=None) -> tuple[list[str], list[list]]:
    """
    Load the spreadsheet and return (headers, rows), keeping only rows whose
    include flag (column index 0) is 1.

    Each returned row is a list of cell values (NaN normalized to None) with the
    PatientID (col 1) normalized to int and the Timestamp (col 2) to a stripped
    string. Validates that every included row has a positive-integer PatientID and
    a "T<number>" timestamp; all errors are collected and raised together as a
    single ValueError. Rows with an unrecognized include flag are skipped with a
    warning. Duplicate and variable-column checks are left to the caller, since
    they differ between the preprocessing and FSGD consumers.
    """
    df = _load_excel(excel_path, sheet_name)

    if df.shape[1] < 3:
        raise ValueError(
            f"The spreadsheet must have at least 3 columns "
            f"(Include, PatientID, Timestamp). Found only {df.shape[1]}."
        )

    headers = [str(col).strip() for col in df.columns]
    # Normalize pandas NA to None for consistent downstream handling.
    df = df.where(df.notna(), other=None)

    errors_pid: list[str] = []
    errors_ts: list[str] = []
    rows: list[list] = []

    for i in range(len(df)):
        row = list(df.iloc[i])
        row_idx = i + 2  # Excel row number (row 1 is the header)
        include = row[0]

        # --- Include flag ---
        if include is None:
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
        pid = row[1]
        if pid is None:
            errors_pid.append(f"  Row {row_idx}: missing PatientID")
            row_has_error = True
        else:
            try:
                pid_float = float(pid)
                if pid_float != int(pid_float) or int(pid_float) <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors_pid.append(
                    f"  Row {row_idx}: PatientID '{pid}' is not a positive integer"
                )
                row_has_error = True
            else:
                row[1] = int(pid_float)

        # --- Timestamp ---
        ts = row[2]
        if ts is None:
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
                row[2] = ts_str

        if row_has_error:
            continue

        rows.append(row)

    # --- Hard fail if any errors were collected ---
    if errors_pid or errors_ts:
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
        raise ValueError(
            "Fix the following errors in your spreadsheet before re-running:\n\n"
            + "\n\n".join(parts)
        )

    return headers, rows


def read_patients_from_excel(excel_path: str) -> list[tuple[int, str]]:
    """
    Returns a list of unique (patient_id, timestamp) tuples for rows where the
    include flag (column index 0) is 1. Duplicate rows are skipped with a warning.

    Hard-fails (raises ValueError) if any included row has an invalid patient ID
    or timestamp — all such errors are collected before failing.
    """
    _, rows = load_included_rows(excel_path)

    result: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    for row in rows:
        entry = (row[1], row[2])
        if entry in seen:
            logger.warning(
                "Duplicate entry (patient %s / %s) — already seen, skipping.",
                entry[0], entry[1],
            )
            continue
        seen.add(entry)
        result.append(entry)

    if not result:
        raise ValueError(
            "No patients to process. Check that at least one row has include=1 "
            "with a valid PatientID and Timestamp."
        )

    return result
