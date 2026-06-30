"""
Visualize mri_glmfit results using freeview.

Opens the significance map (sig.mgh) from a glmfit output directory overlaid
on the fsaverage inflated surface.

Usage:
    python src/visualize_glmfit.py --glmfit-dir path/to/glmfit-output/all.lh.pet.fsaverage.sm05.glmfit

The script auto-detects the single contrast subfolder inside --glmfit-dir.
"""

import argparse
import os
import subprocess
import sys


def find_contrast_dir(glmfit_dir: str) -> str:
    """Return the single contrast subdirectory inside glmfit_dir, or error."""
    try:
        entries = [
            e for e in os.scandir(glmfit_dir)
            if e.is_dir() and os.path.exists(os.path.join(e.path, 'sig.mgh'))
        ]
    except FileNotFoundError:
        print(f'ERROR: glmfit directory not found: {glmfit_dir}', file=sys.stderr)
        sys.exit(1)

    if len(entries) == 0:
        print(
            f'ERROR: no contrast subfolder containing sig.mgh found in {glmfit_dir}',
            file=sys.stderr
        )
        sys.exit(1)
    if len(entries) > 1:
        names = ', '.join(e.name for e in entries)
        print(
            f'ERROR: multiple contrast subfolders found ({names}). '
            'Specify which one to use with --contrast.',
            file=sys.stderr
        )
        sys.exit(1)

    return entries[0].path


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Visualize mri_glmfit sig.mgh results on the fsaverage inflated surface.'
    )
    parser.add_argument(
        '--glmfit-dir', required=True,
        help='Path to the mri_glmfit output directory (contains the contrast subfolder).'
    )
    parser.add_argument(
        '--subjects-dir', default='/media/vmalotaux/data/subjects-v.7.2.0',
        help='Directory containing the fsaverage subject folder. Default: ./data'
    )
    parser.add_argument(
        '--hemi', choices=['lh', 'rh'], default='lh',
        help='Hemisphere to display. Default: lh'
    )
    parser.add_argument(
        '--overlay-threshold', default='2,5', metavar='MIN,MAX',
        help='Overlay threshold as min,max (e.g. 2,5). Default: 2,5'
    )
    args = parser.parse_args()

    contrast_dir = find_contrast_dir(args.glmfit_dir)
    sig_path = os.path.join(contrast_dir, 'sig.mgh')

    surf_path = os.path.join(args.subjects_dir, 'fsaverage', 'surf', f'{args.hemi}.inflated')
    if not os.path.exists(surf_path):
        print(f'ERROR: surface file not found: {surf_path}', file=sys.stderr)
        sys.exit(1)

    overlay_spec = (
        f'{surf_path}'
        ':annot=aparc.annot'
        ':annot_outline=1'
        f':overlay={sig_path}'
        f':overlay_threshold={args.overlay_threshold}'
    )

    cmd = ['freeview', '-f', overlay_spec, '-viewport', '3d']
    print('Running:', ' '.join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()
