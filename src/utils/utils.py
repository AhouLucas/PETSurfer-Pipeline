import os
import pandas as pd


def _load_excel(excel_path: str) -> pd.DataFrame:
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    try:
        return pd.read_excel(excel_path, header=0)
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")


def read_all_ids_from_excel(excel_path: str) -> list:
    """
    Returns patient IDs (column index 1) for rows where the include flag
    (column index 0) is 1.
    """
    df = _load_excel(excel_path)
    include_col = df.iloc[:, 0]
    id_col = df.iloc[:, 1]
    included = id_col[include_col == 1].dropna().unique().tolist()
    return [int(pid) for pid in included]


def read_timestamps_from_excel(excel_path: str) -> dict:
    """
    Returns a dict mapping patient ID (column index 1) to timestamp
    (column index 2) for rows where the include flag (column index 0) is 1.
    """
    df = _load_excel(excel_path)
    include_col = df.iloc[:, 0]
    id_col = df.iloc[:, 1]
    ts_col = df.iloc[:, 2]

    result = {}
    for include, pid, ts in zip(include_col, id_col, ts_col):
        if include == 1 and pd.notna(pid) and pd.notna(ts):
            result[int(pid)] = ts
    return result
