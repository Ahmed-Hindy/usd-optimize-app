# User & CLI Guide

## Using the GUI

Launch the app with `usdopt-gui.cmd` (portable release) or `uv run usdopt-gui` (from source).

1. **Open a stage** — Browse, paste a path, or drag and drop a `.usd`, `.usda`, or `.usdc` file into **Input USD**. Press `Enter` (or click away) to load the scene hierarchy, refresh the default output path, and run stage diagnostics. The app remembers the last committed input and output paths across launches.
2. **Set the scope (optional)** — Select one or more prims in the **Scene** tab (`Ctrl`- or `Shift`-click for multi-select) to target only those prims and all of their descendants (including any descendants truncated in the tree preview). Click **Clear selection** to target the whole stage.
3. **Choose a workflow** — Pick **Safe Cleanup**, **Geometry Optimization**, or **Find Overlaps** and review the operation list and output path. Any operation that cannot safely run on a sub-hierarchy (such as material deduplication in **Safe Cleanup**) is marked as skipped.
4. **Run** — Click **Run** (or press `Ctrl+Enter`). Existing output files prompt for confirmation before overwrite. Use **Open output folder** when a write job finishes.

### Result tabs

- **Overview** — Summary of the loaded stage, active scope, selected workflow, and latest run result.
- **Scene** — Bounded prim hierarchy with schema types and composition badges.
- **Diagnostics** — Prim, face, and vertex counts collected automatically when a stage is loaded (stored in a temporary report so source folders stay clean).
- **Analysis** — Structured mesh-overlap findings from **Find Overlaps**.
- **Log** — Color-coded live output from the optimization worker process.

### Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Browse for an input USD file |
| `Ctrl+Enter` | Run the selected workflow |
| `Esc` | Cancel the running workflow |

---

## Using the CLI

Run `.\usdopt.cmd` from the portable folder or `uv run usdopt` from a source checkout.

```powershell
# Check runtime environment and operation discovery
usdopt doctor

# Optimize a single USD stage (defaults to --preset safe_publish; use --dry-run to validate only)
usdopt optimize --input "C:\path\asset.usda" --output "C:\path\asset.opt.usda" --force

# Run a read-only overlap check and write a JSON report
usdopt optimize --input "C:\path\asset.usda" --preset find_overlaps

# Optimize multiple files into one directory
usdopt batch --input "C:\path\a.usda" --input "C:\path\b.usda" --output-dir "C:\path\out" --preset safe_publish

# Inspect available presets (add --all to include developer presets) and operations
usdopt list-presets
usdopt show-preset safe_publish
usdopt list-ops
```

### Reports

Every CLI run writes `<output>.report.json` and `<output>.log` recording the normalized `prim_paths` (empty for whole-stage runs), executed `operations`, structured `operation_results`, duration, and warnings.

To summarize a directory of JSON reports as a text table or JSON payload:

```powershell
usdopt report-summary --reports-dir reports/smoke-tests
usdopt report-summary --reports-dir reports/smoke-tests --json
```

Read-only presets (`diagnostics`, `find_overlaps`) write a report JSON without exporting a USD file, so their output file size appears as `missing` in the summary table.
