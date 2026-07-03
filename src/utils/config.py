"""
PipelineConfig: holds all user-supplied parameters for one pipeline run.
Build it once with build_config(args) and pass it to each step function.
"""

import argparse
import os
from dataclasses import dataclass, field

from utils.utils import read_patients_from_excel

# ---------------------------------------------------------------------------
# Shared pipeline constants
# ---------------------------------------------------------------------------

# Default data locations (overridable via CLI flags).
DEFAULT_SUBJECTS_DIR = '/media/vmalotaux/data/subjects-v.7.2.0'
DEFAULT_DATA_DIR = '/media/vmalotaux/data/Yasmine'

# Hemispheres processed by the surface steps.
HEMISPHERES = ('lh', 'rh')

# gtmpvc output directory (relative to a subject dir) and the files that must
# exist inside it before the step counts as complete. These files are also the
# required inputs for the vol2surf step.
GTMPVC_OUTPUT_DIRNAME = 'mri/gtmpvc.no.tfe.cerebellum.cortex.output'
GTMPVC_OUTPUT_FILES = [
    'input.rescaled.nii.gz',
    'aux/bbpet2anat.lta',
]

# vol2surf output filename pattern, written into each subject's mri/ directory.
VOL2SURF_FILENAME = '{hemi}.pet.fsaverage.sm00.nii.gz'


@dataclass
class PipelineConfig:
    subjects_dir: str
    data_dir: str
    excel_path: str
    projfrac: float
    fwhm: int
    subjects_template: str
    data_template: str
    fsgd_path: str | None
    contrast_matrix_path: str | None  # .mtx file passed to mri_glmfit --C
    force: bool = False

    # Populated by build_config from the Excel file.
    # Each entry is (patient_id, timestamp); a patient with repeat scans
    # appears once per scan so both are processed independently.
    patients: list = field(default_factory=list)

    def subject_path(self, patient_id: int, timestamp: str) -> str:
        """Absolute path to a patient's FreeSurfer subject directory."""
        return os.path.join(
            self.subjects_dir,
            self.subjects_template % (patient_id, timestamp)
        )

    def data_path(self, patient_id: int, timestamp: str) -> str:
        """Absolute path to a patient's raw PET data directory."""
        return os.path.join(
            self.data_dir,
            self.data_template % (patient_id, timestamp)
        )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Register all shared CLI flags on an argparse parser."""
    parser.add_argument(
        '--excel-path', required=True,
        help='Path to the Excel spreadsheet with patient data.'
    )
    parser.add_argument(
        '--subjects-dir', default=DEFAULT_SUBJECTS_DIR,
        help=f'Directory containing FreeSurfer subject folders. Default: {DEFAULT_SUBJECTS_DIR}'
    )
    parser.add_argument(
        '--data-dir', default=DEFAULT_DATA_DIR,
        help=f'Directory containing raw PET image folders. Default: {DEFAULT_DATA_DIR}'
    )
    parser.add_argument(
        '--fsgd-path', default=None,
        help='Path to the FSGD file used by mri_glmfit (optional).'
    )
    parser.add_argument(
        '--contrast-matrix-path', default=None,
        help='Path to the contrast matrix (.mtx) passed to mri_glmfit --C (optional).'
    )
    parser.add_argument(
        '--projfrac', type=float, default=0.5,
        help='Projection fraction for mri_vol2surf. Default: 0.5'
    )
    parser.add_argument(
        '--fwhm', type=int, default=5,
        help='Surface smoothing FWHM (mm). Default: 5'
    )
    parser.add_argument(
        '--subjects-template', default='YASMINE_TAU_%d_%s',
        help='printf-style template for subject directory names. Default: YASMINE_TAU_%%d_%%s'
    )
    parser.add_argument(
        '--data-template', default='TAU_%d_%s',
        help='printf-style template for PET data directory names. Default: TAU_%%d_%%s'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Recompute all steps even if output files already exist.'
    )


def build_config(args: argparse.Namespace) -> PipelineConfig:
    """
    Construct a PipelineConfig from parsed CLI args.
    Reads patient IDs and timestamps from the Excel file.
    """
    patients = read_patients_from_excel(args.excel_path)

    # Directory existence checks
    if not os.path.isdir(args.subjects_dir):
        raise ValueError(
            f"Subjects directory not found: {args.subjects_dir}\n"
            "Pass --subjects-dir with the correct path."
        )
    if not os.path.isdir(args.data_dir):
        raise ValueError(
            f"Data directory not found: {args.data_dir}\n"
            "Pass --data-dir with the correct path."
        )
    if getattr(args, 'fsgd_path', None) and not os.path.exists(args.fsgd_path):
        raise ValueError(f"FSGD file not found: {args.fsgd_path}")
    if getattr(args, 'contrast_matrix_path', None) and not os.path.exists(args.contrast_matrix_path):
        raise ValueError(f"Contrast matrix file not found: {args.contrast_matrix_path}")

    # Per-patient subject directory existence
    missing_dirs = []
    for pid, ts in patients:
        subject_name = args.subjects_template % (pid, ts)
        path = os.path.join(args.subjects_dir, subject_name)
        if not os.path.isdir(path):
            missing_dirs.append(f"  {path}")
    if missing_dirs:
        raise ValueError(
            f"The following subject directories were not found under {args.subjects_dir}:\n"
            + "\n".join(missing_dirs)
            + "\nCheck that the patients in your spreadsheet have been processed by FreeSurfer."
        )

    return PipelineConfig(
        subjects_dir=args.subjects_dir,
        data_dir=args.data_dir,
        excel_path=args.excel_path,
        fsgd_path=args.fsgd_path,
        contrast_matrix_path=args.contrast_matrix_path,
        projfrac=args.projfrac,
        fwhm=args.fwhm,
        subjects_template=args.subjects_template,
        data_template=args.data_template,
        patients=patients,
        force=args.force,
    )
