"""
Flag patients with pipeline warnings in the Excel include column.

Reads the pipeline log file and sets the include flag (column 0) to 0 for
any (patient_id, timestamp) row that has at least one WARNING line in the log.

Usage:
    python scripts/flag_warned_patients.py --excel-path data/matched_results.xlsx
    python scripts/flag_warned_patients.py --excel-path data/matched_results.xlsx --log-path src/pipeline.log
"""

import argparse
import re
import sys
import pandas as pd

# Matches lines like: "2026-07-01 12:00:00  WARNING   ... patient 1234 / T0 ..."
# The patient ID and timestamp appear as "patient <id> / <timestamp>" anywhere in the line.
WARNING_PATTERN = re.compile(r'WARNING.*patient (\d+) / (\S+)')


def parse_warnings(log_path: str) -> set[tuple[int, str]]:
    """Return the set of (patient_id, timestamp) pairs that have at least one WARNING."""
    warned = set()
    with open(log_path, 'r') as f:
        for line in f:
            m = WARNING_PATTERN.search(line)
            if m:
                warned.add((int(m.group(1)), m.group(2)))
    return warned


def flag_excel(excel_path: str, warned: set[tuple[int, str]]) -> int:
    """Set include flag to 0 for warned (patient_id, timestamp) rows. Returns count of rows changed."""
    df = pd.read_excel(excel_path, header=0)

    include_col = df.columns[0]
    patient_col = df.columns[1]
    timestamp_col = df.columns[2]

    mask = df.apply(
        lambda r: (int(r[patient_col]), str(r[timestamp_col]).strip()) in warned,
        axis=1,
    )
    changed = int((mask & (df[include_col] != 0)).sum())
    df.loc[mask, include_col] = 0

    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    return changed


def main():
    parser = argparse.ArgumentParser(
        description='Set include flag to 0 for patients with pipeline warnings.'
    )
    parser.add_argument('--excel-path', required=True,
                        help='Path to the Excel file to update in place.')
    parser.add_argument('--log-path', default='src/pipeline.log',
                        help='Path to the pipeline log file (default: src/pipeline.log).')
    args = parser.parse_args()

    warned = parse_warnings(args.log_path)
    if not warned:
        print('No warnings found in log — nothing to change.')
        sys.exit(0)

    print(f'Found warnings for {len(warned)} scan(s): '
          + ', '.join(f'{pid}/{ts}' for pid, ts in sorted(warned)))

    changed = flag_excel(args.excel_path, warned)
    print(f'Updated {changed} row(s) in {args.excel_path}.')


if __name__ == '__main__':
    main()
