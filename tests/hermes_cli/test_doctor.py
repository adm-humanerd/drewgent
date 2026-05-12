"""Tests for drewgent_cli.doctor architectural debt checks."""

import os
import sys
import types
from argparse import Namespace
from types import SimpleNamespace

import pytest

import drewgent_cli.doctor as doctor
import drewgent_cli.gateway as gateway_cli
from drewgent_cli import doctor as doctor_mod
from drewgent_cli.doctor import _has_provider_env_config


class TestProviderEnvDetection:
    def test_detects_openai_api_key(self):
        content = "OPENAI_BASE_URL=http://localhost:1234/v1\nOPENAI_API_KEY=***"
        assert _has_provider_env_config(content)

    def test_detects_custom_endpoint_without_openrouter_key(self):
        content = "OPENAI_BASE_URL=http://localhost:8080/v1\n"
        assert _has_provider_env_config(content)

    def test_returns_false_when_no_provider_settings(self):
        content = "TERMINAL_ENV=local\n"
        assert not _has_provider_env_config(content)


class TestDoctorToolAvailabilityOverrides:
    def test_marks_honcho_available_when_configured(self, monkeypatch):
        monkeypatch.setattr(doctor, "_honcho_is_configured_for_doctor", lambda: True)

        available, unavailable = doctor._apply_doctor_tool_availability_overrides(
            [],
            [{"name": "honcho", "env_vars": [], "tools": ["query_user_context"]}],
        )

        assert available == ["honcho"]
        assert unavailable == []

    def test_leaves_honcho_unavailable_when_not_configured(self, monkeypatch):
        monkeypatch.setattr(doctor, "_honcho_is_configured_for_doctor", lambda: False)

        honcho_entry = {"name": "honcho", "env_vars": [], "tools": ["query_user_context"]}
        available, unavailable = doctor._apply_doctor_tool_availability_overrides(
            [],
            [honcho_entry],
        )

        assert available == []
        assert unavailable == [honcho_entry]


class TestHonchoDoctorConfigDetection:
    def test_reports_configured_when_enabled_with_api_key(self, monkeypatch):
        fake_config = SimpleNamespace(enabled=True, api_key="***")

        monkeypatch.setattr(
            "plugins.memory.honcho.client.HonchoClientConfig.from_global_config",
            lambda: fake_config,
        )

        assert doctor._honcho_is_configured_for_doctor()

    def test_reports_not_configured_without_api_key(self, monkeypatch):
        fake_config = SimpleNamespace(enabled=True, api_key="")

        monkeypatch.setattr(
            "plugins.memory.honcho.client.HonchoClientConfig.from_global_config",
            lambda: fake_config,
        )

        assert not doctor._honcho_is_configured_for_doctor()


def test_run_doctor_sets_interactive_env_for_tool_checks(monkeypatch, tmp_path):
    """Doctor should present CLI-gated tools as available in CLI context."""
    project_root = tmp_path / "project"
    drewgent_home = tmp_path / ".hermes"
    project_root.mkdir()
    drewgent_home.mkdir()

    monkeypatch.setattr(doctor_mod, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(doctor_mod, "DREW_HOME", drewgent_home)
    monkeypatch.delenv("HERMES_INTERACTIVE", raising=False)

    seen = {}

    def fake_check_tool_availability(*args, **kwargs):
        seen["interactive"] = os.getenv("HERMES_INTERACTIVE")
        raise SystemExit(0)

    fake_model_tools = types.SimpleNamespace(
        check_tool_availability=fake_check_tool_availability,
        TOOLSET_REQUIREMENTS={},
    )
    monkeypatch.setitem(sys.modules, "model_tools", fake_model_tools)

    with pytest.raises(SystemExit):
        doctor_mod.run_doctor(Namespace(fix=False))

    assert seen["interactive"] == "1"


def test_check_gateway_service_linger_warns_when_disabled(monkeypatch, tmp_path, capsys):
    unit_path = tmp_path / "drewgent-gateway.service"
    unit_path.write_text("[Unit]\n")

    monkeypatch.setattr(gateway_cli, "is_linux", lambda: True)
    monkeypatch.setattr(gateway_cli, "get_systemd_unit_path", lambda: unit_path)
    monkeypatch.setattr(gateway_cli, "get_systemd_linger_status", lambda: (False, ""))

    issues = []
    doctor._check_gateway_service_linger(issues)

    out = capsys.readouterr().out
    assert "Gateway Service" in out
    assert "Systemd linger disabled" in out
    assert "loginctl enable-linger" in out
    assert issues == [
        "Enable linger for the gateway user service: sudo loginctl enable-linger $USER"
    ]


def test_check_gateway_service_linger_skips_when_service_not_installed(monkeypatch, tmp_path, capsys):
    unit_path = tmp_path / "missing.service"

    monkeypatch.setattr(gateway_cli, "is_linux", lambda: True)
    monkeypatch.setattr(gateway_cli, "get_systemd_unit_path", lambda: unit_path)

    issues = []
    doctor._check_gateway_service_linger(issues)

    out = capsys.readouterr().out
    assert out == ""
    assert issues == []


class TestStubModuleDetection:
    def test_finds_stub_file_with_stub_marker(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()
        stub_file = home / "drewgent_state.py"
        stub_file.write_text("# stub - canonical version lives in src/\ndef foo(): pass\n")

        issues = doctor.check_runtime_home_stubs(home)
        assert any("drewgent_state.py" in i and "stub" in i.lower() for i in issues)

    def test_finds_stub_file_with_canonical_version_lives_marker(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()
        stub_file = home / "drewgent_constants.py"
        stub_file.write_text("# canonical version lives in src/drewgent_constants.py\n")

        issues = doctor.check_runtime_home_stubs(home)
        assert any("drewgent_constants.py" in i and "canonical" in i.lower() for i in issues)

    def test_finds_stub_in_hermes_cli_directory(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()
        cli_dir = home / "drewgent_cli"
        cli_dir.mkdir()
        stub_file = cli_dir / "config.py"
        stub_file.write_text("# stub - do not edit\n")

        issues = doctor.check_runtime_home_stubs(home)
        assert any("drewgent_cli/config.py" in i for i in issues)

    def test_no_issues_when_no_stubs(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()
        real_file = home / "drewgent_state.py"
        real_file.write_text("def real_thing(): pass\n")

        issues = doctor.check_runtime_home_stubs(home)
        assert issues == []


class TestDeprecatedDrewgentDb:
    def test_warns_on_empty_drewgent_db(self, tmp_path):
        home = tmp_path / ".drewgent"
        home.mkdir()
        db_file = home / "drewgent.db"
        db_file.write_text("")

        issues = doctor.check_deprecated_drewgent_db(home, "~/.drewgent")
        assert any("drewgent.db" in i.lower() and "state.db" in i for i in issues)

    def test_no_warning_when_drewgent_db_does_not_exist(self, tmp_path):
        home = tmp_path / ".drewgent"
        home.mkdir()

        issues = doctor.check_deprecated_drewgent_db(home, "~/.drewgent")
        assert issues == []

    def test_no_warning_for_nonempty_drewgent_db(self, tmp_path):
        home = tmp_path / ".drewgent"
        home.mkdir()
        db_file = home / "drewgent.db"
        db_file.write_text("some content here")
        assert db_file.stat().st_size > 0

        issues = doctor.check_deprecated_drewgent_db(home, "~/.drewgent")
        assert issues == []


def test_runtime_architecture_debt_appends_all_detected_issues(monkeypatch, tmp_path):
    home = tmp_path / ".drewgent"
    home.mkdir()
    (home / "drewgent.db").write_text("")
    (home / "drewgent_state.py").write_text("# stub\n")
    (home / "agent").mkdir()

    warnings = []
    monkeypatch.setattr(doctor, "check_warn", lambda text, detail="": warnings.append(text))

    issues = []
    doctor._check_runtime_architecture_debt(home, "~/.drewgent", issues)

    assert len(issues) == 3
    assert warnings == issues
    assert any("drewgent.db" in issue for issue in issues)
    assert any("drewgent_state.py" in issue for issue in issues)
    assert any("agent/" in issue for issue in issues)


def test_fix_runtime_architecture_debt_archives_empty_drewgent_db_and_removes_empty_dirs(tmp_path):
    home = tmp_path / ".drewgent"
    home.mkdir()
    db = home / "drewgent.db"
    db.write_text("")
    agent_dir = home / "agent"
    modules_dir = home / "modules"
    agent_dir.mkdir()
    modules_dir.mkdir()

    fixed = doctor.fix_runtime_architecture_debt(home, "~/.drewgent")

    assert fixed == 3
    assert not db.exists()
    assert (home / "drewgent.db.deprecated").exists()
    assert not agent_dir.exists()
    assert not modules_dir.exists()


def test_fix_runtime_architecture_debt_preserves_nonempty_legacy_items(tmp_path):
    home = tmp_path / ".drewgent"
    home.mkdir()
    db = home / "drewgent.db"
    db.write_text("not empty")
    agent_dir = home / "agent"
    agent_dir.mkdir()
    (agent_dir / "keep.py").write_text("x = 1")

    fixed = doctor.fix_runtime_architecture_debt(home, "~/.drewgent")

    assert fixed == 0
    assert db.exists()
    assert agent_dir.exists()


def test_archive_runtime_home_stubs_moves_only_detected_stub_modules(tmp_path):
    home = tmp_path / ".drewgent"
    home.mkdir()
    top_stub = home / "drewgent_state.py"
    top_stub.write_text("# stub\n")
    real_top = home / "utils.py"
    real_top.write_text("x = 1\n")
    cli_dir = home / "drewgent_cli"
    cli_dir.mkdir()
    cli_stub = cli_dir / "config.py"
    cli_stub.write_text("# canonical version lives in source\n")
    cli_real = cli_dir / "real.py"
    cli_real.write_text("x = 2\n")

    moved = doctor.archive_runtime_home_stubs(home, "~/.drewgent")

    assert moved == 2
    assert not top_stub.exists()
    assert not cli_stub.exists()
    assert real_top.exists()
    assert cli_real.exists()
    archive_root = home / "P6-prefrontal" / "archive" / "runtime-stubs"
    assert (archive_root / "drewgent_state.py").exists()
    assert (archive_root / "drewgent_cli" / "config.py").exists()


class TestEmptyLegacyDirectories:
    def test_warns_on_empty_legacy_agent_dir(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()
        agent_dir = home / "agent"
        agent_dir.mkdir()

        issues = doctor.check_empty_legacy_dirs(home)
        assert any("agent/" in i for i in issues)

    def test_warns_on_empty_legacy_modules_dir(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()
        modules_dir = home / "modules"
        modules_dir.mkdir()

        issues = doctor.check_empty_legacy_dirs(home)
        assert any("modules/" in i for i in issues)

    def test_no_warning_for_nonempty_legacy_agent_dir(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()
        agent_dir = home / "agent"
        agent_dir.mkdir()
        (agent_dir / "something.py").write_text("x = 1")

        issues = doctor.check_empty_legacy_dirs(home)
        assert not any("agent/" in i for i in issues)

    def test_no_warning_for_nonempty_legacy_modules_dir(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()
        modules_dir = home / "modules"
        modules_dir.mkdir()
        (modules_dir / "util.py").write_text("x = 2")

        issues = doctor.check_empty_legacy_dirs(home)
        assert not any("modules/" in i for i in issues)

    def test_no_warning_when_legacy_dirs_do_not_exist(self, tmp_path):
        home = tmp_path / ".hermes"
        home.mkdir()

        issues = doctor.check_empty_legacy_dirs(home)
        assert issues == []
