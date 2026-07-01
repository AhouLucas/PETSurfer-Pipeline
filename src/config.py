"""
PipelineConfig: holds all user-supplied parameters for one pipeline run.
Build it once with build_config(args) and pass it to each step function.
"""

import argparse
import os
from dataclasses import dataclass, field

from utils.utils import read_patients_from_excel


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
        '--subjects-dir', default='./data',
        help='Directory containing FreeSurfer subject folders. Default: ./data'
    )
    parser.add_argument(
        '--data-dir', default='./dataPET',
        help='Directory containing raw PET image folders. Default: ./dataPET'
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

    if not patients:
        raise ValueError(
            "No included patients found in the Excel file. "
            "Check that column 0 (include flag) has at least one row set to 1."
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
