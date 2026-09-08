# USD Optimize App

A CLI/ GUI app for optimizing OpenUSD scenes.

![USD](https://img.shields.io/badge/file%20format-USD-6B5B95)
![PySide6](https://img.shields.io/badge/interface-PySide6-41CD52?logo=qt&logoColor=white)

![USD Optimize App interface showing the Safe Cleanup workflow and scene hierarchy](a.png)

## Overview

`USD Optimize App` is built around NVIDIA's `usd-optimize` runtime, with an added user-friendly CLI and GUI so you don't have to build and link it yourself. GUI workflows can target the entire stage or selected prim hierarchies.

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

## CLI

Open a terminal in the extracted folder:

```powershell
.\usdopt.cmd optimize --input "C:\path\asset.usda" --preset safe_publish
```

## More information

- [GUI guide](docs/gui.md)
- [Windows portable release](docs/windows-portable-release.md)
- [Operation support](docs/operation-support.md)
- [Reports](docs/report-summary.md)
- [Development guide](docs/development.md)

