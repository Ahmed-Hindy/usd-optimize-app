"""Qt helpers for rendering inspected USD scene hierarchies."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
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
    header = tree.header()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(96)
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    header_item = tree.headerItem()
    if header_item is not None:
        header_item.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_item.setTextAlignment(1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


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


def _build_item(node: SceneGraphNode) -> QTreeWidgetItem:
    item = QTreeWidgetItem((node.name or node.path, node.type_name))
    item.setData(0, Qt.ItemDataRole.UserRole, node.path)
    item.setForeground(1, QColor("#9e9a91"))

    if not node.is_active or not node.is_loaded:
        muted_color = QColor("#6f7479")
        italic_font = QFont(item.font(0))
        italic_font.setItalic(True)
        for col in (0, 1):
            item.setForeground(col, muted_color)
            item.setFont(col, italic_font)

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

