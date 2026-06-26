#!/usr/bin/env python3
"""Compare two NIfTI (.nii.gz) files to validate pipeline output."""

import sys
import numpy as np
import nibabel as nib


def compare_nifti(ref_path, test_path, atol=1e-6, rtol=1e-5):
    ref = nib.load(ref_path)
    test = nib.load(test_path)

    print(f"Reference : {ref_path}")
    print(f"Test      : {test_path}")
    print()

    # --- Header ---
    print(f"Header of {ref_path}:")
    print(ref.header)
    print()
    print(f"Header of {test_path}:")
    print(test.header)


    # --- Shape ---
    if ref.shape != test.shape:
        print(f"FAIL  Shape mismatch: {ref.shape} vs {test.shape}")
        return False
    print(f"OK    Shape: {ref.shape}")

    # --- Affine ---
    aff_close = np.allclose(ref.affine, test.affine, atol=1e-4)
    if not aff_close:
        max_diff = np.max(np.abs(ref.affine - test.affine))
        print(f"WARN  Affine differs (max diff: {max_diff:.6g})")
    else:
        print("OK    Affine matches")

    # --- Voxel data ---
    ref_data = ref.get_fdata()
    test_data = test.get_fdata()

    mask = np.abs(ref_data) > 1e-6
    rel_diff = np.abs(ref_data[mask] - test_data[mask]) / np.abs(ref_data[mask]) 
    diff = np.abs(ref_data - test_data)
    max_diff = diff.max()
    mean_diff = diff.mean()
    n_nonzero = np.count_nonzero(diff)
    pct_differ = 100.0 * n_nonzero / diff.size

    print()
    print(f"  Max absolute diff : {max_diff:.6g}")
    print(f"  Mean absolute diff: {mean_diff:.6g}")
    print(f"  Max relative diff: {rel_diff.max():.6g}")
    print(f"  Mean relative diff: {rel_diff.mean():.6g}")
    print(f"  Voxels differing  : {n_nonzero} / {diff.size} ({pct_differ:.4f}%)")

    # Correlation (skip if constant)
    ref_flat, test_flat = ref_data.ravel(), test_data.ravel()
    if ref_flat.std() > 0 and test_flat.std() > 0:
        corr = np.corrcoef(ref_flat, test_flat)[0, 1]
        print(f"  Pearson correlation: {corr:.8f}")

    match = np.allclose(ref_data, test_data, atol=atol, rtol=rtol)
    print()
    print(f"{'OK    Match' if match else 'FAIL  Mismatch'} (atol={atol}, rtol={rtol})")
    return match


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <reference.nii.gz> <test.nii.gz> [atol] [rtol]")
        sys.exit(1)

    atol = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-6
    rtol = float(sys.argv[4]) if len(sys.argv) > 4 else 1e-5

    ok = compare_nifti(sys.argv[1], sys.argv[2], atol, rtol)
    sys.exit(0 if ok else 1)
