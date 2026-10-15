#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Tests for Chunk 3: Desktop Outline parity with Web App (Chapters, indented Scenes,
Associated Notes, Tree/Table view toggle, and lossless MMD round-trip with msklib)."""

import sys
from pathlib import Path

from manuskript.enums import Outline
from manuskript.functions.outlineHelpers import (
    add_associated_note,
    delete_associated_note,
    is_chapter_item,
    parse_associated_notes,
    sibling_depth_offset,
    update_associated_note,
)


def test_associated_notes_crud_and_inspector(MWSampleProject):
    MW = MWSampleProject
    view = MW.treeOutlineOutline
    root = MW.mdlOutline.rootItem
    first_folder = root.children()[0]
    first_scene = first_folder.children()[0]

    # Select first scene in the outline (setCurrentIndex triggers selectionChanged automatically)
    scene_idx = MW.mdlOutline.indexFromItem(first_scene)
    view.setCurrentIndex(scene_idx)

    # Add two associated notes via the inspector widget
    n1 = MW.outlineItemEditor.associatedNotes.addNote("Plot clue", "The butler left a muddy footprint.")
    n2 = MW.outlineItemEditor.associatedNotes.addNote("Pacing", "Keep dialogue brisk.")
    assert n1 is not None and n2 is not None

    notes = parse_associated_notes(first_scene.data(Outline.associatedNotes))
    assert len(notes) == 2
    assert notes[0]["title"] == "Plot clue"
    assert notes[0]["text"] == "The butler left a muddy footprint."

    # Update first note and delete second note
    update_associated_note(first_scene, n1["id"], title="Updated clue", text="Footprint by the study.")
    delete_associated_note(first_scene, n2["id"])

    notes_after = parse_associated_notes(first_scene.data(Outline.associatedNotes))
    assert len(notes_after) == 1
    assert notes_after[0]["title"] == "Updated clue"
    assert notes_after[0]["text"] == "Footprint by the study."

    # Also verify chapters/folders support associated notes
    folder_note = add_associated_note(first_folder, "Chapter arc", "Rising tension across the act.")
    assert folder_note is not None
    assert len(parse_associated_notes(first_folder.data(Outline.associatedNotes))) == 1


def test_chapters_as_md_and_scenes_indent_under_chapters(MWSampleProject):
    MW = MWSampleProject
    view = MW.treeOutlineOutline
    root = MW.mdlOutline.rootItem
    first_folder = root.children()[0]

    # Select the folder and add a Chapter (.md with Chapter label)
    view.setCurrentIndex(MW.mdlOutline.indexFromItem(first_folder))
    ch_A = view.addChapter("Chapter A")
    assert ch_A.isMD()
    assert is_chapter_item(ch_A, MW.mdlLabels)
    assert sibling_depth_offset(ch_A, MW.mdlLabels) == 0

    # With Chapter A selected, add two scenes -> they place right after Chapter A and visually indent (offset 1)
    view.setCurrentIndex(MW.mdlOutline.indexFromItem(ch_A))
    sc_1 = view.addScene("Scene A1")
    sc_2 = view.addScene("Scene A2")
    assert sc_1.isMD() and sc_2.isMD()
    assert sc_1.parent() == ch_A.parent()
    assert sc_1.row() == ch_A.row() + 1
    assert sc_2.row() == ch_A.row() + 2
    assert sibling_depth_offset(sc_1, MW.mdlLabels) == 1
    assert sibling_depth_offset(sc_2, MW.mdlLabels) == 1

    # With Chapter A selected, adding a new Chapter B places it AFTER Scene A1 and Scene A2
    view.setCurrentIndex(MW.mdlOutline.indexFromItem(ch_A))
    ch_B = view.addChapter("Chapter B")
    assert is_chapter_item(ch_B, MW.mdlLabels)
    assert ch_B.row() == sc_2.row() + 1
    assert sibling_depth_offset(ch_B, MW.mdlLabels) == 0


def test_tree_table_mode_toggle_and_no_inline_notes_column(MWSampleProject):
    MW = MWSampleProject
    view = MW.treeOutlineOutline

    # In table mode, Notes column is hidden while Title and Summary are shown
    view.setViewMode("table")
    assert not view.isColumnHidden(Outline.title)
    assert view.isColumnHidden(Outline.notes)

    # In tree mode, only Title column is shown and header is hidden
    view.setViewMode("tree")
    assert not view.isColumnHidden(Outline.title)
    assert view.isColumnHidden(Outline.wordCount)
    assert view.isColumnHidden(Outline.notes)

    view.setViewMode("table")


def test_associated_notes_roundtrip_between_desktop_and_web_msklib(MWSampleProject):
    MW = MWSampleProject
    root = MW.mdlOutline.rootItem
    first_folder = root.children()[0]
    first_scene = first_folder.children()[0]
    scene_id = int(first_scene.ID())

    add_associated_note(first_scene, "Web-Desktop Sync Note", "Shared via MMD header associatedNotes.")
    MW.saveDatas()

    project_folder = Path(MW.currentProject[:-4])

    # Verify msklib reads the associatedNotes saved by Desktop Manuskript
    web_server_dir = Path("/home/ab/workspaces/manuskript-ai-web/server")
    if web_server_dir.exists():
        sys.path.insert(0, str(web_server_dir))
        try:
            from msklib.project import Project
            p = Project.load(project_folder)
            web_item = p.find(scene_id)
            assert web_item is not None
            raw = web_item.meta.get("associatedNotes", "")
            parsed = parse_associated_notes(raw)
            assert any(n["title"] == "Web-Desktop Sync Note" for n in parsed)
        finally:
            sys.path.remove(str(web_server_dir))

    # Reload in Desktop and verify associatedNotes survived
    MW.loadProject(MW.currentProject)
    reloaded_item = MW.mdlOutline.getItemByID(str(scene_id))
    reloaded_notes = parse_associated_notes(reloaded_item.data(Outline.associatedNotes))
    assert any(n["title"] == "Web-Desktop Sync Note" for n in reloaded_notes)
