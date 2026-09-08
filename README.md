# USD Optimize App

A Windows app for inspecting and optimizing OpenUSD scenes, powered by NVIDIA's `usd-optimize`.

![USD Optimize App interface showing the Safe Cleanup workflow and scene hierarchy](a.png)

## Get started

1. Download the Windows ZIP from [Releases](https://github.com/Ahmed-Hindy/usd-optimize-app/releases) and extract the whole folder.
2. Run `usdopt-gui.cmd`.
3. Open a USD scene, choose a workflow, and run it.

The portable app includes its runtime; no separate Python installation is needed.

## Workflows

| Workflow | What it does |
| --- | --- |
| Safe Cleanup | Reduces redundant scene data while preserving hierarchy and topology. |
| Geometry Optimization | Recomputes bounds and optimizes primvar storage. |
| Inspect Stage | Shows scene statistics automatically when you open a file. |
| Find Overlaps | Finds overlapping meshes without changing the scene. |

Select prims in the Scene tree to process them and their descendants, or clear the selection to process the whole stage. Safe Cleanup skips material deduplication for selected prims to avoid affecting objects outside the selection.

## Command line

Open a terminal in the extracted folder:

```powershell
.\usdopt.cmd optimize --input "C:\path\asset.usda" --preset safe_publish
```

[GUI guide](docs/gui.md) · [Reports](docs/report-summary.md) · [Development and packaging](docs/development.md)
