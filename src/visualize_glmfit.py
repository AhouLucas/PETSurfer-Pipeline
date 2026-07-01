"""
Visualize mri_glmfit results using freeview.

Opens the significance map(s) (sig.mgh) from a glmfit output directory overlaid
on the fsaverage inflated surface.

Usage:
    python src/visualize_glmfit.py braak-stage/

Both hemispheres are loaded by default. Use --hemi to restrict to one.
All contrasts are loaded as stacked overlay layers (toggle in the Layers panel).
Use --contrast to load a single contrast instead of all of them.
"""

import argparse
import glob
import os
import subprocess
import sys

HEMISPHERES = ('lh', 'rh')


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


def build_f_args(
    surf_path: str,
    contrast_dirs: list[str],
    overlay_threshold: str,
    hemi: str,
) -> list[str]:
    """
    Build the list of -f arguments for one hemisphere.
    Each contrast gets its own entry with a hemi-prefixed name so layers from
    lh and rh are distinguishable in the freeview Layers panel.
    Only the first contrast of the first hemisphere loaded will be visible by default.
    """
    f_args = []
    for i, d in enumerate(contrast_dirs):
        name = f'{hemi}.{os.path.basename(d)}'
        sig = os.path.join(d, 'sig.mgh')
        visible = '' if i == 0 else ':visible=0'
        spec = (
            f'{surf_path}'
            ':annot=aparc.annot'
            ':annot_outline=1'
            f':overlay={sig}'
            f':overlay_threshold={overlay_threshold}'
            f':name={name}'
            f'{visible}'
        )
        f_args += ['-f', spec]
    return f_args


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Visualize mri_glmfit sig.mgh results on the fsaverage inflated surface.\n\n'
            'Both hemispheres are loaded by default. All contrasts are loaded as stacked\n'
            'overlay layers in freeview — toggle visibility in the Layers panel.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'analysis_dir',
        help='Analysis directory produced by run_analysis.py. The glmfit directory is auto-detected.',
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
        '--hemi', choices=['lh', 'rh'], default=None,
        help='Hemisphere to display. Loads both hemispheres if omitted.',
    )
    parser.add_argument(
        '--overlay-threshold', default='2,5', metavar='MIN,MAX',
        help='Overlay threshold as min,max (e.g. 2,5). Default: 2,5',
    )
    args = parser.parse_args()

    if not os.path.isdir(args.analysis_dir):
        print(f'ERROR: analysis directory not found: {args.analysis_dir}', file=sys.stderr)
        sys.exit(1)

    hemis = [args.hemi] if args.hemi else list(HEMISPHERES)

    f_args = []
    for hemi in hemis:
        glmfit_dir = find_glmfit_dir(args.analysis_dir, hemi)

        contrast_dirs = find_contrast_dirs(glmfit_dir, args.contrast)

        surf_path = os.path.join(args.subjects_dir, 'fsaverage', 'surf', f'{hemi}.inflated')
        if not os.path.exists(surf_path):
            print(f'ERROR: surface file not found: {surf_path}', file=sys.stderr)
            sys.exit(1)

        f_args += build_f_args(surf_path, contrast_dirs, args.overlay_threshold, hemi)

    cmd = ['freeview'] + f_args + ['-viewport', '3d']
    print('Running:', ' '.join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()
