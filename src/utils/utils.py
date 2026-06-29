import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)


def _load_excel(excel_path: str) -> pd.DataFrame:
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    try:
        return pd.read_excel(excel_path, header=0)
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")


def read_patients_from_excel(excel_path: str) -> list[tuple[int, str]]:
    """
    Returns a list of (patient_id, timestamp) tuples for rows where the
    include flag (column index 0) is 1. A patient with multiple timestamps
    (repeat scans) appears once per row.

    Warns and skips any included row with a missing patient ID or timestamp.
    """
    df = _load_excel(excel_path)
    include_col = df.iloc[:, 0]
    id_col = df.iloc[:, 1]
    ts_col = df.iloc[:, 2]

    result = []
    seen = set()
    for row_idx, (include, pid, ts) in enumerate(zip(include_col, id_col, ts_col), start=2):
        if include != 1:
            continue
        missing = []
        if not pd.notna(pid):
            missing.append("PatientID")
        if not pd.notna(ts):
            missing.append("Timestamp")
        if missing:
            logger.warning(
                "Row %d: include=1 but missing %s — skipping this patient. "
                "Fill in the missing value or set include=0 to suppress this warning.",
                row_idx, " and ".join(missing),
            )
            continue
        entry = (int(pid), ts)
        if entry not in seen:
            seen.add(entry)
            result.append(entry)
    return result
