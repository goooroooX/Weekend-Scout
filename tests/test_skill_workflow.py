"""Tests for generated skill structure, packaging, and install target paths."""

from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest


def _norm(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_weekend_scout_commands(text: str) -> list[str]:
    commands: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("python -m weekend_scout "):
            if current:
                commands.append(" ".join(current))
                current = []
            current.append(line.rstrip("\\").strip())
            if not raw_line.rstrip().endswith("\\"):
                commands.append(" ".join(current))
                current = []
        elif current:
            current.append(line.rstrip("\\").strip())
            if not raw_line.rstrip().endswith("\\"):
                commands.append(" ".join(current))
                current = []
    if current:
        commands.append(" ".join(current))
    return [" ".join(cmd.replace("\\", " ").split()) for cmd in commands]


def _commands_named(text: str, name: str) -> list[str]:
    return [cmd for cmd in _extract_weekend_scout_commands(text) if f"python -m weekend_scout {name} " in f"{cmd} "]


def _assert_command_with_parts(commands: list[str], *, label: str, parts: list[str]) -> None:
    for command in commands:
        if all(part in command for part in parts):
            return
    raise AssertionError(f"Missing {label} command with required parts: {parts!r}")


def test_codex_install_targets_use_agents_dir():
    from weekend_scout.__main__ import _get_install_targets
    import install.install_skill as install_skill

    assert _norm(_get_install_targets()["codex"]).endswith("/.agents/skills/weekend-scout")
    assert _norm(install_skill.INSTALL_TARGETS["codex"]).endswith("/.agents/skills/weekend-scout")


def test_main_resolve_platforms_detects_codex_from_dot_codex(tmp_path, monkeypatch):
    from weekend_scout import __main__ as main_mod

    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    monkeypatch.setattr(
        main_mod,
        "_get_platform_detection_dirs",
        lambda: {
            "claude-code": (tmp_path / ".claude",),
            "codex": (codex_home, tmp_path / ".agents"),
            "openclaw": (tmp_path / ".openclaw",),
        },
    )

    assert main_mod._resolve_platforms(None) == ["codex"]


def test_install_script_detects_codex_from_dot_codex(tmp_path, monkeypatch):
    import install.install_skill as install_skill

    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    monkeypatch.setattr(
        install_skill,
        "PLATFORM_DETECTION_DIRS",
        {
            "claude-code": (tmp_path / ".claude",),
            "codex": (codex_home, tmp_path / ".agents"),
            "openclaw": (tmp_path / ".openclaw",),
        },
    )

    assert install_skill.detect_platforms() == ["codex"]


def test_bind_runtime_commands_rewrites_weekend_scout_invocations():
    from weekend_scout.skill_install import bind_runtime_commands

    content = "python -m weekend_scout init-skill\npython -m weekend_scout send --file out.txt\n"
    rewritten = bind_runtime_commands(content, "C:/Python311/python.exe")

    assert '"C:/Python311/python.exe" -m weekend_scout init-skill' in rewritten
    assert '"C:/Python311/python.exe" -m weekend_scout send --file out.txt' in rewritten
    assert "python -m weekend_scout" not in rewritten


def test_install_script_copies_skill_with_bound_python(tmp_path, monkeypatch):
    import install.install_skill as install_skill

    source_root = tmp_path / "repo"
    target_root = tmp_path / "installed"
    source_dir = source_root / ".openclaw" / "skills" / "weekend-scout"
    source_dir.mkdir(parents=True)
    refs_dir = source_dir / "references"
    refs_dir.mkdir()
    (source_dir / "SKILL.md").write_text(
        "python -m weekend_scout init-skill\npython -m weekend_scout send --file out.txt\n",
        encoding="utf-8",
    )
    (refs_dir / "search-workflow.md").write_text(
        "python -m weekend_scout session-query --run-id test-run\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(install_skill, "SOURCE_DIRS", {"openclaw": ".openclaw/skills/weekend-scout"})
    monkeypatch.setattr(install_skill, "INSTALL_TARGETS", {"openclaw": target_root / "weekend-scout"})
    monkeypatch.setattr(install_skill.sys, "executable", "C:/Python311/python.exe")

    assert install_skill.install_platform("openclaw", source_root) is True
    installed = (target_root / "weekend-scout" / "SKILL.md").read_text(encoding="utf-8")
    installed_ref = (target_root / "weekend-scout" / "references" / "search-workflow.md").read_text(
        encoding="utf-8"
    )
    assert '"C:/Python311/python.exe" -m weekend_scout init-skill' in installed
    assert "python -m weekend_scout init-skill" not in installed
    assert '"C:/Python311/python.exe" -m weekend_scout session-query --run-id test-run' in installed_ref
    assert "python -m weekend_scout session-query" not in installed_ref


def test_install_script_with_pip_uses_detected_platforms_only(monkeypatch):
    import install.install_skill as install_skill

    commands: list[tuple[list[str], Path | None]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append((cmd, cwd))
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip"])
    monkeypatch.setattr(install_skill.sys, "executable", "C:/Python311/python.exe")

    install_skill.main()

    command_only = [cmd for cmd, _ in commands]
    assert ["C:/Python311/python.exe", "-m", "pip", "--version"] in command_only
    assert ["C:/Python311/python.exe", "-m", "ensurepip", "--upgrade", "--default-pip"] not in command_only
    assert ["C:/Python311/python.exe", "-m", "pip", "install", "."] in command_only
    assert [
        "C:/Python311/python.exe",
        "-m",
        "weekend_scout",
        "install-skill",
        "--platform",
        "openclaw",
    ] in command_only
    assert [
        "C:/Python311/python.exe",
        "-m",
        "weekend_scout",
        "install-skill",
        "--platform",
        "all",
    ] not in command_only
    assert ["C:/Python311/python.exe", "-m", "weekend_scout", "download-data"] in command_only
    assert (
        ["C:/Python311/python.exe", "-m", "weekend_scout", "install-skill", "--platform", "openclaw"],
        Path.home(),
    ) in commands
    assert (["C:/Python311/python.exe", "-m", "weekend_scout", "download-data"], Path.home()) in commands


def test_install_script_with_break_system_packages_appends_pip_flag(monkeypatch):
    import install.install_skill as install_skill

    commands: list[list[str]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append(cmd)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(
        install_skill.sys,
        "argv",
        ["install_skill.py", "--with-pip", "--break-system-packages"],
    )
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    install_skill.main()

    assert ["/usr/bin/python3", "-m", "pip", "install", ".", "--break-system-packages"] in commands


def test_install_script_runtime_only_skips_skill_copy(monkeypatch):
    import install.install_skill as install_skill

    commands: list[tuple[list[str], Path | None]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append((cmd, cwd))
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(
        install_skill,
        "detect_platforms",
        lambda: (_ for _ in ()).throw(AssertionError("detect_platforms should not be called")),
    )
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip", "--runtime-only"])
    monkeypatch.setattr(install_skill.sys, "executable", "C:/Python311/python.exe")

    install_skill.main()

    command_only = [cmd for cmd, _ in commands]
    assert ["C:/Python311/python.exe", "-m", "pip", "--version"] in command_only
    assert ["C:/Python311/python.exe", "-m", "pip", "install", "."] in command_only
    assert ["C:/Python311/python.exe", "-m", "weekend_scout", "download-data"] in command_only
    assert not any("install-skill" in cmd for cmd in command_only)
    assert (["C:/Python311/python.exe", "-m", "weekend_scout", "download-data"], Path.home()) in commands


def test_install_script_runtime_only_rejects_platform(monkeypatch, capsys):
    import install.install_skill as install_skill

    monkeypatch.setattr(
        install_skill.sys,
        "argv",
        ["install_skill.py", "--with-pip", "--runtime-only", "--platform", "openclaw"],
    )

    with pytest.raises(SystemExit) as excinfo:
        install_skill.main()

    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--runtime-only cannot be combined with --platform" in err


def test_install_script_with_dev_and_break_system_packages_appends_pip_flag(monkeypatch):
    import install.install_skill as install_skill

    commands: list[list[str]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append(cmd)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(
        install_skill.sys,
        "argv",
        ["install_skill.py", "--with-pip", "--dev", "--break-system-packages"],
    )
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    install_skill.main()

    assert ["/usr/bin/python3", "-m", "pip", "install", "-e", ".[dev]", "--break-system-packages"] in commands


def test_install_script_uninstall_without_platform_removes_existing_dirs_only(tmp_path, monkeypatch, capsys):
    import install.install_skill as install_skill

    codex_target = tmp_path / ".agents" / "skills" / "weekend-scout"
    openclaw_target = tmp_path / ".openclaw" / "skills" / "weekend-scout"
    data_dir = tmp_path / ".weekend_scout"
    codex_target.mkdir(parents=True)
    openclaw_target.mkdir(parents=True)
    data_dir.mkdir()
    (data_dir / "config.yaml").write_text("home_city: Warsaw\n", encoding="utf-8")

    monkeypatch.setattr(
        install_skill,
        "INSTALL_TARGETS",
        {
            "claude-code": tmp_path / ".claude" / "skills" / "weekend-scout",
            "codex": codex_target,
            "openclaw": openclaw_target,
        },
    )

    commands: list[tuple[list[str], Path | None]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append((cmd, cwd))
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--uninstall"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    install_skill.main()

    assert not codex_target.exists()
    assert not openclaw_target.exists()
    assert data_dir.exists()
    assert (["/usr/bin/python3", "-m", "pip", "uninstall", "-y", "weekend-scout"], Path.home()) in commands
    out = capsys.readouterr().out
    assert "codex: removed" in out
    assert "openclaw: removed" in out
    assert "claude-code" not in out


def test_install_script_uninstall_with_platform_openclaw_removes_only_that_target(tmp_path, monkeypatch):
    import install.install_skill as install_skill

    codex_target = tmp_path / ".agents" / "skills" / "weekend-scout"
    openclaw_target = tmp_path / ".openclaw" / "skills" / "weekend-scout"
    codex_target.mkdir(parents=True)
    openclaw_target.mkdir(parents=True)

    monkeypatch.setattr(
        install_skill,
        "INSTALL_TARGETS",
        {
            "claude-code": tmp_path / ".claude" / "skills" / "weekend-scout",
            "codex": codex_target,
            "openclaw": openclaw_target,
        },
    )

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--uninstall", "--platform", "openclaw"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    install_skill.main()

    assert codex_target.exists()
    assert not openclaw_target.exists()


def test_install_script_uninstall_with_platform_all_targets_all_known_dirs(tmp_path, monkeypatch):
    import install.install_skill as install_skill

    targets = {
        "claude-code": tmp_path / ".claude" / "skills" / "weekend-scout",
        "codex": tmp_path / ".agents" / "skills" / "weekend-scout",
        "openclaw": tmp_path / ".openclaw" / "skills" / "weekend-scout",
    }
    for path in targets.values():
        path.mkdir(parents=True)

    monkeypatch.setattr(install_skill, "INSTALL_TARGETS", targets)

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--uninstall", "--platform", "all"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    install_skill.main()

    assert all(not path.exists() for path in targets.values())


def test_install_script_uninstall_missing_skill_directory_is_nonfatal(tmp_path, monkeypatch, capsys):
    import install.install_skill as install_skill

    monkeypatch.setattr(
        install_skill,
        "INSTALL_TARGETS",
        {
            "claude-code": tmp_path / ".claude" / "skills" / "weekend-scout",
            "codex": tmp_path / ".agents" / "skills" / "weekend-scout",
            "openclaw": tmp_path / ".openclaw" / "skills" / "weekend-scout",
        },
    )

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        if cmd[:5] == ["/usr/bin/python3", "-m", "pip", "uninstall", "-y"]:
            return SimpleNamespace(returncode=0, stderr="", stdout="Skipping weekend-scout as it is not installed.")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--uninstall"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    install_skill.main()

    out = capsys.readouterr().out
    assert "no installed platform directories found" in out
    assert "package: weekend-scout was not installed" in out


def test_install_script_uninstall_with_break_system_packages_appends_pip_flag(monkeypatch):
    import install.install_skill as install_skill

    commands: list[list[str]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append(cmd)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(
        install_skill.sys,
        "argv",
        ["install_skill.py", "--uninstall", "--break-system-packages"],
    )
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    install_skill.main()

    assert ["/usr/bin/python3", "-m", "pip", "uninstall", "-y", "weekend-scout", "--break-system-packages"] in commands


def test_install_script_uninstall_pep_668_guidance_suggests_break_system_packages(monkeypatch, capsys):
    import install.install_skill as install_skill

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        if cmd[-2:] == ["pip", "--version"]:
            return SimpleNamespace(returncode=0, stderr="", stdout="pip 24.0")
        if cmd[:5] == ["/usr/bin/python3", "-m", "pip", "uninstall", "-y"]:
            return SimpleNamespace(
                returncode=1,
                stderr="error: externally-managed-environment\nhint: See PEP 668 for the detailed specification.",
                stdout="",
            )
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--uninstall", "--platform", "openclaw"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    with pytest.raises(SystemExit) as excinfo:
        install_skill.main()

    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "pip uninstall was blocked because this Python interpreter is externally managed (PEP 668)" in err
    assert "python install/install_skill.py --uninstall --platform openclaw --break-system-packages" in err
    assert "pip config set global.break-system-packages true" in err


def test_install_script_without_pip_requires_existing_runtime(monkeypatch, capsys):
    import install.install_skill as install_skill

    commands: list[list[str]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append(cmd)
        return SimpleNamespace(
            returncode=1,
            stderr="importlib.metadata.PackageNotFoundError: weekend-scout",
            stdout="",
        )

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py"])
    monkeypatch.setattr(install_skill.sys, "executable", "C:/Python311/python.exe")

    with pytest.raises(SystemExit) as excinfo:
        install_skill.main()

    assert excinfo.value.code == 1
    assert commands == [["C:/Python311/python.exe", "-c", install_skill._RUNTIME_CHECK_CODE]]
    err = capsys.readouterr().err
    assert "Cannot install skill files without a ready Python runtime" in err
    assert "python install/install_skill.py --with-pip" in err
    assert "python -m weekend_scout install-skill --platform ..." in err


def test_install_script_bootstraps_missing_pip_with_ensurepip(monkeypatch, capsys):
    import install.install_skill as install_skill

    commands: list[list[str]] = []
    pip_checks = {"count": 0}

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append(cmd)
        if cmd[-2:] == ["pip", "--version"]:
            pip_checks["count"] += 1
            if pip_checks["count"] == 1:
                return SimpleNamespace(returncode=1, stderr="/usr/bin/python: No module named pip", stdout="")
            return SimpleNamespace(returncode=0, stderr="", stdout="pip 24.0")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    install_skill.main()

    assert ["/usr/bin/python3", "-m", "ensurepip", "--upgrade", "--default-pip"] in commands
    assert ["/usr/bin/python3", "-m", "pip", "install", "."] in commands
    assert "bootstrapping with ensurepip" in capsys.readouterr().out


def test_install_script_fails_when_ensurepip_cannot_provide_pip(monkeypatch, capsys):
    import install.install_skill as install_skill

    commands: list[list[str]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append(cmd)
        if cmd[-2:] == ["pip", "--version"]:
            return SimpleNamespace(returncode=1, stderr="/usr/bin/python: No module named pip", stdout="")
        if cmd[2:4] == ["ensurepip", "--upgrade"]:
            return SimpleNamespace(
                returncode=1,
                stderr="/usr/bin/python: No module named ensurepip",
                stdout="",
            )
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.os, "name", "posix")
    monkeypatch.setattr(install_skill.shutil, "which", lambda name: None)
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    with pytest.raises(SystemExit) as excinfo:
        install_skill.main()

    assert excinfo.value.code == 1
    assert ["/usr/bin/python3", "-m", "ensurepip", "--upgrade", "--default-pip"] in commands
    err = capsys.readouterr().err
    assert "pip is unavailable for this Python interpreter" in err
    assert "may omit ensurepip" in err
    assert "with your Linux distribution package manager" in err
    assert "Then rerun: `python install/install_skill.py --with-pip`" in err


def test_install_script_pep_668_guidance_suggests_break_system_packages(monkeypatch, capsys):
    import install.install_skill as install_skill

    commands: list[list[str]] = []

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        commands.append(cmd)
        if cmd[-2:] == ["pip", "--version"]:
            return SimpleNamespace(returncode=0, stderr="", stdout="pip 24.0")
        if cmd[:4] == ["/usr/bin/python3", "-m", "pip", "install"]:
            return SimpleNamespace(
                returncode=1,
                stderr="error: externally-managed-environment\nhint: See PEP 668 for the detailed specification.",
                stdout="",
            )
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip", "--platform", "openclaw"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    with pytest.raises(SystemExit) as excinfo:
        install_skill.main()

    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "externally managed (PEP 668)" in err
    assert "python install/install_skill.py --with-pip --platform openclaw --break-system-packages" in err
    assert "pip config set global.break-system-packages true" in err


def test_install_script_pep_668_guidance_preserves_dev_retry_args(monkeypatch, capsys):
    import install.install_skill as install_skill

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        if cmd[-2:] == ["pip", "--version"]:
            return SimpleNamespace(returncode=0, stderr="", stdout="pip 24.0")
        if cmd[:4] == ["/usr/bin/python3", "-m", "pip", "install"]:
            return SimpleNamespace(returncode=1, stderr="externally managed", stdout="")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(
        install_skill.sys,
        "argv",
        ["install_skill.py", "--with-pip", "--dev", "--platform", "openclaw"],
    )
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    with pytest.raises(SystemExit):
        install_skill.main()

    err = capsys.readouterr().err
    assert "python install/install_skill.py --with-pip --dev --platform openclaw --break-system-packages" in err


def test_install_script_non_pep_668_pip_failure_stays_generic(monkeypatch, capsys):
    import install.install_skill as install_skill

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        if cmd[-2:] == ["pip", "--version"]:
            return SimpleNamespace(returncode=0, stderr="", stdout="pip 24.0")
        if cmd[:4] == ["/usr/bin/python3", "-m", "pip", "install"]:
            return SimpleNamespace(returncode=1, stderr="network failure", stdout="")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    with pytest.raises(SystemExit):
        install_skill.main()

    err = capsys.readouterr().err
    assert "externally managed (PEP 668)" not in err
    assert "ERROR: pip install failed. Aborting skill installation." in err


def test_install_script_suggests_apt_recovery_command(monkeypatch, capsys):
    import install.install_skill as install_skill

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        if cmd[-2:] == ["pip", "--version"]:
            return SimpleNamespace(returncode=1, stderr="/usr/bin/python: No module named pip", stdout="")
        if cmd[2:4] == ["ensurepip", "--upgrade"]:
            return SimpleNamespace(returncode=1, stderr="/usr/bin/python: No module named ensurepip", stdout="")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.os, "name", "posix")
    monkeypatch.setattr(install_skill.shutil, "which", lambda name: "/usr/bin/apt-get" if name == "apt-get" else None)
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    with pytest.raises(SystemExit):
        install_skill.main()

    err = capsys.readouterr().err
    assert "Suggested fix for this system:" in err
    assert "sudo apt update && sudo apt install python3-venv python3-pip" in err
    assert "Then rerun: `python install/install_skill.py --with-pip`" in err


def test_install_script_suggests_dnf_recovery_command(monkeypatch, capsys):
    import install.install_skill as install_skill

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        if cmd[-2:] == ["pip", "--version"]:
            return SimpleNamespace(returncode=1, stderr="/usr/bin/python: No module named pip", stdout="")
        if cmd[2:4] == ["ensurepip", "--upgrade"]:
            return SimpleNamespace(returncode=1, stderr="/usr/bin/python: No module named ensurepip", stdout="")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.os, "name", "posix")
    monkeypatch.setattr(install_skill.shutil, "which", lambda name: "/usr/bin/dnf" if name == "dnf" else None)
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip", "--dev"])
    monkeypatch.setattr(install_skill.sys, "executable", "/usr/bin/python3")

    with pytest.raises(SystemExit):
        install_skill.main()

    err = capsys.readouterr().err
    assert "sudo dnf install python3-pip python3-wheel" in err
    assert "Then rerun: `python install/install_skill.py --with-pip --dev`" in err


def test_install_script_shows_windows_recovery_guidance(monkeypatch, capsys):
    import install.install_skill as install_skill

    def fake_run(cmd, check=False, cwd=None, capture_output=False, text=False):
        if cmd[-2:] == ["pip", "--version"]:
            return SimpleNamespace(returncode=1, stderr="No module named pip", stdout="")
        if cmd[2:4] == ["ensurepip", "--upgrade"]:
            return SimpleNamespace(returncode=1, stderr="No module named ensurepip", stdout="")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(install_skill, "detect_platforms", lambda: ["openclaw"])
    monkeypatch.setattr(install_skill.os, "name", "nt")
    monkeypatch.setattr(install_skill.shutil, "which", lambda name: "C:/Windows/System32/where.exe")
    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    monkeypatch.setattr(install_skill.sys, "argv", ["install_skill.py", "--with-pip"])
    monkeypatch.setattr(install_skill.sys, "executable", "C:/Python311/python.exe")

    with pytest.raises(SystemExit):
        install_skill.main()

    err = capsys.readouterr().err
    assert "Repair or reinstall this Python installation so `pip` is included" in err
    assert "Linux distribution package manager" not in err
    assert "sudo apt update" not in err
    assert "Then rerun: `python install/install_skill.py --with-pip`" in err


def test_install_script_bootstraps_from_clean_clone_help():
    install_dir = Path("install").resolve()
    result = subprocess.run(
        [sys.executable, "-S", "install_skill.py", "--help"],
        cwd=install_dir,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Install the Weekend Scout skill or Python runtime." in result.stdout
    assert "--runtime-only" in result.stdout
    assert "--with-pip" in result.stdout


def test_generator_uses_agents_dir_for_codex():
    from skill_template.generate import load_config

    config = load_config()
    assert config["platforms"]["codex"]["output_dir"] == ".agents/skills/weekend-scout"


def test_template_has_no_utf8_bom():
    template_bytes = Path("skill_template/weekend-scout.template.md").read_bytes()
    assert not template_bytes.startswith(b"\xef\xbb\xbf")


def test_generator_includes_bundled_reference_files():
    from skill_template.generate import generate_for_platform, load_config, load_template

    config = load_config()
    files = generate_for_platform(
        "codex",
        config["platforms"]["codex"],
        config["shared_vars"],
        load_template(),
    )
    assert "SKILL.md" in files
    assert "references/search-workflow.md" in files
    assert "references/scoring-and-trips.md" in files
    assert "references/delivery-and-audit.md" in files
    assert "references/onboarding.md" in files
    assert "references/platform-transport.md" in files
    assert "references/platform-codex.md" in files
    assert "agents/openai.yaml" in files


def test_generated_skill_resources_are_mirrored_into_repo_and_package():
    repo_paths = [
        Path(".claude/skills/weekend-scout/references/search-workflow.md"),
        Path(".claude/skills/weekend-scout/references/scoring-and-trips.md"),
        Path(".claude/skills/weekend-scout/references/delivery-and-audit.md"),
        Path(".claude/skills/weekend-scout/references/onboarding.md"),
        Path(".claude/skills/weekend-scout/references/platform-transport.md"),
        Path(".agents/skills/weekend-scout/references/search-workflow.md"),
        Path(".agents/skills/weekend-scout/references/scoring-and-trips.md"),
        Path(".agents/skills/weekend-scout/references/delivery-and-audit.md"),
        Path(".agents/skills/weekend-scout/references/onboarding.md"),
        Path(".agents/skills/weekend-scout/references/platform-transport.md"),
        Path(".agents/skills/weekend-scout/references/platform-codex.md"),
        Path(".openclaw/skills/weekend-scout/references/search-workflow.md"),
        Path(".openclaw/skills/weekend-scout/references/scoring-and-trips.md"),
        Path(".openclaw/skills/weekend-scout/references/delivery-and-audit.md"),
        Path(".openclaw/skills/weekend-scout/references/onboarding.md"),
        Path(".openclaw/skills/weekend-scout/references/platform-transport.md"),
        Path("weekend_scout/skill_data/claude-code/references/search-workflow.md"),
        Path("weekend_scout/skill_data/claude-code/references/onboarding.md"),
        Path("weekend_scout/skill_data/claude-code/references/platform-transport.md"),
        Path("weekend_scout/skill_data/codex/references/search-workflow.md"),
        Path("weekend_scout/skill_data/codex/references/onboarding.md"),
        Path("weekend_scout/skill_data/codex/references/platform-transport.md"),
        Path("weekend_scout/skill_data/codex/references/platform-codex.md"),
        Path("weekend_scout/skill_data/openclaw/references/search-workflow.md"),
        Path("weekend_scout/skill_data/openclaw/references/onboarding.md"),
        Path("weekend_scout/skill_data/openclaw/references/platform-transport.md"),
    ]
    for path in repo_paths:
        assert path.exists(), f"Missing generated resource: {path}"


def test_core_runtime_skills_are_short_and_reference_driven():
    skill_paths = [
        Path(".claude/skills/weekend-scout/SKILL.md"),
        Path(".agents/skills/weekend-scout/SKILL.md"),
        Path(".openclaw/skills/weekend-scout/SKILL.md"),
    ]

    for path in skill_paths:
        content = _read_text(path)
        assert len(content.splitlines()) < 300, f"{path} exceeds line budget"
        assert "references/onboarding.md" in content
        assert "references/search-workflow.md" in content
        assert "references/scoring-and-trips.md" in content
        assert "references/delivery-and-audit.md" in content
        assert "Do **not** preload all references." in content
        assert "Do **not** open later-stage references during" in content
        assert "Do **not** open `references/search-workflow.md` before setup is complete." in content
        assert "If either setup condition is true, do **not** open any other reference" in content
        assert "`--cached-only` is a skill invocation argument." in content
        assert "continue with the normal Step 3 and Step 5/6 flow" in content
        assert "python -m weekend_scout audit-run --run-id" not in content
        assert "workflow.audit_command" in content
        assert "workflow.phase_order" not in content
        assert "workflow.log_checkpoints" not in content
        assert "**SEARCH STEP [SEARCH_STEP]**" not in content
        assert "**FETCH STEP [FETCH_STEP]**" not in content
        assert "For every WebSearch, execute `SEARCH_STEP` exactly as written." not in content
        assert "Do **not** invent trip bundles from unrelated weak findings." not in content
        assert "sole authority for Step 2 phase lifecycle" in content
        assert "Required `python -m weekend_scout ...` commands must succeed before the run continues." in content
        assert "Do **not** fabricate missing logs, synthesize helper outputs, or continue after such a failure." in content
        assert "If a bundled reference documents a negative-but-valid outcome" in content
        assert "phase_start missing" not in content
        assert "Do not use for codebase maintenance or skill edits." in content
        assert "weekend-scout-maintenance" not in content


def test_root_skill_is_bundle_bootstrap_dispatcher():
    content = _read_text(Path("SKILL.md"))

    assert "stable bundle entrypoint" in content
    assert "--with-pip --runtime-only" in content
    assert "pyproject.toml" in content
    assert ".claude/skills/weekend-scout/SKILL.md" in content
    assert ".agents/skills/weekend-scout/SKILL.md" in content
    assert ".openclaw/skills/weekend-scout/SKILL.md" in content
    assert "Do **not** manually edit cache files" in content
    assert "Do **not** send the user to README-style manual setup as the primary path." in content
    assert "Output Format" not in content
    assert "Skills Directory" not in content
    assert "ClawHub" not in content


def test_openclaw_needs_setup_stops_with_fixed_setup_message():
    openclaw_skill = _read_text(Path(".openclaw/skills/weekend-scout/SKILL.md"))
    packaged_openclaw_skill = _read_text(Path("weekend_scout/skill_data/openclaw/SKILL.md"))
    claude_skill = _read_text(Path(".claude/skills/weekend-scout/SKILL.md"))
    codex_skill = _read_text(Path(".agents/skills/weekend-scout/SKILL.md"))

    expected = (
        "Weekend Scout needs one-time setup. Run it again with your city and radius, "
        "for example: /weekend-scout Warsaw, 150"
    )

    assert "do **not** guess or infer a city" in openclaw_skill
    assert "do **not** continue to Step 2" in openclaw_skill
    assert expected in openclaw_skill
    assert "read `references/onboarding.md` and follow it exactly." not in openclaw_skill.split(
        "If `needs_setup` is `true`", 1
    )[1].split("If `warnings` contains `coordinates_not_set`", 1)[0]

    assert "do **not** guess or infer a city" in packaged_openclaw_skill
    assert "do **not** continue to Step 2" in packaged_openclaw_skill
    assert expected in packaged_openclaw_skill

    assert expected not in claude_skill
    assert expected not in codex_skill


def test_skill_wrapper_has_reset_mode_with_confirmation():
    template = _read_text(Path("skill_template/weekend-scout.template.md"))
    claude_skill = _read_text(Path(".claude/skills/weekend-scout/SKILL.md"))
    codex_skill = _read_text(Path(".agents/skills/weekend-scout/SKILL.md"))
    openclaw_skill = _read_text(Path(".openclaw/skills/weekend-scout/SKILL.md"))
    packaged_codex_skill = _read_text(Path("weekend_scout/skill_data/codex/SKILL.md"))

    assert "argument-hint: [city] [radius-km] [--cached-only] [--research-only] [--reset]" in template
    assert "If the user invoked `%%INVOKE_CMD%% --reset`, do **not** run `init-skill`." in template
    assert "python -m weekend_scout reset --yes" in template

    assert "If the user invoked `/weekend-scout --reset`, do **not** run `init-skill`." in claude_skill
    assert "If the user invoked `$weekend-scout --reset`, do **not** run `init-skill`." in codex_skill
    assert "If the user invoked `weekend-scout --reset`, do **not** run `init-skill`." in openclaw_skill
    assert "If the user invoked `$weekend-scout --reset`, do **not** run `init-skill`." in packaged_codex_skill
    for content in (claude_skill, codex_skill, openclaw_skill, packaged_codex_skill):
        assert "First ask for confirmation that this will delete the Weekend Scout config and cache for the active installation." in content
        assert "python -m weekend_scout reset --yes" in content
        assert "Do **not** continue to Step 1 or any discovery steps in reset mode." in content


def test_codex_transport_rule_moved_to_reference_file():
    codex_skill = _read_text(Path(".agents/skills/weekend-scout/SKILL.md"))
    claude_skill = _read_text(Path(".claude/skills/weekend-scout/SKILL.md"))
    openclaw_skill = _read_text(Path(".openclaw/skills/weekend-scout/SKILL.md"))
    transport_ref = _read_text(Path(".agents/skills/weekend-scout/references/platform-transport.md"))
    codex_ref = _read_text(Path(".agents/skills/weekend-scout/references/platform-codex.md"))

    assert "references/platform-transport.md" in codex_skill
    assert "references/platform-transport.md" in claude_skill
    assert "references/platform-transport.md" in openclaw_skill
    assert "references/platform-codex.md" not in codex_skill
    assert "transport-only snippets" in transport_ref
    assert "Set-Content -LiteralPath $payload_path -Encoding utf8" in transport_ref
    assert "Use `cache_dir` from the latest successful `init-skill` output" in transport_ref
    assert "<cache_dir from init-skill>" in transport_ref
    assert "_tmp_detail.tmp" in transport_ref
    assert "When one command uses multiple `--*-file` flags, each flag must use its own file path." in transport_ref
    assert "do **not** use `Write` to create brand-new transport payload files" in transport_ref
    assert "Shared JSON transport rules live in `references/platform-transport.md`." in codex_ref
    assert "Set-Content -LiteralPath $payload_path -Encoding utf8" not in codex_ref
    assert "_tmp_detail.tmp" not in codex_ref


def test_packaged_codex_skill_keeps_sidecar_and_references():
    skill_dir = Path("weekend_scout/skill_data/codex")
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "agents" / "openai.yaml").exists()
    assert (skill_dir / "references" / "platform-codex.md").exists()
    assert (skill_dir / "references" / "platform-transport.md").exists()


def test_onboarding_reference_uses_compact_two_question_prompt():
    paths = [
        Path("skill_template/resources/common/references/onboarding.md"),
        Path(".claude/skills/weekend-scout/references/onboarding.md"),
        Path(".agents/skills/weekend-scout/references/onboarding.md"),
        Path(".openclaw/skills/weekend-scout/references/onboarding.md"),
        Path("weekend_scout/skill_data/claude-code/references/onboarding.md"),
        Path("weekend_scout/skill_data/codex/references/onboarding.md"),
        Path("weekend_scout/skill_data/openclaw/references/onboarding.md"),
    ]
    expected = (
        "Weekend Scout needs a quick one-time setup. What city do you live in, "
        "and How far (in km) are you willing to drive for a day trip? "
        "(example: <city>, 100)"
    )
    for path in paths:
        content = _read_text(path)
        assert "Ask the user (and provide input example):" in content
        assert expected in content
        assert "documented onboarding" in content
        assert "fallback, not contract drift" in content
        assert "Normalize decorated city input to a plain city name" in content
        assert "`find-city` does not yield a usable resolved city" in content
        assert 'Use `WebSearch("<setup_city> city coordinates latitude longitude country")` first.' in content
        assert "If the search snippets already provide `lat`, `lon`, and `country`, use them." in content
        assert "Otherwise use at most one `WebFetch` of the best result" in content
        assert "Use the resolved city name in `home_city`" in content
        assert "Before writing the setup payload, read `references/platform-transport.md`." in content
        assert "Set `setup_json_path` under `cache_dir` from `init-skill`" in content
        assert 'python -m weekend_scout setup --json-file "$setup_json_path"' in content
        assert "--json '{" not in content
        assert "`setup` must succeed before `init-skill` is rerun." in content
        assert "stop onboarding and report that setup persistence failed" in content


def test_shared_transport_reference_has_dedicated_setup_transport_example():
    paths = [
        Path("skill_template/resources/common/references/platform-transport.md"),
        Path(".claude/skills/weekend-scout/references/platform-transport.md"),
        Path(".agents/skills/weekend-scout/references/platform-transport.md"),
        Path(".openclaw/skills/weekend-scout/references/platform-transport.md"),
        Path("weekend_scout/skill_data/claude-code/references/platform-transport.md"),
        Path("weekend_scout/skill_data/codex/references/platform-transport.md"),
        Path("weekend_scout/skill_data/openclaw/references/platform-transport.md"),
    ]
    for path in paths:
        content = _read_text(path)
        assert "Use this exact pattern for onboarding setup payloads:" in content
        assert "Use `cache_dir` from the latest successful `init-skill` output" in content
        assert "$cache_dir = '<cache_dir from init-skill>'" in content
        assert "$setup_json_path = Join-Path $cache_dir '_tmp_setup.tmp'" in content
        assert 'Set-Content -LiteralPath $setup_json_path -Encoding utf8' in content
        assert 'cache_dir="<cache_dir from init-skill>"' in content
        assert "printf '%s' '{\"reason\":\"<skip_reason>\"}' > \"$payload_path\"" in content
        assert "<<'EOF'" not in content
        assert 'python -m weekend_scout setup --json-file "$setup_json_path"' in content
        assert "For any `python -m weekend_scout ...` command that passes structured JSON" in content
        assert "Never pass structured JSON inline during a skill run." in content
        assert "Do **not** stage payloads through `/tmp`, `%TEMP%`" in content
        assert "do **not** use `Write` to create brand-new transport payload files" in content
        assert "cities_json_path" in content


def test_codex_delivery_reference_has_one_shot_network_blocked_resend():
    codex_delivery = _read_text(Path(".agents/skills/weekend-scout/references/delivery-and-audit.md"))
    claude_delivery = _read_text(Path(".claude/skills/weekend-scout/references/delivery-and-audit.md"))
    openclaw_delivery = _read_text(Path(".openclaw/skills/weekend-scout/references/delivery-and-audit.md"))
    codex_platform = _read_text(Path(".agents/skills/weekend-scout/references/platform-codex.md"))
    transport_ref = _read_text(Path(".agents/skills/weekend-scout/references/platform-transport.md"))

    assert 'error_code = "telegram_network_blocked"' in codex_delivery
    assert 'request Codex approval to rerun the exact same `python -m weekend_scout send --file "<path from written>" --run-id "<run_id>"` command once outside the sandbox' in codex_delivery
    assert "do **not** rerun `format-message`" in codex_delivery
    assert "do **not** retry more than once" in codex_delivery
    assert "if approval is denied" in codex_delivery

    assert 'request Codex approval' not in claude_delivery
    assert 'request Codex approval' not in openclaw_delivery

    assert '--send-reason <sent|telegram_not_configured|send_failed>' in claude_delivery
    assert '--send-reason <sent|telegram_not_configured|send_failed>' in codex_delivery
    assert '--send-reason <sent|telegram_not_configured|telegram_internal|send_failed>' in openclaw_delivery
    assert "if this run was started from an interactive channel, deliver formatted results through the invocation channel" in openclaw_delivery
    assert "if this run was started by OpenClaw cron, return formatted results for the cron runner's configured announce target" in openclaw_delivery
    assert "read the formatted message from the file path returned by `format-message`" not in openclaw_delivery
    assert '`send_reason = "telegram_internal"`' in openclaw_delivery
    assert "python -m weekend_scout config telegram_bot_token YOUR_BOT_TOKEN" in claude_delivery
    assert "python -m weekend_scout config telegram_bot_token YOUR_BOT_TOKEN" in codex_delivery
    assert "python -m weekend_scout config telegram_bot_token YOUR_BOT_TOKEN" not in openclaw_delivery
    assert "if this run was started from an interactive channel, deliver formatted results through the invocation channel" not in claude_delivery
    assert "if this run was started from an interactive channel, deliver formatted results through the invocation channel" not in codex_delivery
    assert "Chat ID - if defined in schedule instructions" not in openclaw_delivery
    assert "do **not** mark served" not in openclaw_delivery.split('If `{\"sent\": false, \"reason\": \"telegram_not_configured\", ...}`:', 1)[1].split('## Mark served', 1)[0]
    assert "_tmp_delivery_stats.tmp" in codex_delivery
    assert "_tmp_delivery_notes.tmp" in codex_delivery

    assert "Only request Codex approval / outside-sandbox execution when a stage reference explicitly authorizes it." in codex_platform
    assert "rerun the exact same `python -m weekend_scout send ...` command once with approval-gated outside-sandbox execution" in codex_platform
    assert "Before writing delivery payloads, read `references/platform-transport.md`." in codex_delivery
    assert "Never pass structured JSON inline during a skill run." in transport_ref


def test_search_workflow_restores_monolith_guardrails():
    content = _read_text(Path("skill_template/resources/common/references/search-workflow.md"))
    phase_a = content.split("## Phase A: Broad sweep", 1)[1].split("## Phase B: Aggregator deep-dive", 1)[0]
    phase_b = content.split("## Phase B: Aggregator deep-dive", 1)[1].split("## Phase C: Targeted city searches", 1)[0]
    phase_c = content.split("## Phase C: Targeted city searches", 1)[1].split("## Phase D: Verification", 1)[0]
    phase_d = content.split("## Phase D: Verification", 1)[1]

    assert "## Event filter" in content
    assert "### Status line templates" in content
    assert "religious festivals and processions" in content
    assert "religious services" in content
    assert "After Phase A completes, continue only to Phase B." in content
    assert "Phase B is URL-based extraction. Use only `FETCH STEP` for queued page work" in content
    assert "Out-of-scope hits may be mentioned as discarded evidence, but must not be saved" in content
    assert "Broad or aggregator hits outside the radius do **not** justify ending targeted search" in content
    assert "Do **not** start another web action until the matching `log-search` succeeds." in content
    assert "Write a fresh payload file immediately before each `log-search` call." in content
    assert "references/platform-transport.md" in content
    assert "`cache_dir` from `init-skill`" in content
    assert "`--cities-file` and `--events-file` must point to different files." in content
    assert "references/platform-codex.md" not in content
    assert "Broad searches must log `cities = [home_city]`." in content
    assert "Targeted and verification searches/fetches must log `cities = [city_name]`" in content
    assert "If a kept event has a known event/source URL, include it as `source_url` in that event object." in content
    assert "Use the best known relevant URL the first time you keep that event." in content
    assert "If only a listing or aggregator page URL is known, use that instead of leaving `source_url` blank." in content
    assert "If a follow-up `WebFetch` fails, keep any earlier known `source_url`." in content
    assert "Do **not** leave them only in scratch notes or a final sources list." in content
    assert "The CLI owns the canonical run-level candidate set." in content
    assert "query_already_done" in content
    assert "retry_on_rerun" in content
    assert "retry_query" in content
    assert "`already_done`" not in content
    assert "Required Step 2 CLI calls must succeed before discovery continues." in content
    assert "show the human-readable `error` plus the `failure_id`" in content
    assert "without inventing a" in content
    assert "diagnosis." in content
    assert "Do **not** repair failed Step 2 state by retroactive logging or manual" in content
    assert "payload" in content
    assert "synthesis." in content
    assert "phase_start missing" not in content
    assert "If that helper returns `logged: false` or an `error`" not in content
    assert "coverage is still thin" not in content
    assert "--events-discovered" not in content
    assert "--covered-cities" not in content
    assert "max_searches * 0.6" not in content
    assert "max_searches * 0.8" not in content
    assert "--searches-used" not in content
    assert "Otherwise:" not in content
    assert "Reset phase counters" not in content
    assert "phase_searches" not in content
    assert "phase_fetches" not in content
    assert "phase_new_events" not in content
    assert "Show the progress line." not in content
    assert "Do **not** skip tier2 or tier3 because coverage looks good elsewhere." in content
    assert "validation_fetches_used/validation_fetch_limit" in content
    assert 'STATUS phase=<A|C> action=WebSearch searches=<searches_used>/<max_searches> target="<query>"' in content
    assert 'STATUS phase=<B|C> action=WebFetch fetches=<fetches_used>/<max_fetches> target="<url>"' in content
    assert 'STATUS phase=D action=WebFetch validation_fetches=<validation_fetches_used>/<validation_fetch_limit> target="<url>"' in content
    assert 'STATUS phase=<A|C> action=WebSearch searches=<searches_used>/<max_searches> fetches=<fetches_used>/<max_fetches> target="<query>"' not in content
    assert 'STATUS phase=<B|C> action=WebFetch searches=<searches_used>/<max_searches> fetches=<fetches_used>/<max_fetches> target="<url>"' not in content
    assert 'STATUS phase=D action=WebFetch searches=<searches_used>/<max_searches> fetches=<fetches_used>/<max_fetches> validation_fetches=<validation_fetches_used>/<validation_fetch_limit> target="<url>"' not in content
    assert "The counter shown in a status line is always the current pre-action counter." in content
    assert "Increment only after the matching web tool call completes." in content
    assert "Action triplet rule for this step:" in content
    assert "exactly one `SEARCH STATUS` line, emitted only through the platform's local CLI/exec command tool" in content
    assert "then the matching `WebSearch(query)`" in content
    assert "then the matching `log-search`" in content
    assert "`log-search --query` must exactly match the target shown in the immediately preceding status line" in content
    assert "do **not** repeat the status line after the tool call" in content
    assert "do **not** emit another status line or run another web action until that `log-search` succeeds" in content
    assert "never include status lines in the assistant's text response or final delivery" in content
    assert "--events '<JSON array>'" not in content
    assert "--cities '[\"<city_name>\"]'" not in content
    assert "--events '[]'" not in content
    assert "--events-file \"$events_json_path\"" in content
    assert "--cities-file \"$cities_json_path\"" in content
    assert "--detail-file \"$detail_json_path\"" in content
    assert "--detail '{\"reason\":\"cached_only_requested\"}'" not in content
    assert "2. Show the exact `SEARCH STATUS` line." in content
    assert "2. Show the exact status line for the current fetch type:" in content
    assert "SEARCH STEP` with `phase_label = broad`" in content
    assert "FETCH STEP` with `phase_label = aggregator`" in content
    assert "SEARCH STEP` with `phase_label = targeted`" in content
    assert "FETCH STEP` with `phase_label = verification`" in content
    assert "Queued aggregator URL work in Phase B uses the exact `DISCOVERY FETCH STATUS` line." in content
    assert "Every Phase B web action must be `DISCOVERY FETCH STATUS` -> `WebFetch(url, prompt)` -> `log-search --phase aggregator`." in content
    assert "Do **not** run fresh `WebSearch` queries inside Phase B." in content
    assert "Targeted searches in Phase C use the exact `SEARCH STATUS` line with `phase=C`." in content
    assert "Any targeted fetch in Phase C uses the exact `DISCOVERY FETCH STATUS` line with `phase=C`." in content
    assert "Tier2 targeted searches in Phase C use the exact `SEARCH STATUS` line with `phase=C`." in content
    assert "Any targeted fetch in tier2 uses the exact `DISCOVERY FETCH STATUS` line with `phase=C`." in content
    assert "Tier3 targeted searches in Phase C use the exact `SEARCH STATUS` line with `phase=C`." in content
    assert "Any targeted fetch in tier3 uses the exact `DISCOVERY FETCH STATUS` line with `phase=C`." in content
    assert "Do **not** log a search phrase as an aggregator or verification fetch." in content
    assert "verification fetches in Phase D use the exact `VALIDATION FETCH STATUS` line" in content
    assert "the `VALIDATION FETCH STATUS` line must include `validation_fetches_used/validation_fetch_limit`" in content
    assert "every Phase D web action must be `VALIDATION FETCH STATUS` -> `WebFetch(url, prompt)` -> `log-search --phase verification`" in content
    assert "do **not** drop an already known `source_url` just because the verification fetch fails" in content
    assert "do **not** run fresh `WebSearch` queries inside Phase D" in content
    assert "python -m weekend_scout session-query --run-id" in content
    assert "python -m weekend_scout prepare-digest --date" in content
    assert "python -m weekend_scout phase-summary" in content
    assert "python -m weekend_scout phase-c-cities --run-id" in content
    assert "python -m weekend_scout save --run-id \"<run_id>\" --from-session" in content
    assert "`duplicates_merged`" in content
    assert "Store that helper result as `digest_input` and use only `digest_input` for Step 3." in content
    assert '"reason": "cached_only_requested"' in content
    assert "Cached-only bypasses the offline pre-check and discovery Phases A-D." in content
    assert "After this cached-only bypass, continue with the normal Step 3 and Step 5/6 flow." in content
    assert "Skip this section entirely when invoked with `--cached-only`." in content
    assert "Do **not** append `--cached-only` to" in content
    assert "`python -m weekend_scout init` or `python -m weekend_scout init-skill`." in content
    assert "Finish and log the current batch before requesting the next one." in content
    assert "--phase A --target-weekend \"<saturday>\"" in content
    assert "--phase B --target-weekend \"<saturday>\"" in content
    assert "--phase C --target-weekend \"<saturday>\"" in content
    assert "--phase D --target-weekend \"<saturday>\"" in content
    assert "phase-summary --run-id \"<run_id>\" --phase A --target-weekend \"<saturday>\"" in content
    assert "phase-summary --run-id \"<run_id>\" --phase B --target-weekend \"<saturday>\"" in content
    assert "phase-summary --run-id \"<run_id>\" --phase C --target-weekend \"<saturday>\"" in content
    assert "phase-summary --run-id \"<run_id>\" --phase D --target-weekend \"<saturday>\"" in content
    assert "Do **not** call `phase-summary` between tier batches." in content
    assert phase_a.index("1. Log Phase A start:") < phase_a.index("all_queries_in_done_q")
    assert phase_b.index("1. Log Phase B start:") < phase_b.index("no_aggregator_urls")
    assert phase_c.index("1. Log Phase C start:") < phase_c.index("all_cities_covered")
    assert phase_d.index("1. Log Phase D start:") < phase_d.index("all_confirmed")


def test_openclaw_skill_wrapper_mentions_pre_search_notice():
    openclaw_skill = _read_text(Path(".openclaw/skills/weekend-scout/SKILL.md"))
    packaged_openclaw_skill = _read_text(Path("weekend_scout/skill_data/openclaw/SKILL.md"))
    claude_skill = _read_text(Path(".claude/skills/weekend-scout/SKILL.md"))
    codex_skill = _read_text(Path(".agents/skills/weekend-scout/SKILL.md"))

    expected = "Searching for next weekend's events now. This can take a minute or two."
    cron_rule = "Do **not** send that message for OpenClaw cron runs."
    cached_only_rule = "Do **not** send that message for `weekend-scout --cached-only`."
    repeat_rule = "Do **not** repeat that message during later phases, later city batches, or reruns within the same run."

    assert expected in openclaw_skill
    assert cron_rule in openclaw_skill
    assert cached_only_rule in openclaw_skill
    assert repeat_rule in openclaw_skill

    assert expected in packaged_openclaw_skill
    assert cron_rule in packaged_openclaw_skill
    assert cached_only_rule in packaged_openclaw_skill
    assert repeat_rule in packaged_openclaw_skill
    assert "return the final formatted summary for cron delivery" in openclaw_skill
    assert "return the final formatted summary for cron delivery" in packaged_openclaw_skill
    assert "final plain-text summary for cron delivery" not in openclaw_skill
    assert "final plain-text summary for cron delivery" not in packaged_openclaw_skill

    assert expected not in claude_skill
    assert expected not in codex_skill


def test_delivery_reference_uses_helper_commands_and_debug_audit():
    content = _read_text(Path("skill_template/resources/common/references/delivery-and-audit.md"))
    transport_ref = _read_text(Path("skill_template/resources/common/references/platform-transport.md"))

    assert "python -m weekend_scout prepare-delivery --run-id" in content
    assert "python -m weekend_scout run-complete --run-id" in content
    assert '--stage pre_send' in content
    assert '--stage post_send' in content
    assert "`audit-run` is debug-only by default" in content
    assert "If a required delivery command returns a top-level `error`" in content
    assert "`failure_id`" in content
    assert '`send` returning `{"sent": false, "reason": "telegram_not_configured", ...}`' in content
    assert '`send` returning `{"sent": false, "reason": "send_failed", ...}`' in content
    assert "`audit-run` returning `ok: false` is debug information, not contract drift" in content
    assert "`preview` is the authoritative user-visible report for this run" in content
    assert "`preview`: markdown-ish composite report for showing in the conversation or returning through native channel delivery" in content
    assert "`delivery_stats_lines`" in content
    assert "--stats-lines" in content
    assert "--notes-lines" in content
    assert "optional `stats-lines`: a JSON array of plain strings to append after the digest" in content
    assert "optional `notes-lines`: a JSON array of plain strings to append after the stats block" in content
    assert "print the audit mismatches and warnings in the agent CLI only" in content
    assert "Do **not** append it" in content
    assert "Telegram delivery, or native channel delivery." in content
    assert "Debug information from audit:" in content
    assert "Pre-send audit:" in content
    assert "Post-send audit:" in content
    assert "Do **not** tell the" in content
    assert "user to fix the skill, switch modes, or perform maintenance." in content
    assert "Only after the audit passes" not in content
    assert "to prepend" not in content
    assert "includes the normal digest and the stats block" in content
    assert "--cached-events" not in content
    assert "Before writing delivery payloads, read `references/platform-transport.md`." in content
    assert "`cache_dir` from `init-skill`" in content
    assert "validation budget used: `validation_fetches_used/validation_fetch_limit`" in content
    assert "_tmp_city_events.tmp" in content
    assert "_tmp_delivery_stats.tmp" in content
    assert "_tmp_delivery_notes.tmp" in content
    assert "--notes-lines-file \"$delivery_notes_json_path\"" in content
    assert "_tmp_uncovered_tier1.tmp" not in content
    assert "`uncovered_tier1` = derived from `run_init.tier1` plus the saved weekend cache" in content
    assert "`run_complete.send_reason` must copy `send.reason`" in content
    assert "if this run was started from an interactive channel, deliver formatted results through the invocation channel" in content
    assert "if this run was started by OpenClaw cron, return formatted results for the cron runner's configured announce target" in content
    assert '`send_reason = "telegram_internal"`' in content
    assert "<%%RUN_COMPLETE_SEND_REASONS%%>" in content

    claude_delivery = _read_text(Path(".claude/skills/weekend-scout/references/delivery-and-audit.md"))
    assert "Before writing delivery payloads, read `references/platform-transport.md`." in claude_delivery
    assert "`preview`: markdown-ish composite report for showing in the conversation or returning through native channel delivery" in claude_delivery
    assert "Debug information from audit:" in claude_delivery
    assert "CLI-only debug section" in claude_delivery
    assert "Never pass structured JSON inline during a skill run." in transport_ref
    assert "Do **not** stage payloads through `/tmp`, `%TEMP%`" in transport_ref


def test_last_failed_run_fixture_documents_unlogged_small_city_searches():
    cli_trace = _read_text(Path("tests/fixtures/cli_trace_2026-04-03_1529_excerpt.txt"))
    action_log = _read_text(Path("tests/fixtures/run_2026-04-03_1529.jsonl"))

    assert "Get-Content -LiteralPath 'D:\\Work\\Weekend-Scout\\.agents\\skills\\weekend-scout\\references\\search-workflow.md'" in cli_trace
    assert "Searched Otwock imprezy plenerowe 4 kwietnia 2026" in cli_trace
    assert "Otwock" not in action_log


def test_init_skill_compact_contract_no_longer_ships_full_later_tiers_in_runtime_output():
    content = _read_text(Path("skill_template/weekend-scout.template.md"))
    assert "cities.tier2_count, cities.tier3_count" in content
    assert "tier1" in content
    assert "cache_dir" in content.split("Otherwise extract and keep:")[1]
    assert "Reuse `cache_dir` from `init-skill`" in content
    assert "searches_this_week" not in content.split("Otherwise extract and keep:")[1]


def test_no_semantic_transport_filenames_in_skill_sources():
    paths = [
        Path("skill_template/resources/common/references/search-workflow.md"),
        Path("skill_template/resources/common/references/delivery-and-audit.md"),
        Path("skill_template/resources/common/references/onboarding.md"),
        Path("skill_template/resources/common/references/platform-transport.md"),
        Path("skill_template/resources/codex/references/platform-codex.md"),
    ]
    forbidden = [
        "setup.json",
        "events.json",
        "city-events.json",
        "trips.json",
        "covered-cities.json",
        "uncovered-tier1.json",
    ]
    for path in paths:
        content = _read_text(path)
        for token in forbidden:
            assert token not in content, f"{path} still mentions semantic transport file {token}"


def test_authoritative_reference_commands_match_cli_contract():
    onboarding = _read_text(Path("skill_template/resources/common/references/onboarding.md"))
    search = _read_text(Path("skill_template/resources/common/references/search-workflow.md"))
    scoring = _read_text(Path("skill_template/resources/common/references/scoring-and-trips.md"))
    delivery = _read_text(Path("skill_template/resources/common/references/delivery-and-audit.md"))

    onboarding_commands = _extract_weekend_scout_commands(onboarding)
    search_commands = _extract_weekend_scout_commands(search)
    scoring_commands = _extract_weekend_scout_commands(scoring)
    delivery_commands = _extract_weekend_scout_commands(delivery)

    _assert_command_with_parts(
        _commands_named(onboarding, "find-city"),
        label="find-city",
        parts=["--name \"<setup_city>\""],
    )
    _assert_command_with_parts(
        _commands_named(onboarding, "setup"),
        label="setup --json-file",
        parts=["--json-file \"$setup_json_path\""],
    )
    _assert_command_with_parts(
        _commands_named(onboarding, "init-skill"),
        label="init-skill rerun",
        parts=[],
    )
    assert "setup persistence failed" in onboarding
    assert "at most one `WebFetch`" in onboarding

    for phase in ("A", "B", "C", "D"):
        _assert_command_with_parts(
            _commands_named(search, "log-action"),
            label=f"phase_start {phase}",
            parts=["--run-id \"<run_id>\"", "--action phase_start", f"--phase {phase}", "--target-weekend \"<saturday>\""],
        )
        _assert_command_with_parts(
            _commands_named(search, "phase-summary"),
            label=f"phase-summary {phase}",
            parts=["--run-id \"<run_id>\"", f"--phase {phase}", "--target-weekend \"<saturday>\""],
        )

    _assert_command_with_parts(
        _commands_named(search, "log-search"),
        label="log-search non-empty events file",
        parts=["--query \"<query_or_url>\"", "--target-weekend \"<saturday>\"", "--cities-file \"$cities_json_path\"", "--events-file \"$events_json_path\"", "--phase <broad|aggregator|targeted|verification>", "--result-count <N>", "--run-id \"<run_id>\""],
    )
    _assert_command_with_parts(
        _commands_named(search, "phase-c-cities"),
        label="phase-c-cities tier2",
        parts=["--run-id \"<run_id>\"", "--tier 2", "--offset <offset>", "--limit 6"],
    )
    _assert_command_with_parts(
        _commands_named(search, "phase-c-cities"),
        label="phase-c-cities tier3",
        parts=["--run-id \"<run_id>\"", "--tier 3", "--offset <offset>", "--limit 6"],
    )
    _assert_command_with_parts(
        _commands_named(search, "session-query"),
        label="session-query",
        parts=["--run-id \"<run_id>\""],
    )
    _assert_command_with_parts(
        _commands_named(search, "save"),
        label="save from-session",
        parts=["--run-id \"<run_id>\"", "--from-session"],
    )
    _assert_command_with_parts(
        _commands_named(search, "cache-query"),
        label="cache-query",
        parts=["--date \"<saturday>\""],
    )
    _assert_command_with_parts(
        _commands_named(search + "\n" + scoring, "prepare-digest"),
        label="prepare-digest",
        parts=["--date \"<saturday>\""],
    )

    _assert_command_with_parts(
        _commands_named(scoring, "score-summary"),
        label="score-summary",
        parts=["--run-id \"<run_id>\"", "--target-weekend \"<saturday>\"", "--total-pool <N>", "--city-events-selected <N>", "--trip-options <N>"],
    )

    _assert_command_with_parts(
        _commands_named(delivery, "prepare-delivery"),
        label="prepare-delivery",
        parts=["--run-id \"<run_id>\"", "--target-weekend \"<saturday>\"", "--events-sent <city_count + trip_count>"],
    )
    _assert_command_with_parts(
        _commands_named(delivery, "format-message"),
        label="format-message file",
        parts=["--saturday \"<saturday>\"", "--sunday \"<sunday>\"", "--city-events-file \"$city_events_json_path\"", "--trips-file \"$trips_json_path\"", "--stats-lines-file \"$delivery_stats_json_path\"", "--run-id \"<run_id>\""],
    )
    _assert_command_with_parts(
        _commands_named(delivery, "send"),
        label="send",
        parts=["--file \"<path from written>\"", "--run-id \"<run_id>\""],
    )
    _assert_command_with_parts(
        _commands_named(delivery, "cache-mark-served"),
        label="cache-mark-served",
        parts=["--date \"<saturday>\"", "--run-id \"<run_id>\""],
    )
    _assert_command_with_parts(
        _commands_named(delivery, "run-complete"),
        label="run-complete",
        parts=["--run-id \"<run_id>\"", "--target-weekend \"<saturday>\"", "--events-sent <city_count + trip_count>", "--sent <true|false>", "--send-reason <%%RUN_COMPLETE_SEND_REASONS%%>", "--served-marked <true|false>"],
    )
    _assert_command_with_parts(
        _commands_named(delivery, "audit-run"),
        label="audit-run pre_send",
        parts=["--run-id \"<run_id>\"", "--stage pre_send"],
    )
    _assert_command_with_parts(
        _commands_named(delivery, "audit-run"),
        label="audit-run post_send",
        parts=["--run-id \"<run_id>\"", "--stage post_send"],
    )

    all_commands = "\n".join(search_commands + scoring_commands + delivery_commands + onboarding_commands)
    assert "--cached-events" not in all_commands
    assert "--searches-used" not in all_commands
    assert "--events-discovered" not in all_commands


def test_scoring_reference_uses_prepare_digest_output():
    content = _read_text(Path("skill_template/resources/common/references/scoring-and-trips.md"))

    assert "prepare-digest --date" in content
    assert "`digest_input`" in content
    assert "trip_city_groups" in content
    assert "Objective dedupe and city grouping are already done by Python." in content
    assert "do **not** under-fill the digest when eligible helper-provided candidates exist" in content
    assert "preserve each selected event's `source_url` when building the `city-events` payload" in content
    assert "keep that `source_url` when later verification did not improve the link" in content
    assert "copy that event's `source_url` into trip `url` when available" in content
    assert "all canonical events for that city, sorted best-first" in content
    assert "Label trips `01` through `NN` in the final message only." in content
    assert "fewer than three credible trip cities" not in content
    assert "aiming for at least three credible trip options" not in content
    assert "up to 3 canonical events for that city" not in content
    assert "cached_full" not in content


def test_search_reference_no_longer_carries_cached_full_into_step_3():
    content = _read_text(Path("skill_template/resources/common/references/search-workflow.md"))

    assert "Store that result as `cached_full`" not in content
    assert "supporting raw cache context" not in content
    assert "use only `digest_input` for Step 3" in content
    assert "fewer than three credible trip cities" not in content


def test_authoritative_references_use_placeholder_formats_consistently():
    refs = [
        _read_text(Path("skill_template/resources/common/references/onboarding.md")),
        _read_text(Path("skill_template/resources/common/references/search-workflow.md")),
        _read_text(Path("skill_template/resources/common/references/scoring-and-trips.md")),
        _read_text(Path("skill_template/resources/common/references/delivery-and-audit.md")),
    ]
    combined = "\n".join(refs)

    assert "\"<run_id>\"" in combined
    assert "\"<saturday>\"" in combined
    assert "\"<sunday>\"" in combined
    assert "\"$cities_json_path\"" in combined
    assert "\"$events_json_path\"" in combined
    assert "\"$setup_json_path\"" in combined
    assert "\"$detail_json_path\"" in combined
    assert "<N>" in combined
    assert "'<JSON array>'" not in combined
    assert not re.search(r"--events-sent \"<city_count \+ trip_count>\"", combined)
