"""Qt helpers for rendering inspected USD scene hierarchies."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem

from usd_optimize_app.backend import SceneGraphNode
from usd_optimize_app.operation_scope import normalize_prim_paths


def configure_scene_tree(tree: QTreeWidget) -> None:
    """Configure a two-column read-only scene hierarchy tree."""
    tree.setColumnCount(2)
    tree.setHeaderLabels(("Prim", "Type"))
    tree.setAlternatingRowColors(True)
    tree.setUniformRowHeights(True)
    tree.setRootIsDecorated(True)
    tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)


def populate_scene_tree(tree: QTreeWidget, roots: tuple[SceneGraphNode, ...]) -> None:
    """Replace the tree contents with one inspected USD hierarchy."""
    tree.clear()
    for root in roots:
        tree.addTopLevelItem(_build_item(root))
    tree.expandToDepth(1)


def selected_prim_paths(tree: QTreeWidget) -> tuple[str, ...]:
    """Return USD paths stored on the currently selected hierarchy items."""
    paths = []
    for item in tree.selectedItems():
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(path, str) and path:
            paths.append(path)
    return normalize_prim_paths(paths)


def filter_scene_tree(tree: QTreeWidget, query: str) -> None:
    """Show prims matching a case-insensitive name or path query and their ancestors."""
    needle = query.strip().lower()
    for index in range(tree.topLevelItemCount()):
        _filter_item(tree.topLevelItem(index), needle)


def _filter_item(item: QTreeWidgetItem, needle: str) -> bool:
    child_matches = False
    for index in range(item.childCount()):
        if _filter_item(item.child(index), needle):
            child_matches = True

    if not needle:
        item.setHidden(False)
        return True

    prim_name = item.text(0).lower()
    prim_path = str(item.data(0, Qt.ItemDataRole.UserRole) or "").lower()
    self_matches = needle in prim_name or needle in prim_path
    visible = self_matches or child_matches
    item.setHidden(not visible)
    if child_matches:
        item.setExpanded(True)
    return visible


def _build_item(node: SceneGraphNode) -> QTreeWidgetItem:
    item = QTreeWidgetItem((node.name or node.path, node.type_name))
    item.setData(0, Qt.ItemDataRole.UserRole, node.path)

    markers = []
    if node.has_payload:
        markers.append("payload")
    if node.has_references:
        markers.append("reference")
    if node.is_instance:
        markers.append("instance")
    if not node.is_active:
        markers.append("inactive")
    if not node.is_loaded:
        markers.append("unloaded")
    marker_text = f"\nComposition: {', '.join(markers)}" if markers else ""
    item.setToolTip(0, f"{node.path}{marker_text}")
    item.setToolTip(1, node.type_name)

    for child in node.children:
        item.addChild(_build_item(child))
    return item
