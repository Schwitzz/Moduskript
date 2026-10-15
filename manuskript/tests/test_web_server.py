#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Tests for Chunk 6: Web Server integration, commingled file structure, background
execution settings, and live external change reload."""

import os
import sys
from pathlib import Path

from manuskript.enums import Outline
from manuskript.web_server import (
    WebServerConfig,
    WebServerManager,
    ensure_commingled_project_markers,
    project_folder_signature,
)


def test_web_server_config_and_settings_page(MWSampleProject):
    MW = MWSampleProject
    MW.actSettings.triggered.emit()
    SW = MW.sw
    SW.hide()

    # Navigate to Web Server & Sync settings page
    SW.setTab("WebServer")
    assert SW.lstMenu.currentRow() == 9

    page = SW.webServerPage
    page.chkStartOnLaunch.setChecked(True)
    assert WebServerConfig.startOnLaunch() is True
    page.chkStartOnLaunch.setChecked(False)
    assert WebServerConfig.startOnLaunch() is False

    page.chkRunInBackground.setChecked(True)
    assert WebServerConfig.runInBackgroundOnClose() is True
    page.chkRunInBackground.setChecked(False)
    assert WebServerConfig.runInBackgroundOnClose() is False
    page.chkRunInBackground.setChecked(True)

    page.spnPort.setValue(8779)
    assert WebServerConfig.port() == 8779
    page.spnPort.setValue(8770)


def test_commingled_project_markers_and_external_web_edit_reload(MWSampleProject, tmp_path):
    MW = MWSampleProject
    shared_dir = tmp_path / "data" / "projects"
    shared_dir.mkdir(parents=True)

    # 1. Simulate a project created in the Web App (has <Name>/MANUSKRIPT, no <Name>.msk yet)
    web_proj = shared_dir / "web-novel"
    web_proj.mkdir()
    (web_proj / "MANUSKRIPT").write_text("1", encoding="utf8")
    (web_proj / "infos.txt").write_text("Title:          Web Novel\n", encoding="utf8")

    # Sync markers: should create web-novel.msk so Desktop can open it directly
    found = ensure_commingled_project_markers(shared_dir)
    assert str(shared_dir / "web-novel.msk") in found
    assert (shared_dir / "web-novel.msk").exists()

    # 2. Test live external change detection when Web App edits the open project on disk
    # Ensure the .msk marker file is persisted on disk before external modification
    MW.saveDatas()
    project_folder = Path(MW.currentProject[:-4])
    sig_before = project_folder_signature(MW.currentProject)
    assert sig_before != ""

    web_server_dir = Path("/home/ab/workspaces/manuskript-ai-web/server")
    if web_server_dir.exists():
        sys.path.insert(0, str(web_server_dir))
        try:
            from msklib.project import Project
            p = Project.load(project_folder)
            first_scene = next(i for i in p.outline.walk() if not i.is_folder)
            scene_id = first_scene.id
            first_scene.text = "Edited from Web App while open in Desktop."
            p.save()
        finally:
            sys.path.remove(str(web_server_dir))

        sig_after = project_folder_signature(MW.currentProject)
        assert sig_after != sig_before

        # Trigger Desktop's periodic disk check -> reloads cleanly when projectDirty is False
        MW.projectDirty = False
        MW._checkExternalProjectChanges()
        reloaded = MW.mdlOutline.getItemByID(str(scene_id))
        assert reloaded.data(Outline.text) == "Edited from Web App while open in Desktop."


def test_web_server_manager_start_health_and_stop(tmp_path):
    web_repo = Path("/home/ab/workspaces/manuskript-ai-web")
    if not (web_repo / "server").is_dir():
        return

    old_port = WebServerConfig.port()
    old_data = WebServerConfig.dataDir()
    try:
        WebServerConfig.setPort(8791)
        # Simulate user choosing a single project folder directly (Bug #1 scenario):
        # e.g. /tmp/.../my_custom_folder/EpicNovel (containing infos.txt and outline/)
        custom_parent = tmp_path / "my_custom_folder"
        single_proj = custom_parent / "EpicNovel"
        (single_proj / "outline").mkdir(parents=True)
        (single_proj / "infos.txt").write_text("Title:          Epic Novel\n", encoding="utf8")

        WebServerConfig.setDataDir(str(single_proj))
        assert WebServerConfig.sharedProjectsDir() == str(custom_parent)

        mgr = WebServerManager()
        started = mgr.start(wait_ready=True, timeout=10.0)
        assert started is True
        assert mgr.isRunning() is True

        # Create an account on the running server and verify /api/projects lists "EpicNovel"!
        import requests
        s = requests.Session()
        r_setup = s.post(
            "http://127.0.0.1:8791/api/auth/setup",
            headers={"x-allow-local-signup": "1"},
            json={"username": "tester", "password": "correct horse battery"},
            timeout=5,
        )
        assert r_setup.status_code == 200
        r_projs = s.get("http://127.0.0.1:8791/api/projects", timeout=5)
        assert r_projs.status_code == 200
        proj_names = [p["name"] for p in r_projs.json()["projects"]]
        assert "EpicNovel" in proj_names

        stopped = mgr.stop()
        assert stopped is True
        assert mgr.isRunning() is False
    finally:
        WebServerConfig.setPort(old_port)
        WebServerConfig.setDataDir(old_data)
