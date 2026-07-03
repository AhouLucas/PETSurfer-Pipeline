# Start here

Welcome! This guide walks you through running the tau PET analysis pipeline from
start to finish. **You do not need to know how to program.** A guided tool asks
you a few questions and does the work for you.

## The big picture

The pipeline has **three steps**, always run in this order:

```
   1. Preprocess   →   2. Analyse   →   3. Visualize
   (per patient)       (whole group)     (look at results)
```

1. **Preprocess** — cleans up and prepares each patient's PET scan.
2. **Analyse** — compares groups of patients statistically.
3. **Visualize** — shows the results as coloured maps on a 3-D brain.

You will use the same guided tool for all three steps. Each one is described on
its own page in this guide.

## What has already been set up for you

An administrator has already installed and configured everything technical on
the shared computer:

- FreeSurfer / PETSurfer software,
- the Python environment for this tool,
- the earlier processing steps for each patient (`recon-all` and coregistration).

!!! tip "Quick check that the machine is ready"
    Open a terminal (the next page shows how) and type:

    ```bash
    echo $FREESURFER_HOME
    ```

    If it prints a folder path, FreeSurfer is set up. If it prints an empty line,
    **contact your administrator** before continuing.

## What you provide

You only need to prepare two kinds of files:

- an **Excel patient list** (who to include, and their group/age/etc.),
- one or more **contrast matrices** (`.mtx`) describing the comparisons you want.

The next page shows exactly what these files look like and how to organise them.

[:octicons-arrow-right-24: Prepare your files](01-prepare-files.md)
