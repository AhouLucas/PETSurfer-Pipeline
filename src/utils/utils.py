import os
import pandas as pd

def read_all_ids_from_excel(excel_path, id_column_name):
    """
    Reads all patient IDs from the specified Excel file.

    Args:
        excel_path (str): Path to the Excel file.
        id_column_name (str): Name of the column containing patient IDs.
    
    Returns:
        list: A list of patient IDs.
    """

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"The specified Excel file does not exist: {excel_path}")

    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        raise ValueError(f"Error reading the Excel file: {e}")

    if id_column_name not in df.columns:
        raise ValueError(f"The specified ID column '{id_column_name}' does not exist in the Excel file.")

    return df[id_column_name].dropna().unique().tolist()

def read_timestamps_from_excel(excel_path, id_column_name, timestamp_column_name):
    """
    Reads timestamps for each patient ID from the specified Excel file.

    Args:
        excel_path (str): Path to the Excel file.
        id_column_name (str): Name of the column containing patient IDs.
        timestamp_column_name (str): Name of the column containing timestamps.
    
    Returns:
        dict: A dictionary mapping patient IDs to their corresponding timestamps.
    """

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"The specified Excel file does not exist: {excel_path}")

    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        raise ValueError(f"Error reading the Excel file: {e}")

    if id_column_name not in df.columns or timestamp_column_name not in df.columns:
        raise ValueError(f"One or both specified columns '{id_column_name}' and '{timestamp_column_name}' do not exist in the Excel file.")

    timestamps_dict = {}
    for _, row in df.iterrows():
        patient_id = row[id_column_name]
        timestamp = row[timestamp_column_name]
        if pd.notna(patient_id) and pd.notna(timestamp):
            timestamps_dict[patient_id] = timestamp

    return timestamps_dict