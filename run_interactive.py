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
from datetime import datetime
from pathlib import Path

from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import PathCompleter

# Allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from rich import box
from rich.console import Console
from rich.panel import Panel

from utils.config import DEFAULT_DATA_DIR, DEFAULT_SUBJECTS_DIR

console = Console()

DEFAULT_SUBJECTS_TEMPLATE = 'YASMINE_TAU_%d_%s'


# ---------------------------------------------------------------------------
# Input helpers — all use prompt_toolkit so backspace/Ctrl+C behave correctly
# ---------------------------------------------------------------------------

def ask_path(prompt_text: str, must_exist: bool = True, is_file: bool = True,
             default: str | None = None) -> str:
    """Ask for a filesystem path with tab-completion; re-prompt if it doesn't exist."""
    completer = PathCompleter(expanduser=True)
    default_hint = f" (default: {default})" if default else ""

    while True:
        value = pt_prompt(f"{prompt_text}{default_hint}: ", completer=completer)
        if not value:
            if default:
                value = default
            else:
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


def ask_confirm(prompt_text: str, default: bool = True) -> bool:
    """Ask a yes/no question; returns True for yes, False for no."""
    hint = "[Y/n]" if default else "[y/N]"
    default_hint = f" (default: {'y' if default else 'n'})"
    while True:
        value = pt_prompt(f"{prompt_text}{default_hint} {hint}: ").strip().lower()
        if not value:
            return default
        if value in ('y', 'yes'):
            return True
        if value in ('n', 'no'):
            return False
        console.print("[red]Please enter y or n.[/red]")


def ask_choice(prompt_text: str, choices: list[str], default: str | None = None) -> str:
    """Ask the user to pick one of several choices."""
    hint = f"[{'/'.join(choices)}]"
    default_hint = f" (default: {default})" if default is not None else ""
    while True:
        value = pt_prompt(f"{prompt_text}{default_hint} {hint}: ").strip().lower()
        if not value and default is not None:
            return default
        if value in choices:
            return value
        console.print(f"[red]Please enter one of: {', '.join(choices)}[/red]")


def ask_text(prompt_text: str, default: str = "") -> str:
    """Ask for a free-text value with an optional default."""
    default_hint = f" (default: {default})" if default else " (or press Enter to skip)"
    value = pt_prompt(f"{prompt_text}{default_hint}: ").strip()
    return value or default


class _ErrorCapture(logging.Handler):
    """Attaches to a logger to capture the most recent ERROR-level message."""
    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.last_error: str | None = None

    def emit(self, record: logging.LogRecord) -> None:
        self.last_error = record.getMessage()


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
    force = ask_confirm("Force recompute even if output files already exist?", default=False)

    summary = (
        f"[bold]Patient list:[/bold]        {excel_path}\n"
        f"[bold]Subjects directory:[/bold]  {subjects_dir}\n"
        f"[bold]PET data directory:[/bold]  {data_dir}\n"
        f"[bold]Force recompute:[/bold]     {'Yes' if force else 'No'}"
    )
    console.print(Panel(summary, title="[bold green]Ready to preprocess[/bold green]", box=box.ROUNDED))

    if not ask_confirm("Proceed?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    from utils.config import add_common_args, build_config
    from utils.utils import setup_logger
    from steps.gtmpvc import run_gtmpvc_patient
    from steps.vol2surf import run_vol2surf_patient

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(os.path.dirname(os.path.abspath(excel_path)), f'pipeline_{ts}.log')
    logger = setup_logger('petsurfer', log_file, file_mode='w')
    capture = _ErrorCapture()
    logger.addHandler(capture)

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
            ok = run_gtmpvc_patient(config, patient_id, timestamp, logger)
            if ok:
                run_vol2surf_patient(config, patient_id, timestamp, logger)
            else:
                logger.warning(
                    '[SKIPPED] vol2surf — patient %s / %s — gtmpvc did not succeed',
                    patient_id, timestamp,
                )
    except Exception as e:
        detail = capture.last_error or str(e) or "An unexpected error occurred."
        console.print(Panel(
            f"[red]{detail}[/red]\n\nSee the log file for details: {log_file}",
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
    xlsx = (sorted(Path(analysis_dir).glob('*.xlsx'))
            + sorted(Path(analysis_dir).glob('*.xls'))
            + sorted(Path(analysis_dir).glob('*.ods')))
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
    fwhm_str = ask_text("Surface smoothing kernel size (mm)", default="5")

    # Advanced settings
    design = 'dods'
    mean_center = False
    default_var: str | None = None

    if ask_confirm("\nConfigure advanced settings? (GLM design, mean-centering, default variable)", default=False):
        console.print(
            "\n[bold]Design type[/bold]\n"
            "  [cyan]dods[/cyan]  Each group gets its own slope — more flexible, recommended when unsure.\n"
            "  [cyan]doss[/cyan]  Groups share a common slope — simpler, fewer parameters.\n"
        )
        design = ask_choice("Design type", choices=['dods', 'doss'], default='dods')

        console.print(
            "\n[bold]Mean-centering[/bold]\n"
            "  Subtracts the group mean from continuous variables (e.g. age, MMSE).\n"
            "  Makes the intercept more interpretable. Usually recommended.\n"
        )
        mean_center = ask_confirm("Mean-center continuous variables?", default=False)

        console.print(
            "\n[bold]Default variable[/bold]\n"
            "  Which continuous variable freeview highlights by default.\n"
        )
        dv = ask_text("Default variable name")
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

    if not ask_confirm("Proceed?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    from run_analysis import run_analysis, setup_analysis_logger

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

    logger, log_path = setup_analysis_logger(analysis_dir)
    capture = _ErrorCapture()
    logger.addHandler(capture)

    try:
        run_analysis(args, logger)
    except SystemExit as e:
        if e.code != 0:
            detail = capture.last_error or "Analysis failed."
            console.print(Panel(
                f"[red]{detail}[/red]\n\nSee the log file for details: {log_path}",
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
        detail = capture.last_error or "An unexpected error occurred."
        console.print(Panel(
            f"[red]{detail}[/red]\n\nSee the log file for details: {log_path}",
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
        "Subjects directory (must contain an fsaverage/ folder)",
        must_exist=True, is_file=False,
        default=DEFAULT_SUBJECTS_DIR,
    )

    hemi_choice = ask_choice(
        "Which hemisphere to display?",
        choices=['both', 'lh', 'rh'],
        default='both',
    )
    hemi: str | None = None if hemi_choice == 'both' else hemi_choice

    overlay_threshold = ask_text(
        "Overlay threshold MIN,MAX  (values below MIN are hidden; above MAX are fully colored)",
        default='2,5',
    )

    contrast_input = ask_text("Single contrast to show")
    contrast: str | None = contrast_input or None

    summary = (
        f"[bold]Analysis folder:[/bold]     {analysis_dir}\n"
        f"[bold]Subjects directory:[/bold]  {subjects_dir}\n"
        f"[bold]Hemisphere:[/bold]          {hemi_choice}\n"
        f"[bold]Overlay threshold:[/bold]   {overlay_threshold}\n"
        f"[bold]Contrast:[/bold]            {contrast or 'all'}"
    )
    console.print(Panel(summary, title="[bold green]Ready to visualize[/bold green]", box=box.ROUNDED))

    if not ask_confirm("Open freeview?", default=True):
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
                    "Make sure subjects_dir contains an fsaverage/ folder.",
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
        "Run the steps in order: [cyan]Preprocess[/cyan] → [cyan]Analyse[/cyan] → [cyan]Visualize[/cyan].\n\n"
        "[dim]Press Ctrl+C at any time to quit.[/dim]",
        title="PETSurfer",
        box=box.DOUBLE_EDGE,
        padding=(1, 4),
    ))

    while True:
        console.print("\nWhat would you like to do?\n")
        for key, label, _ in MENU:
            console.print(f"  [bold cyan]{key}[/bold cyan]  {label}")

        choice = ask_choice("\nEnter your choice", choices=[k for k, _, _ in MENU])

        if choice == 'q':
            console.print("\nGoodbye!")
            break

        fn = next(fn for k, _, fn in MENU if k == choice)
        console.print()
        fn()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted. Goodbye![/yellow]")
        sys.exit(0)
