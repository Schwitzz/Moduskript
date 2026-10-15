#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Tests for the Desktop Native Whiteboard (`WhiteboardView`) and `whiteboards.json` load/save parity."""

import json
import os
import sys
from pathlib import Path

from manuskript.ui.views.whiteboardView import (
    EdgeGraphicsItem,
    LINE_TYPES,
    NoteGraphicsItem,
    ShapeGraphicsItem,
    WHITEBOARD_COLORS,
    WhiteboardView,
)


def test_whiteboard_defaults():
    wb = WhiteboardView()
    data = wb.toDict()
    assert data["active_board_id"] == "default"
    assert len(data["boards"]) == 1
    assert data["boards"][0]["name"] == "Main Board"
    assert data["boards"][0]["nodes"] == []
    assert data["boards"][0]["edges"] == []
    assert [lt[0] for lt in LINE_TYPES] == ["solid", "dash", "dot", "solid-dashed"]
    assert WHITEBOARD_COLORS[0] == ("default", "Theme Accent", "")


def test_whiteboard_shapes_notes_edges_and_colors():
    wb = WhiteboardView()

    # Add a rectangle shape (starts with blank label by default)
    s1 = wb.addNode("shape", "", "rectangle")
    assert isinstance(s1, ShapeGraphicsItem)
    assert s1.label == ""
    assert s1.shape_kind == "rectangle"

    # Edit label, note, and color via inspector/toolbar methods
    wb.txtShapeLabel.setText("Protagonist")
    wb._onInspectorLabelEdited("Protagonist")
    wb.txtShapeNote.setText("Secretly the heir")
    wb._onInspectorNoteEdited("Secretly the heir")
    wb.selectColor("#ef4444")

    assert s1.label == "Protagonist"
    assert s1.note == "Secretly the heir"
    assert s1.color == "#ef4444"

    # Toggle show all notes
    wb.toggleShowAllNotes()
    assert wb.show_all_notes is True
    assert s1.data["showNotes"] is True

    # Add a circle shape and link them via connection mode with solid-dashed emerald line
    s2 = wb.addNode("shape", "", "circle")
    wb.selectColor("#22c55e")
    wb.selectLineType("solid-dashed")
    assert wb.connection_mode is True

    wb.handleConnectionNodeClick(s1)
    wb.handleConnectionNodeClick(s2)

    assert len(wb._edge_items) == 1
    edge = wb._edge_items[0]
    assert isinstance(edge, EdgeGraphicsItem)
    assert edge.line_type == "solid-dashed"
    assert edge.color == "#22c55e"

    # Select the edge and switch line styles + color
    wb.scene.clearSelection()
    edge.setSelected(True)
    wb.selectLineType("dash")
    assert edge.line_type == "dash"
    wb.selectLineType("dot")
    assert edge.line_type == "dot"
    assert wb.btnAddNode.text() == ""
    assert not wb.btnAddNode.icon().isNull()
    assert wb.btnDelete.text() == ""
    assert not wb.btnDelete.icon().isNull()
    assert wb.btnShowNotes.text() == ""
    assert not wb.btnShowNotes.icon().isNull()

    # Add a third node and connect by dragging directly from s2's right handle onto s3!
    s3 = wb.addNode("shape", "Antagonist", "triangle")
    assert s2.handleAtLocalPos(s2.rightHandlePos()) == "right"
    assert s2.handleAtLocalPos(s2.leftHandlePos()) == "left"
    wb.startHandleDragConnection(s2, "right", s2.rightHandleScenePos())
    assert wb._drag_line_item is not None
    target_center = s3.mapToScene(s3.nodeRect().center())
    wb.updateHandleDragConnection(target_center)
    wb.finishHandleDragConnection(s2, "right", target_center)
    assert wb._drag_line_item is None
    assert len(wb._edge_items) == 2
    assert wb._edge_items[1].source_item == s2
    assert wb._edge_items[1].target_item == s3


def test_multiple_whiteboards_crud():
    wb = WhiteboardView()
    wb.addNode("shape", "Hero", "rectangle")
    assert len(wb._node_items) == 1

    # Create second board
    b2_id = wb.createNewBoard("Subplot Map")
    assert wb.active_board_id == b2_id
    assert len(wb.boards) == 2
    assert len(wb._node_items) == 0

    note_item = wb.addNode("note", "Clue #1")
    assert isinstance(note_item, NoteGraphicsItem)
    assert len(wb._node_items) == 1

    # Rename second board
    wb.renameActiveBoard("Act II Board")
    assert wb.cmbBoards.currentText() == "Act II Board"

    # Switch back to Main Board
    wb.switchBoard("default")
    assert wb.active_board_id == "default"
    assert len(wb._node_items) == 1
    first_node = list(wb._node_items.values())[0]
    assert first_node.label == "Hero"

    # Switch to Act II Board and delete it
    wb.switchBoard(b2_id)
    wb.deleteActiveBoard()
    assert len(wb.boards) == 1
    assert wb.active_board_id == "default"


def test_project_load_save_whiteboards_and_web_msklib_parity(MWSampleProject):
    MW = MWSampleProject
    assert hasattr(MW, "whiteboardView")
    wb = MW.whiteboardView

    # Populate Main Board and a second board in Desktop
    n1 = wb.addNode("shape", "Desktop Node", "triangle")
    wb.selectColor("#a855f7")
    wb.patchNodeData(n1.node_id, {"note": "Created in desktop PyQt5"})

    b2 = wb.createNewBoard("World Map")
    n2 = wb.addNode("note", "Continent overview")
    wb.selectColor("#14b8a6")

    # Save project from Desktop Manuskript
    MW.saveDatas()

    project_folder = Path(MW.currentProject[:-4])
    wb_file = project_folder / "whiteboards.json"
    assert wb_file.exists()

    saved_data = json.loads(wb_file.read_text(encoding="utf8"))
    assert saved_data["active_board_id"] == b2
    assert len(saved_data["boards"]) == 2
    assert saved_data["boards"][0]["nodes"][0]["data"]["label"] == "Desktop Node"
    assert saved_data["boards"][0]["nodes"][0]["data"]["color"] == "#a855f7"
    assert saved_data["boards"][1]["name"] == "World Map"

    # Reload project in Desktop and verify everything restores
    MW.loadProject(MW.currentProject)
    assert MW.whiteboardView.active_board_id == b2
    assert len(MW.whiteboardView.boards) == 2
    MW.whiteboardView.switchBoard("default")
    restored_node = list(MW.whiteboardView._node_items.values())[0]
    assert restored_node.label == "Desktop Node"
    assert restored_node.color == "#a855f7"
    assert restored_node.note == "Created in desktop PyQt5"

    # Cross-check with Web msklib if available in sibling repo
    web_server_dir = Path("/home/ab/workspaces/manuskript-ai-web/server")
    if web_server_dir.exists():
        sys.path.insert(0, str(web_server_dir))
        try:
            from msklib.project import Project
            p = Project.load(project_folder)
            assert "whiteboards.json" in p.files
            parsed_from_msklib = json.loads(p.files["whiteboards.json"])
            assert parsed_from_msklib["boards"][0]["nodes"][0]["data"]["label"] == "Desktop Node"
        finally:
            sys.path.remove(str(web_server_dir))
