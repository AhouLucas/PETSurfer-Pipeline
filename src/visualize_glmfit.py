"""
Visualize mri_glmfit results using freeview.

Opens the significance map(s) (sig.mgh) from a glmfit output directory overlaid
on the fsaverage inflated surface.

Usage:
    python src/visualize_glmfit.py braak-stage/

The script finds the glmfit directory for the chosen hemisphere inside the analysis
directory, then loads all contrast sig.mgh files as stacked overlay layers in
freeview (toggle visibility in the Layers panel).

Use --contrast to load a single contrast instead of all of them.
Use --glmfit-dir to point directly at a glmfit directory instead of an analysis dir.
"""

import argparse
import glob
import os
import subprocess
import sys


def find_glmfit_dir(analysis_dir: str, hemi: str) -> str:
    """Return the glmfit directory for the given hemisphere inside analysis_dir."""
    pattern = os.path.join(analysis_dir, f'all.{hemi}.pet.fsaverage.sm*.glmfit')
    matches = sorted(glob.glob(pattern))

    if len(matches) == 0:
        print(
            f'ERROR: no glmfit directory found for hemisphere "{hemi}" in {analysis_dir}\n'
            f'Expected a directory matching: all.{hemi}.pet.fsaverage.sm*.glmfit',
            file=sys.stderr,
        )
        sys.exit(1)
    if len(matches) > 1:
        names = '\n  '.join(matches)
        print(
            f'ERROR: multiple glmfit directories found for hemisphere "{hemi}" in {analysis_dir}:\n'
            f'  {names}\n'
            'Use --glmfit-dir to specify which one to use.',
            file=sys.stderr,
        )
        sys.exit(1)

    return matches[0]


def find_contrast_dirs(glmfit_dir: str, contrast: str | None) -> list[str]:
    """
    Return a list of contrast subdirectory paths that contain sig.mgh.
    If contrast is given, return only that one. Otherwise return all of them.
    """
    if contrast is not None:
        path = os.path.join(glmfit_dir, contrast)
        if not os.path.isdir(path):
            print(f'ERROR: contrast directory not found: {path}', file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(os.path.join(path, 'sig.mgh')):
            print(f'ERROR: sig.mgh not found in {path}', file=sys.stderr)
            sys.exit(1)
        return [path]

    try:
        entries = sorted(
            e.path for e in os.scandir(glmfit_dir)
            if e.is_dir() and os.path.exists(os.path.join(e.path, 'sig.mgh'))
        )
    except FileNotFoundError:
        print(f'ERROR: glmfit directory not found: {glmfit_dir}', file=sys.stderr)
        sys.exit(1)

    if len(entries) == 0:
        print(
            f'ERROR: no contrast subfolder containing sig.mgh found in {glmfit_dir}',
            file=sys.stderr,
        )
        sys.exit(1)

    return entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Visualize mri_glmfit sig.mgh results on the fsaverage inflated surface.\n\n'
            'Pass an analysis directory and all contrasts are loaded as stacked overlay\n'
            'layers in freeview — toggle visibility in the Layers panel.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'analysis_dir', nargs='?', default=None,
        help='Analysis directory produced by run_analysis.py. The glmfit directory is auto-detected.',
    )
    parser.add_argument(
        '--glmfit-dir', default=None,
        help='Path to a specific mri_glmfit output directory. Overrides analysis_dir.',
    )
    parser.add_argument(
        '--contrast', default=None,
        help='Name of a single contrast subfolder to visualize. Loads all contrasts if omitted.',
    )
    parser.add_argument(
        '--subjects-dir', default='/media/vmalotaux/data/subjects-v.7.2.0',
        help='Directory containing the fsaverage subject folder. Default: /media/vmalotaux/data/subjects-v.7.2.0',
    )
    parser.add_argument(
        '--hemi', choices=['lh', 'rh'], default='lh',
        help='Hemisphere to display. Default: lh',
    )
    parser.add_argument(
        '--overlay-threshold', default='2,5', metavar='MIN,MAX',
        help='Overlay threshold as min,max (e.g. 2,5). Default: 2,5',
    )
    args = parser.parse_args()

    if args.glmfit_dir is None and args.analysis_dir is None:
        parser.error('Provide an analysis directory or use --glmfit-dir.')

    # Resolve glmfit directory
    if args.glmfit_dir:
        glmfit_dir = args.glmfit_dir
    else:
        if not os.path.isdir(args.analysis_dir):
            print(f'ERROR: analysis directory not found: {args.analysis_dir}', file=sys.stderr)
            sys.exit(1)
        glmfit_dir = find_glmfit_dir(args.analysis_dir, args.hemi)

    contrast_dirs = find_contrast_dirs(glmfit_dir, args.contrast)

    surf_path = os.path.join(args.subjects_dir, 'fsaverage', 'surf', f'{args.hemi}.inflated')
    if not os.path.exists(surf_path):
        print(f'ERROR: surface file not found: {surf_path}', file=sys.stderr)
        sys.exit(1)

    # One -f entry per contrast so each gets its own name in the Layers panel.
    # Only the first is visible by default; toggle the others in freeview.
    f_args = []
    for i, d in enumerate(contrast_dirs):
        name = os.path.basename(d)
        sig = os.path.join(d, 'sig.mgh')
        visible = '' if i == 0 else ':visible=0'
        spec = (
            f'{surf_path}'
            ':annot=aparc.annot'
            ':annot_outline=1'
            f':overlay={sig}'
            f':overlay_threshold={args.overlay_threshold}'
            f':name={name}'
            f'{visible}'
        )
        f_args += ['-f', spec]

    if len(contrast_dirs) > 1:
        names = ', '.join(os.path.basename(d) for d in contrast_dirs)
        print(f'Loading {len(contrast_dirs)} contrasts: {names}')
        print('Toggle overlay visibility in the freeview Layers panel.')

    cmd = ['freeview'] + f_args + ['-viewport', '3d']
    print('Running:', ' '.join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()
