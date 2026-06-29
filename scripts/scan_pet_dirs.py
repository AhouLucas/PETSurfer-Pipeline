import os
import re
import pandas as pd

DATA_DIR = "/media/vmalotaux/data/Yasmine"
OUTPUT_FILE = "data/all_subject_ids.xlsx"

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

df = pd.DataFrame(rows, columns=["ID", "Timestamp"])
df.sort_values(["ID", "Timestamp"], inplace=True, ignore_index=True)
df.to_excel(OUTPUT_FILE, index=False)
print(f"Written {len(rows)} rows to {OUTPUT_FILE}")
