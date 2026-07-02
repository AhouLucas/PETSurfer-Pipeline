#!/usr/bin/env python3
"""
PETSurfer interactive launcher — guided entry point for all pipeline steps.

Usage:
    python run_interactive.py
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

# Allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

DEFAULT_SUBJECTS_DIR = '/media/vmalotaux/data/subjects-v.7.2.0'
DEFAULT_DATA_DIR = '/media/vmalotaux/data/Yasmine'
DEFAULT_SUBJECTS_TEMPLATE = 'YASMINE_TAU_%d_%s'
DEFAULT_DATA_TEMPLATE = 'TAU_%d_%s'


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def ask_path(prompt_text: str, must_exist: bool = True, is_file: bool = True,
             default: str | None = None) -> str:
    """Ask for a filesystem path; re-prompt if the path doesn't exist.

    Relative paths are resolved against the current working directory.
    """
    while True:
        value = Prompt.ask(prompt_text, default=default or "")
        if not value:
            console.print("[red]Please enter a path.[/red]")
            continue
        value = str(Path(value).resolve())
        if must_exist:
            check = os.path.isfile(value) if is_file else os.path.isdir(value)
            if not check:
                kind = "file" if is_file else "directory"
                console.print(f"[red]That {kind} doesn't exist — please try again.[/red]")
                continue
        return value


def _clear_logger(name: str) -> None:
    """Remove all handlers from a named logger so re-runs don't stack them."""
    lgr = logging.getLogger(name)
    lgr.handlers.clear()


# ---------------------------------------------------------------------------
# Preprocessing flow
# ---------------------------------------------------------------------------

def preprocessing_flow() -> None:
    console.rule("[bold cyan]Preprocess patients[/bold cyan]")
    console.print(
        "This step runs partial volume correction ([italic]mri_gtmpvc[/italic]) "
        "then surface projection ([italic]mri_vol2surf[/italic]) for each patient.\n"
    )

    excel_path = ask_path(
        "Path to the patient list Excel file [.xlsx]",
        must_exist=True, is_file=True,
    )
    subjects_dir = ask_path(
        "Subjects directory (root folder containing FreeSurfer subject folders)",
        must_exist=True, is_file=False,
        default=DEFAULT_SUBJECTS_DIR,
    )
    data_dir = ask_path(
        "Raw PET data directory",
        must_exist=True, is_file=False,
        default=DEFAULT_DATA_DIR,
    )
    force = Confirm.ask("Force recompute even if output files already exist?", default=False)

    summary = (
        f"[bold]Patient list:[/bold]        {excel_path}\n"
        f"[bold]Subjects directory:[/bold]  {subjects_dir}\n"
        f"[bold]PET data directory:[/bold]  {data_dir}\n"
        f"[bold]Force recompute:[/bold]     {'Yes' if force else 'No'}"
    )
    console.print(Panel(summary, title="[bold green]Ready to preprocess[/bold green]", box=box.ROUNDED))

    if not Confirm.ask("Proceed?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    from utils.config import add_common_args, build_config
    from utils.utils import make_formatter
    from steps.gtmpvc import _run_gtmpvc_patient
    from steps.vol2surf import _run_vol2surf_patient

    _clear_logger('petsurfer')
    logger = logging.getLogger('petsurfer')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fmt = make_formatter()

    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'pipeline_rerun.log')
    fh = logging.FileHandler(log_file, mode='a')
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    ch.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.addHandler(ch)

    parser = argparse.ArgumentParser()
    add_common_args(parser)
    cli_args = ['--excel-path', excel_path, '--subjects-dir', subjects_dir, '--data-dir', data_dir]
    if force:
        cli_args.append('--force')
    args = parser.parse_args(cli_args)

    logger.info('Preprocessing started. Log file: %s', log_file)

    try:
        config = build_config(args)
    except ValueError as e:
        console.print(Panel(f"[red]{e}[/red]", title="[bold red]Error[/bold red]", box=box.ROUNDED))
        return

    try:
        for patient_id, timestamp in config.patients:
            ok = _run_gtmpvc_patient(config, patient_id, timestamp, logger)
            if ok:
                _run_vol2surf_patient(config, patient_id, timestamp, logger)
            else:
                logger.warning(
                    '[SKIPPED] vol2surf — patient %s / %s — gtmpvc did not succeed',
                    patient_id, timestamp,
                )
    except Exception as e:
        console.print(Panel(
            f"[red]{e}[/red]\n\nSee the log file for details: {log_file}",
            title="[bold red]Unexpected error[/bold red]", box=box.ROUNDED,
        ))
        logger.debug('Unexpected error:', exc_info=True)
        return

    logger.info('Preprocessing finished.')
    console.print("\n[bold green]Preprocessing complete![/bold green]")


# ---------------------------------------------------------------------------
# Analysis flow
# ---------------------------------------------------------------------------

def analysis_flow() -> None:
    console.rule("[bold cyan]Run group analysis[/bold cyan]")
    console.print(
        "This step runs group-level analysis ([italic]concat → smooth → GLM[/italic]) "
        "on fully preprocessed data.\n"
        "Your analysis folder should contain your patient list [bold](.xlsx)[/bold] "
        "and contrast matrices [bold](.mtx)[/bold].\n"
    )

    analysis_dir = ask_path(
        "Path to your analysis folder",
        must_exist=True, is_file=False,
    )

    # Auto-discovery preview
    xlsx = sorted(Path(analysis_dir).glob('*.xlsx')) + sorted(Path(analysis_dir).glob('*.xls'))
    mtx = sorted(Path(analysis_dir).glob('*.mtx'))
    if xlsx:
        console.print(f"  [dim]Found spreadsheet:  {xlsx[0].name}[/dim]")
    if mtx:
        console.print(f"  [dim]Found contrast file(s): {', '.join(f.name for f in mtx)}[/dim]")
    console.print()

    subjects_dir = ask_path(
        "Subjects directory (root folder containing FreeSurfer subject folders)",
        must_exist=True, is_file=False,
        default=DEFAULT_SUBJECTS_DIR,
    )
    fwhm_str = Prompt.ask("Surface smoothing kernel size (mm)", default="5")

    # Advanced settings
    design = 'dods'
    mean_center = False
    default_var: str | None = None

    if Confirm.ask("\nConfigure advanced settings? (GLM design, mean-centering, default variable)", default=False):
        console.print(
            "\n[bold]Design type[/bold]\n"
            "  [cyan]dods[/cyan]  Each group gets its own slope — more flexible, recommended when unsure.\n"
            "  [cyan]doss[/cyan]  Groups share a common slope — simpler, fewer parameters.\n"
        )
        design = Prompt.ask("Design type", choices=['dods', 'doss'], default='dods')

        console.print(
            "\n[bold]Mean-centering[/bold]\n"
            "  Subtracts the group mean from continuous variables (e.g. age, MMSE).\n"
            "  Makes the intercept more interpretable. Usually recommended.\n"
        )
        mean_center = Confirm.ask("Mean-center continuous variables?", default=False)

        console.print(
            "\n[bold]Default variable[/bold]\n"
            "  Which continuous variable freeview highlights by default. Leave blank to skip.\n"
        )
        dv = Prompt.ask("Default variable name (or press Enter to skip)", default="")
        default_var = dv or None

    summary = (
        f"[bold]Analysis folder:[/bold]     {analysis_dir}\n"
        f"[bold]Subjects directory:[/bold]  {subjects_dir}\n"
        f"[bold]Smoothing FWHM:[/bold]      {fwhm_str} mm\n"
        f"[bold]Design:[/bold]              {design.upper()}\n"
        f"[bold]Mean-center:[/bold]         {'Yes' if mean_center else 'No'}"
        + (f"\n[bold]Default variable:[/bold]  {default_var}" if default_var else "")
    )
    console.print(Panel(summary, title="[bold green]Ready to run analysis[/bold green]", box=box.ROUNDED))

    if not Confirm.ask("Proceed?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    from run_analysis import run_analysis, setup_logger as analysis_setup_logger

    args = argparse.Namespace(
        analysis_dir=analysis_dir,
        excel_path=None,
        contrast_matrix_path=None,
        subjects_dir=subjects_dir,
        fwhm=int(fwhm_str),
        subjects_template=DEFAULT_SUBJECTS_TEMPLATE,
        fsgd_path=None,
        title=None,
        default_var=default_var,
        mean_center=mean_center,
        design=design,
    )

    _clear_logger('run_analysis')
    logger, log_path = analysis_setup_logger(analysis_dir)

    try:
        run_analysis(args, logger)
    except SystemExit as e:
        if e.code != 0:
            console.print(Panel(
                f"[red]Analysis failed.[/red]\n\nSee the log file for details: {log_path}",
                title="[bold red]Error[/bold red]", box=box.ROUNDED,
            ))
        return
    except ValueError as e:
        console.print(Panel(
            f"[red]{e}[/red]\n\nSee the log file for details: {log_path}",
            title="[bold red]Error[/bold red]", box=box.ROUNDED,
        ))
        return
    except Exception:
        console.print(Panel(
            f"[red]An unexpected error occurred.[/red]\n\nSee the log file for details: {log_path}",
            title="[bold red]Error[/bold red]", box=box.ROUNDED,
        ))
        logger.debug('Unexpected error:', exc_info=True)
        return

    console.print("\n[bold green]Analysis complete![/bold green]")


# ---------------------------------------------------------------------------
# Visualization flow
# ---------------------------------------------------------------------------

def visualize_flow() -> None:
    console.rule("[bold cyan]Visualize results[/bold cyan]")
    console.print(
        "This opens your GLM significance maps in freeview overlaid on the brain surface.\n"
    )

    analysis_dir = ask_path(
        "Path to your analysis folder (same folder used for group analysis)",
        must_exist=True, is_file=False,
    )
    subjects_dir = ask_path(
        "Subjects directory (must contain an [italic]fsaverage/[/italic] folder)",
        must_exist=True, is_file=False,
        default=DEFAULT_SUBJECTS_DIR,
    )

    hemi_choice = Prompt.ask(
        "Which hemisphere to display?",
        choices=['both', 'lh', 'rh'],
        default='both',
    )
    hemi: str | None = None if hemi_choice == 'both' else hemi_choice

    overlay_threshold = Prompt.ask(
        "Overlay threshold MIN,MAX  (values below MIN are hidden; above MAX are fully colored)",
        default='2,5',
    )

    contrast_input = Prompt.ask(
        "Single contrast to show — leave blank to show all contrasts",
        default="",
    )
    contrast: str | None = contrast_input or None

    summary = (
        f"[bold]Analysis folder:[/bold]     {analysis_dir}\n"
        f"[bold]Subjects directory:[/bold]  {subjects_dir}\n"
        f"[bold]Hemisphere:[/bold]          {hemi_choice}\n"
        f"[bold]Overlay threshold:[/bold]   {overlay_threshold}\n"
        f"[bold]Contrast:[/bold]            {contrast or 'all'}"
    )
    console.print(Panel(summary, title="[bold green]Ready to visualize[/bold green]", box=box.ROUNDED))

    if not Confirm.ask("Open freeview?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    from visualize_glmfit import build_f_args, find_contrast_dirs, find_glmfit_dir

    hemis = ['lh', 'rh'] if hemi is None else [hemi]
    f_args: list[str] = []

    try:
        for h in hemis:
            glmfit_dir = find_glmfit_dir(analysis_dir, h)
            contrast_dirs = find_contrast_dirs(glmfit_dir, contrast)
            surf_path = os.path.join(subjects_dir, 'fsaverage', 'surf', f'{h}.inflated')
            if not os.path.exists(surf_path):
                console.print(Panel(
                    f"[red]Surface file not found:[/red] {surf_path}\n\n"
                    "Make sure [italic]subjects_dir[/italic] contains an [italic]fsaverage/[/italic] folder.",
                    title="[bold red]Error[/bold red]", box=box.ROUNDED,
                ))
                return
            f_args += build_f_args(surf_path, contrast_dirs, overlay_threshold, h)
    except SystemExit:
        # find_glmfit_dir / find_contrast_dirs call sys.exit on error; message already printed
        return

    cmd = ['freeview'] + f_args + ['-viewport', '3d']
    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")
    subprocess.run(cmd, check=False)


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

MENU = [
    ('1', 'Preprocess patients',  preprocessing_flow),
    ('2', 'Run group analysis',   analysis_flow),
    ('3', 'Visualize results',    visualize_flow),
    ('q', 'Quit',                 None),
]


def main() -> None:
    console.print(Panel(
        "[bold]Welcome to the PETSurfer Pipeline[/bold]\n\n"
        "This tool guides you step by step through the tau PET analysis pipeline.\n"
        "Run the steps in order: [cyan]Preprocess[/cyan] → [cyan]Analyse[/cyan] → [cyan]Visualize[/cyan].",
        title="PETSurfer",
        box=box.DOUBLE_EDGE,
        padding=(1, 4),
    ))

    while True:
        console.print("\nWhat would you like to do?\n")
        for key, label, _ in MENU:
            console.print(f"  [bold cyan]{key}[/bold cyan]  {label}")

        choice = Prompt.ask("\nEnter your choice", choices=[k for k, _, _ in MENU])

        if choice == 'q':
            console.print("\nGoodbye!")
            break

        fn = next(fn for k, _, fn in MENU if k == choice)
        console.print()
        fn()


if __name__ == '__main__':
    main()
