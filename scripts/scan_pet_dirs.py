import os
import re
import openpyxl

DATA_DIR = "/path/to/data"
OUTPUT_FILE = "/path/to/output.xlsx"

VALID_TIMESTAMPS = {"T0", "T1", "T2"}
DIR_PATTERN = re.compile(r"^TAU_(\d+)_(T\d+)$")

rows = []
for entry in os.scandir(DATA_DIR):
    if not entry.is_dir():
        continue
    m = DIR_PATTERN.match(entry.name)
    if not m:
        continue
    patient_id, timestamp = m.group(1), m.group(2)
    if timestamp not in VALID_TIMESTAMPS:
        continue
    if not os.path.isfile(os.path.join(entry.path, "PET.nii")):
        continue
    rows.append((int(patient_id), timestamp))

wb = openpyxl.Workbook()
ws = wb.active
ws.append(["ID", "Timestamp"])
for row in rows:
    ws.append(row)
wb.save(OUTPUT_FILE)
print(f"Written {len(rows)} rows to {OUTPUT_FILE}")
