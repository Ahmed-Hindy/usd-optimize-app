# User & CLI Guide

## Using the GUI

Launch the app with `.\usdopt-gui.cmd` (portable release) or `uv run usdopt-gui` (from source).

1. **Open a stage** — Browse, paste a path, or drag and drop a `.usd`, `.usda`, or `.usdc` file into **Input USD**. Press `Enter` (or click away) to load the scene hierarchy, refresh the default output path, and run stage diagnostics. The app remembers the last committed input and output paths across launches.
2. **Set the scope (optional)** — Select one or more prims in the **Scene** tab (`Ctrl`- or `Shift`-click for multi-select) to target only those prims and all of their descendants (including any descendants truncated in the tree preview). Click **Clear selection** to target the whole stage.
3. **Choose a workflow** — Pick **Safe Cleanup**, **Geometry Optimization**, or **Find Overlaps** and review the operation list and output path. Any operation that cannot safely run on a sub-hierarchy (such as material deduplication in **Safe Cleanup**) is marked as skipped.
4. **Run** — Click **Run** (or press `Ctrl+Enter`). Existing output files prompt for confirmation before overwrite. Use **Open output folder** when a write job finishes.

### Result tabs

- **Overview** — Displays the loaded stage, active scope, selected workflow, latest run result, and the **Stage Statistics** table (prim counts, inactive/invisible counts, faces, and vertices collected automatically in a temporary directory when a stage is loaded).
- **Scene** — Bounded prim hierarchy with schema types and composition badges.
- **Analysis** — Appears when **Find Overlaps** produces structured mesh-overlap findings.
- **Log** — Shows startup and scope messages when a run begins, then appends the worker log tail (up to 80 lines), diagnostic output, or structured operation results once the worker process exits.

### Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Browse for an input USD file |
| `Ctrl+Enter` | Run the selected workflow |
| `Esc` | Cancel the running workflow |

---

## Using the CLI

In PowerShell, use `.\usdopt.cmd` from the extracted portable folder (or `uv run usdopt` from a source checkout):

```powershell
# Check runtime environment and operation discovery
.\usdopt.cmd doctor

# Optimize a single USD stage (defaults to --preset safe_publish; use --dry-run to validate only)
.\usdopt.cmd optimize --input "C:\path\asset.usda" --output "C:\path\asset.opt.usda" --force

# Scope optimization or analysis to specific prim hierarchies
.\usdopt.cmd optimize --input "C:\path\asset.usda" --prim-path /World/Props --prim-path /World/Hero

# Run a read-only overlap check and write a JSON report (supports --json for stdout output)
.\usdopt.cmd optimize --input "C:\path\asset.usda" --preset find_overlaps --json

# Optimize multiple files into one directory
.\usdopt.cmd batch --input "C:\path\a.usda" --input "C:\path\b.usda" --output-dir "C:\path\out" --preset safe_publish

# Inspect available presets (add --all to include developer presets) and operations
.\usdopt.cmd list-presets
.\usdopt.cmd show-preset safe_publish
.\usdopt.cmd list-ops
```

### Reports and logs

- **Write jobs** (`safe_publish`, `geometry_optimization`) write the optimized USD file, `<output>.report.json`, and `<output>.log`.
- **Read-only jobs** (`diagnostics`, `find_overlaps`) and `--dry-run` jobs write `<input_stem>.<preset>.report.json` (when `--output` is omitted for read-only presets) or `<output>.report.json` only (no USD derivative or `.log` file is written).
- **Inspection commands** (`doctor`, `list-presets`, `show-preset`, `list-ops`, `report-summary`) print to stdout without writing report or log files. Pass `--json` to `doctor`, `list-presets`, `optimize`, `batch`, or `report-summary` for machine-readable output.

Each `<output>.report.json` records the normalized `prim_paths` (empty for whole-stage runs), executed `operations`, structured `operation_results`, duration, and warnings.

To summarize a directory of JSON reports as a text table or JSON payload:

```powershell
.\usdopt.cmd report-summary --reports-dir reports/smoke-tests
.\usdopt.cmd report-summary --reports-dir reports/smoke-tests --json
```

Because read-only presets (`diagnostics`, `find_overlaps`) do not export a USD file, their output file size appears as `missing` in the summary table.
