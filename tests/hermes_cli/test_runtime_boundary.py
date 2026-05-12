"""Tests for source/runtime import boundary helpers."""

import sys

from drewgent_cli.runtime_boundary import ensure_source_import_precedence


def test_runtime_home_entries_are_removed_ahead_of_source_root(tmp_path):
    project_root = tmp_path / "repo"
    runtime_home = tmp_path / ".drewgent"
    project_root.mkdir()
    runtime_home.mkdir()
    path_entries = ["", str(runtime_home), str(project_root), "/usr/lib/python"]

    result = ensure_source_import_precedence(
        project_root,
        runtime_home,
        path_entries=path_entries,
        cwd=runtime_home,
    )

    assert path_entries[0] == str(project_root)
    assert "" not in path_entries
    assert str(runtime_home) not in path_entries
    assert path_entries.count(str(project_root)) == 1
    assert result["removed_runtime_entries"] == ["", str(runtime_home)]


def test_non_runtime_cwd_empty_path_entry_is_preserved_after_source_root(tmp_path):
    project_root = tmp_path / "repo"
    runtime_home = tmp_path / ".drewgent"
    workdir = tmp_path / "work"
    project_root.mkdir()
    runtime_home.mkdir()
    workdir.mkdir()
    path_entries = ["", str(runtime_home), "/usr/lib/python"]

    ensure_source_import_precedence(
        project_root,
        runtime_home,
        path_entries=path_entries,
        cwd=workdir,
    )

    assert path_entries[0] == str(project_root)
    assert "" in path_entries[1:]
    assert str(runtime_home) not in path_entries


def test_default_call_mutates_sys_path_safely(monkeypatch, tmp_path):
    project_root = tmp_path / "repo"
    runtime_home = tmp_path / ".drewgent"
    project_root.mkdir()
    runtime_home.mkdir()
    fake_sys_path = [str(runtime_home), str(project_root), "/site"]
    monkeypatch.setattr(sys, "path", fake_sys_path)

    ensure_source_import_precedence(project_root, runtime_home)

    assert sys.path == [str(project_root), "/site"]
