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
import logging
import os
import subprocess
import sys

# Allow imports from src/
sys.path.insert(0, os.path.dirname(__file__))

from utils.config import DEFAULT_SUBJECTS_DIR, HEMISPHERES
from utils.utils import setup_logger

logger = logging.getLogger(__name__)


def find_glmfit_dir(analysis_dir: str, hemi: str) -> str:
    """Return the glmfit directory for the given hemisphere inside analysis_dir."""
    pattern = os.path.join(analysis_dir, f'all.{hemi}.pet.fsaverage.sm*.glmfit')
    matches = sorted(glob.glob(pattern))

    if len(matches) == 0:
        logger.error(
            'no glmfit directory found for hemisphere "%s" in %s\n'
            'Expected a directory matching: all.%s.pet.fsaverage.sm*.glmfit',
            hemi, analysis_dir, hemi,
        )
        sys.exit(1)
    if len(matches) > 1:
        names = '\n  '.join(matches)
        logger.error(
            'multiple glmfit directories found for hemisphere "%s" in %s:\n'
            '  %s\n'
            'Use --glmfit-dir to specify which one to use.',
            hemi, analysis_dir, names,
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
            logger.error('contrast directory not found: %s', path)
            sys.exit(1)
        if not os.path.exists(os.path.join(path, 'sig.mgh')):
            logger.error('sig.mgh not found in %s', path)
            sys.exit(1)
        return [path]

    try:
        entries = sorted(
            e.path for e in os.scandir(glmfit_dir)
            if e.is_dir() and os.path.exists(os.path.join(e.path, 'sig.mgh'))
        )
    except FileNotFoundError:
        logger.error('glmfit directory not found: %s', glmfit_dir)
        sys.exit(1)

    if len(entries) == 0:
        logger.error('no contrast subfolder containing sig.mgh found in %s', glmfit_dir)
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
        '--subjects-dir', default=DEFAULT_SUBJECTS_DIR,
        help=f'Directory containing the fsaverage subject folder. Default: {DEFAULT_SUBJECTS_DIR}',
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
        # Logger not yet attached to the analysis dir; lastResort routes this to stderr.
        logger.error('analysis directory not found: %s', args.analysis_dir)
        sys.exit(1)

    setup_logger(__name__, os.path.join(args.analysis_dir, 'visualize.log'), file_mode='a')

    hemis = [args.hemi] if args.hemi else list(HEMISPHERES)

    f_args = []
    for hemi in hemis:
        glmfit_dir = find_glmfit_dir(args.analysis_dir, hemi)

        contrast_dirs = find_contrast_dirs(glmfit_dir, args.contrast)

        surf_path = os.path.join(args.subjects_dir, 'fsaverage', 'surf', f'{hemi}.inflated')
        if not os.path.exists(surf_path):
            logger.error('surface file not found: %s', surf_path)
            sys.exit(1)

        f_args += build_f_args(surf_path, contrast_dirs, args.overlay_threshold, hemi)

    cmd = ['freeview'] + f_args + ['-viewport', '3d']
    logger.info('Running: %s', ' '.join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()
