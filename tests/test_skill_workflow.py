"""Tests for skill generation, encoding, and install target paths."""

from pathlib import Path


def _norm(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def test_generator_uses_agents_dir_for_codex():
    from skill_template.generate import load_config

    config = load_config()
    assert config["platforms"]["codex"]["output_dir"] == ".agents/skills/weekend-scout"


def test_template_has_no_utf8_bom():
    template_bytes = Path("skill_template/weekend-scout.template.md").read_bytes()
    assert not template_bytes.startswith(b"\xef\xbb\xbf")


def test_template_and_generated_skill_preserve_known_unicode():
    template = _read_text(Path("skill_template/weekend-scout.template.md"))
    generated = _read_text(Path(".claude/skills/weekend-scout/SKILL.md"))

    for literal in ("—", "→", "×", "Łódź"):
        assert literal in template
        assert literal in generated


def test_template_family_has_no_common_mojibake_markers():
    markers = ("вЂ", "в†", "Г—", "ЕЃ")
    paths = [
        Path("skill_template/weekend-scout.template.md"),
        Path(".claude/skills/weekend-scout/SKILL.md"),
        Path(".openclaw/skills/weekend-scout/SKILL.md"),
        Path("weekend_scout/skill_data/claude-code/SKILL.md"),
        Path("weekend_scout/skill_data/codex/SKILL.md"),
        Path("weekend_scout/skill_data/openclaw/SKILL.md"),
    ]

    for path in paths:
        content = _read_text(path)
        for marker in markers:
            assert marker not in content, f"{path} contains mojibake marker {marker!r}"


def test_openclaw_metadata_is_single_line_json_without_pip_installer():
    from skill_template.generate import generate_for_platform, load_config, load_template

    config = load_config()
    content = generate_for_platform(
        "openclaw",
        config["platforms"]["openclaw"],
        config["shared_vars"],
        load_template(),
    )["SKILL.md"]

    metadata_lines = [line for line in content.splitlines() if line.startswith("metadata:")]
    assert metadata_lines == ['metadata: {"openclaw":{"requires":{"bins":["python"]}}}']
    assert 'kind: "pip"' not in content
    assert "preferred_model" not in content
