"""Tests for generated skill structure, packaging, and install target paths."""

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
    assert "references/platform-codex.md" in files
    assert "agents/openai.yaml" in files


def test_generated_skill_resources_are_mirrored_into_repo_and_package():
    repo_paths = [
        Path(".claude/skills/weekend-scout/references/search-workflow.md"),
        Path(".claude/skills/weekend-scout/references/scoring-and-trips.md"),
        Path(".claude/skills/weekend-scout/references/delivery-and-audit.md"),
        Path(".claude/skills/weekend-scout/references/onboarding.md"),
        Path(".agents/skills/weekend-scout/references/search-workflow.md"),
        Path(".agents/skills/weekend-scout/references/scoring-and-trips.md"),
        Path(".agents/skills/weekend-scout/references/delivery-and-audit.md"),
        Path(".agents/skills/weekend-scout/references/onboarding.md"),
        Path(".agents/skills/weekend-scout/references/platform-codex.md"),
        Path(".openclaw/skills/weekend-scout/references/search-workflow.md"),
        Path(".openclaw/skills/weekend-scout/references/scoring-and-trips.md"),
        Path(".openclaw/skills/weekend-scout/references/delivery-and-audit.md"),
        Path(".openclaw/skills/weekend-scout/references/onboarding.md"),
        Path("weekend_scout/skill_data/claude-code/references/search-workflow.md"),
        Path("weekend_scout/skill_data/claude-code/references/onboarding.md"),
        Path("weekend_scout/skill_data/codex/references/search-workflow.md"),
        Path("weekend_scout/skill_data/codex/references/onboarding.md"),
        Path("weekend_scout/skill_data/codex/references/platform-codex.md"),
        Path("weekend_scout/skill_data/openclaw/references/search-workflow.md"),
        Path("weekend_scout/skill_data/openclaw/references/onboarding.md"),
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
        assert "python -m weekend_scout audit-run --run-id" not in content
        assert "workflow.audit_command" in content
        assert "**SEARCH STEP [SEARCH_STEP]**" not in content
        assert "**FETCH STEP [FETCH_STEP]**" not in content
        assert "For every WebSearch, execute `SEARCH_STEP` exactly as written." not in content
        assert "Do **not** invent trip bundles from unrelated weak findings." not in content
        assert "Do not use for codebase maintenance or skill edits." in content
        assert "weekend-scout-maintenance" not in content


def test_codex_transport_rule_moved_to_reference_file():
    core_content = _read_text(Path(".agents/skills/weekend-scout/SKILL.md"))
    ref_content = _read_text(Path(".agents/skills/weekend-scout/references/platform-codex.md"))

    assert "references/platform-codex.md" in core_content
    assert "**Codex JSON file rule:**" not in core_content
    assert "Set-Content -LiteralPath $payload_path -Encoding utf8" in ref_content
    assert ".weekend_scout/cache" in ref_content
    assert "_tmp_detail.tmp" in ref_content


def test_packaged_codex_skill_keeps_sidecar_and_references():
    skill_dir = Path("weekend_scout/skill_data/codex")
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "agents" / "openai.yaml").exists()
    assert (skill_dir / "references" / "platform-codex.md").exists()


def test_onboarding_reference_uses_compact_two_question_prompt():
    paths = [
        Path("skill_template/resources/common/references/onboarding.md"),
        Path(".agents/skills/weekend-scout/references/onboarding.md"),
        Path("weekend_scout/skill_data/codex/references/onboarding.md"),
    ]
    expected = (
        "Weekend Scout needs a quick one-time setup. What city do you live in, "
        "and How far (in km) are you willing to drive for a day trip? "
        "(example: Warsaw, 100)"
    )
    for path in paths:
        assert expected in _read_text(path)


def test_search_workflow_restores_monolith_guardrails():
    content = _read_text(Path("skill_template/resources/common/references/search-workflow.md"))

    assert "## Event filter" in content
    assert "religious festivals and processions" in content
    assert "religious services" in content
    assert "After Phase A completes, continue only to Phase B." in content
    assert "Phase B is URL-based extraction. Use only `FETCH STEP` for queued page work" in content
    assert "Out-of-scope hits may be mentioned as discarded evidence, but must not be saved" in content
    assert "Broad or aggregator hits outside the radius do **not** justify ending targeted search" in content
    assert "Do **not** start another web action until the matching `log-search` succeeds." in content
    assert "Write a fresh payload file immediately before each `log-search` call." in content
    assert "python -m weekend_scout phase-summary" in content
    assert "python -m weekend_scout phase-c-cities --run-id" in content
    assert "Finish and log the current batch before requesting the next one." in content


def test_delivery_reference_uses_helper_commands_and_debug_audit():
    content = _read_text(Path("skill_template/resources/common/references/delivery-and-audit.md"))

    assert "python -m weekend_scout run-complete --run-id" in content
    assert "`audit-run` is debug-only by default." in content
    assert "Always report first:" in content
    assert "DEBUG INFORMATION" in content
    assert "Do **not** tell the user to fix the skill" in content
    assert "Only after the audit passes" not in content


def test_last_failed_run_fixture_documents_unlogged_small_city_searches():
    cli_trace = _read_text(Path("tests/fixtures/cli_trace_2026-04-03_1529_excerpt.txt"))
    action_log = _read_text(Path("tests/fixtures/run_2026-04-03_1529.jsonl"))

    assert "Get-Content -LiteralPath 'D:\\Work\\Weekend-Scout\\.agents\\skills\\weekend-scout\\references\\search-workflow.md'" in cli_trace
    assert "Searched Otwock imprezy plenerowe 4 kwietnia 2026" in cli_trace
    assert "Otwock" not in action_log
