# GUI 🎨

The PySide6 GUI is the primary interface in the packaged Windows distribution. Download and extract the complete portable artifact, then run `usdopt-gui.cmd`.

## Workflow

1. Choose, type, paste, or drop a local `.usd`, `.usda`, or `.usdc` stage.
2. Press Enter or leave the input field to populate the permanent **Scene** and **Diagnostics** tabs.
3. Optionally select one or more prims in **Scene**. Each selected prim and all of its descendants become the workflow scope; no selection means the entire stage.
4. Choose **Safe Cleanup**, **Geometry Optimization**, or **Find Overlaps**.
5. Review the workflow description, operation list, scope, skipped-operation markers, and output path.
6. Select **Run**.
7. Inspect the log or structured analysis results.

The last committed input and output paths are restored on the next launch. No recent-file history or custom operation profiles are stored.

## Reviewed workflows

### Safe Cleanup (`safe_publish`)

Creates a separate USD derivative. Whole-stage runs recompute extents and reduce redundant primvar, material, and exact duplicate time-sample data. Prim-scoped runs omit material deduplication because NVIDIA's operation can rebind material consumers outside the selected hierarchy; the scope label, operation list, worker log, and report warning disclose that omission. The workflow does not expose hierarchy-flattening, topology-changing, deletion, or GPU-dependent operations.

### Geometry Optimization (`geometry_optimization`)

Creates a separate USD derivative using only `computeExtents` and conservative `optimizePrimvars` settings. It is intended for focused geometry-data optimization and supports whole-stage or selected-prim hierarchy scope without skipped operations.

### Automatic Inspect Stage (`diagnostics`)

Runs alongside scene-hierarchy inspection whenever an input is committed. Parsed prim counts, face counts, and vertex counts appear in the permanent **Diagnostics** tab. The automatic GUI check uses temporary report storage and does not leave files beside the source USD; the same preset remains available through the CLI when a persistent report is needed.

### Find Overlaps (`find_overlaps`)

Runs read-only overlapping-mesh analysis on the CPU for predictable hardware-independent behavior. Structured findings appear in the **Analysis** tab and are retained in the JSON report.

## Main controls

- **Input USD** — local stage path or drag-and-drop target.
- **Workflow** — Safe Cleanup, Geometry Optimization, or Find Overlaps. Its description appears directly beneath the selector.
- **Output USD** — rebuilt after the input is committed with Enter or focus loss. Typing alone does not change it; a manual path is replaced when the new input is committed.
- **Verified operations** — compact read-only list showing what the workflow runs. Operations that cannot preserve a selected hierarchy boundary are marked as skipped.
- **Scene** — permanent bounded prim hierarchy with schema types and composition indicators. Use Ctrl- or Shift-click to select multiple prims. A selected parent scopes the workflow to that prim and every descendant, including descendants omitted by display truncation. Selecting both a parent and its child records only the parent scope. **Clear selection** restores whole-stage scope.
- **Run / Cancel** — starts or interrupts the active worker process.
- **Open output folder** — opens the derivative folder after a write workflow.
- Existing outputs are confirmed only when **Run** is pressed; the form does not show an early replacement error.
- **Log** — fixed-width worker output with debug, information, warning, error, and success colors.
- **Analysis** — reviewed headings, counts, and prim-path bullets for Find Overlaps. Unreviewed result shapes direct users to the raw JSON report.
- **Diagnostics** — permanent parsed stage statistics refreshed automatically with Scene inspection.

Reports retain the normalized selected root prim paths in `prim_paths`, the operations that actually ran in `operations`, and any scope-preservation omissions in `warnings`. An empty `prim_paths` list records a whole-stage workflow. Reports remain available as JSON files and through the `usdopt report-summary` CLI command. The GUI intentionally does not maintain a separate report-history browser.

## Shortcuts

- `Ctrl+O` — choose an input USD.
- `Ctrl+Enter` — run the current workflow when ready.
- `Esc` — cancel the active workflow.

See [operation support](operation-support.md) for the complete 47-operation classification and [development](development.md) for source setup and validation.
