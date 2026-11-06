# User & CLI Guide

## Using the GUI

Launch the app with `usdopt-gui.cmd` (portable release) or `uv run usdopt-gui` (from source).

1. **Open a stage** — Browse, paste a path, or drag and drop a `.usd`, `.usda`, or `.usdc` file into **Input USD**. Press `Enter` (or click away) to load the scene hierarchy and run stage diagnostics.
2. **Set the scope (optional)** — Select one or more prims in the **Scene** tab (`Ctrl`- or `Shift`-click for multi-select) to target only those prims and their descendants. Click **Clear selection** to target the whole stage.
3. **Choose a workflow** — Pick **Safe Cleanup**, **Geometry Optimization**, or **Find Overlaps** and review the operation list and output path.
4. **Run** — Click **Run** (or press `Ctrl+Enter`). Use **Open output folder** when a write job finishes.

### Result tabs

- **Overview** — Summary of the loaded stage, active scope, selected workflow, and latest run result.
- **Scene** — Prim hierarchy with schema types and composition badges.
- **Diagnostics** — Prim, face, and vertex counts collected automatically when a stage is loaded.
- **Analysis** — Structured mesh-overlap findings from **Find Overlaps**.
- **Log** — Live output from the optimization worker process.

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
# Optimize a single USD stage (defaults to --preset safe_publish)
usdopt optimize --input "C:\path\asset.usda" --output "C:\path\asset.opt.usda" --force

# Run a read-only overlap check and write a JSON report
usdopt optimize --input "C:\path\asset.usda" --preset find_overlaps

# Optimize multiple files into one directory
usdopt batch --input "C:\path\a.usda" --input "C:\path\b.usda" --output-dir "C:\path\out" --preset safe_publish

# Inspect available presets and operations
usdopt list-presets
usdopt show-preset safe_publish
usdopt list-ops
```

### Reports

Every CLI run writes a `<output>.report.json` and `<output>.log` next to the output file, recording the selected `prim_paths`, executed `operations`, timing, and any warnings.

To summarize a directory of JSON reports as a table or JSON payload:

```powershell
usdopt report-summary --reports-dir reports/smoke-tests
usdopt report-summary --reports-dir reports/smoke-tests --json
```
