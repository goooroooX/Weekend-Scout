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


def test_claude_argument_hint_uses_bare_anthropic_style():
    template = _read_text(Path("skill_template/weekend-scout.template.md"))
    generated = _read_text(Path(".claude/skills/weekend-scout/SKILL.md"))

    assert "argument-hint: [city] [radius-km] [--cached-only]" in template
    assert "argument-hint: [city] [radius-km] [--cached-only]" in generated
    assert 'argument-hint: "[city] [radius-km] [--cached-only]"' not in template
    assert 'argument-hint: "[city] [radius-km] [--cached-only]"' not in generated


def test_template_and_generated_skill_preserve_known_unicode():
    template = _read_text(Path("skill_template/weekend-scout.template.md"))
    generated = _read_text(Path(".claude/skills/weekend-scout/SKILL.md"))

    for literal in ("Łódź", "→", "Sat–Sun"):
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


def test_codex_skill_uses_file_based_payload_commands():
    content = _read_text(Path(".agents/skills/weekend-scout/SKILL.md"))

    assert "python -m weekend_scout init-skill [--city CITY] [--radius KM]" in content
    assert "python -m weekend_scout init [--city CITY] [--radius KM]" not in content
    assert "cached_count = output.cached.count" in content
    assert "cached_covered_cities = output.cached.covered_cities" in content
    assert "cached_city_counts = output.cached.city_counts" in content
    assert "cached = output.cached_events" not in content
    assert 'python -m weekend_scout cache-query --date "<saturday>"' in content
    assert "Here, `saturday` means `output.config.target_weekend.saturday` in ISO format (`YYYY-MM-DD`)," in content
    assert "Store that result as `cached_full`, then proceed directly to Step 3 using only `cached_full`." in content
    assert "Before Step 3, load the full cached weekend event rows once with:" in content
    assert "Here, `saturday` means the same ISO Saturday date from `init-skill`" in content
    assert "Store that result as `cached_full` and combine `cached_full` + newly saved events for ranking." in content
    assert "**Codex JSON file rule:**" in content
    assert "**Normal run rule:**" in content
    assert "do **not** inspect `weekend_scout` package" in content
    assert "stop the run and tell the user" in content
    assert "the skill needs maintenance" in content
    assert 'python -m weekend_scout setup --json-file "$setup_json_path"' in content
    assert '--cities-file "$cities_json_path"' in content
    assert '--detail-file "$detail_json_path"' in content
    assert '--events-file "$events_json_path"' in content
    assert '--city-events-file "$city_events_json_path"' in content
    assert '--trips-file "$trips_json_path"' in content
    assert "get_cache_dir(load_config())" not in content
    assert ".weekend_scout/cache" in content
    assert "New-Item -ItemType Directory -Force -Path $cache_dir | Out-Null" in content
    assert 'mkdir -p "$cache_dir"' in content
    assert "Reuse" in content
    assert "`setup_json_path`" in content
    assert "`detail_json_path`" in content
    assert "`trips_json_path`" in content
    assert "_tmp_detail.tmp" in content
    assert 'Set-Content -LiteralPath $payload_path -Encoding utf8' in content
    assert "Use the resolved match's `language` value for the `search_language` field" in content
    assert 'city_entry        = "<city>|<country_code>"' in content
    assert "city_country_code" in content
    assert "tgt_by_country = output.suggested_queries.targeted_by_country" in content
    assert "target = tgt_by_country[city_country_code]" in content
    assert "target.template.format(city=city_name, date=target.date)" in content
    assert "max_city_options = output.config.max_city_options" in content
    assert "max_trip_options = output.config.max_trip_options" in content
    assert "`searches_used = 0`, `fetches_used = 0`" in content
    assert "`phase_searches = 0`, `phase_fetches = 0`, `phase_new_events = 0`" in content
    assert "Before every WebSearch or WebFetch:" in content
    assert "budget_checkpoint" not in content
    assert "`log-action --action phase_summary`" in content
    assert "`log-action --action run_complete`" in content
    assert "unique-event set keyed by `(event_name, city, start_date)`" in content
    assert "runtime dedupe rule `(event_name, city, start_date)`" in content
    assert "Do **not** call `save` during phases" in content
    assert "After each phase A/B/C/D:" in content
    assert "`save --events` / `save --events-file` must receive a **JSON array**" in content
    assert "`format-message --city-events` / `--city-events-file` must receive a **JSON array** of event dicts." in content
    assert "`format-message --trips` / `--trips-file` must receive a **JSON array** of trip dicts." in content
    assert "`event_name`, `location_name`, `start_date`, optional `end_date`, `time_info`" in content
    assert "`name`, `route`, `events`, `timing`, optional `url`." in content
    assert "Pass the selected top home-city event dicts directly as the `city-events` JSON array" in content
    assert "top `max_city_options` in home city + up to `max_trip_options` road trip options" in content
    assert "Build up to `max_trip_options` options" in content
    assert "Label them `01` through `NN` in the final message only." in content
    assert "Do not patch behavior ad hoc during execution." in content
    assert 'The `format-message` response returns both:' in content
    assert '`preview`: plain-text digest preview for showing in the conversation' in content
    assert "Do **not** read the written HTML file back into the conversation." in content
    assert "#### 2.1 Budget and counters" in content
    assert "#### 2.2 Reusable protocols" in content
    assert "#### 2.3 Log and payload patterns" in content
    assert "#### 2.4 Phase A -- Broad sweep (3-5 searches)" in content
    assert "#### 2.5 Phase B -- Aggregator deep-dive (shares Phase A's fetch budget)" in content
    assert "#### 2.6 Phase C -- Targeted city searches" in content
    assert "#### 2.7 Phase D -- Verification (1-5 fetches)" in content
    assert "#### 2.8 Save discovered events" in content
    assert "**SEARCH STEP [SEARCH_STEP]** -- execute this sequence for every WebSearch:" in content
    assert "**FETCH STEP [FETCH_STEP]** -- execute this sequence for every WebFetch:" in content
    assert "For every WebSearch, execute `SEARCH_STEP` exactly as written." in content
    assert "Do not continue until `SEARCH_STEP` is complete." in content
    assert "Use only `FETCH_STEP` for URL/page extraction in Phase B and Phase D." in content
    assert "**Tier 1 loop** -- for each uncovered tier1 city:" in content
    assert "**Tier 2 loop** -- only if `searches_used < max_searches * 0.6`:" in content
    assert "**Tier 3 loop** -- only if `searches_used < max_searches * 0.8`:" in content
    assert "**Hard rules for this step:**" in content
    assert "A -> B -> C -> D -> save -> cache-query -> score -> format/send" in content
    assert "Do **not** perform any WebSearch or WebFetch after Phase D completes." in content
    assert "Do **not** call `cache-query` before `save` except in the documented `--cached-only` path." in content
    assert "Every phase must end with either a `skip` log or a `phase_summary` log before moving on." in content
    assert "one-call transport files for CLI payloads" in content
    assert "not persistent cache" in content
    assert "always write a fresh" in content
    assert "Do NOT batch log-search calls at the end of a phase." in content
    assert "Do NOT re-fetch a URL already fetched in this run." in content
    assert "After Phase A completes, continue only to Phase B." in content
    assert "Phase B is URL-based extraction. Use only `FETCH_STEP` for queued page work, not ad hoc substitute search-only flows." in content
    assert "Follow the emitted tier order exactly." in content
    assert "Do not start Phase D until Phase C ends with `phase_summary` or `skip`." in content
    assert "After Phase D completes, discovery work is over. Do not return to targeted or broad searching." in content
    assert "Discovery must already be complete before this step starts." in content
    assert '"name":   "Łódź Day Trip"' in content
    assert '"name":   "A. Łódź Day Trip"' not in content
    assert "After the send/no-send outcome is known, **always** log `run_complete`:" in content
    assert 'where `saturday` is the ISO Saturday date from `init-skill` (for example `2026-04-04`)' in content
    assert '--detail-file "$detail_json_path"' in content
    assert "city_meta" not in content
    assert "targeted_template" not in content
    assert "choose the targeted-search language with this mapping" not in content

    assert "setup --json '{\"" not in content
    assert "--cities '[\"" not in content
    assert "--detail '{\"" not in content
    assert "--events '<JSON array>'" not in content
    assert "--city-events '<top_3_city_events_json>'" not in content
    assert "--trips '<trip_options_json>'" not in content
    assert '--city-events-file "$city_events_json_path"' in content
    assert "A through J" not in content
    assert "top 3 in home city + up to 10 road trip options" not in content
    assert 'python -m weekend_scout setup --json "$setup_json"' not in content
    assert '--cities "$cities_json"' not in content
    assert '--detail "$detail_json"' not in content
    assert '--events "$events_json"' not in content
    assert '--city-events "$city_events_json"' not in content
    assert '--trips "$trips_json"' not in content


def test_template_setup_uses_language_placeholder_and_pipe_tiers():
    content = _read_text(Path("skill_template/weekend-scout.template.md"))

    assert "python -m weekend_scout init-skill [--city CITY] [--radius KM]" in content
    assert "python -m weekend_scout init [--city CITY] [--radius KM]" not in content
    assert "The `init-skill` JSON contains all config fields you need" in content
    assert 'search_language":"<language>"' in content
    assert 'search_language":"<lang>"' not in content
    assert '"<city>|<country_code>"' in content
    assert "split each tier entry once" in content
    assert "cached_count = output.cached.count" in content
    assert "cached_covered_cities = output.cached.covered_cities" in content
    assert "cached_city_counts = output.cached.city_counts" in content
    assert "cached = output.cached_events" not in content
    assert 'python -m weekend_scout cache-query --date "<saturday>"' in content
    assert "Here, `saturday` means `output.config.target_weekend.saturday` in ISO format (`YYYY-MM-DD`)," in content
    assert "Store that result as `cached_full`, then proceed directly to Step 3 using only `cached_full`." in content
    assert "Before Step 3, load the full cached weekend event rows once with:" in content
    assert "Here, `saturday` means the same ISO Saturday date from `init-skill`" in content
    assert "Store that result as `cached_full` and combine `cached_full` + newly saved events for ranking." in content
    assert "max_city_options = output.config.max_city_options" in content
    assert "max_trip_options = output.config.max_trip_options" in content
    assert "**Normal run rule:**" in content
    assert "Track usage mentally" not in content
    assert "`searches_used = 0`, `fetches_used = 0`" in content
    assert "`phase_searches = 0`, `phase_fetches = 0`, `phase_new_events = 0`" in content
    assert "Before every WebSearch or WebFetch:" in content
    assert "#### 2.1 Budget and counters" in content
    assert "#### 2.2 Reusable protocols" in content
    assert "#### 2.3 Log and payload patterns" in content
    assert "#### 2.4 Phase A -- Broad sweep (3-5 searches)" in content
    assert "#### 2.5 Phase B -- Aggregator deep-dive (shares Phase A's fetch budget)" in content
    assert "#### 2.6 Phase C -- Targeted city searches" in content
    assert "#### 2.7 Phase D -- Verification (1-5 fetches)" in content
    assert "#### 2.8 Save discovered events" in content
    assert "**SEARCH STEP [SEARCH_STEP]** -- execute this sequence for every WebSearch:" in content
    assert "**FETCH STEP [FETCH_STEP]** -- execute this sequence for every WebFetch:" in content
    assert "For every WebSearch, execute `SEARCH_STEP` exactly as written." in content
    assert "Do not continue until `SEARCH_STEP` is complete." in content
    assert "Use only `FETCH_STEP` for URL/page extraction in Phase B and Phase D." in content
    assert "**Tier 1 loop** -- for each uncovered tier1 city:" in content
    assert "**Tier 2 loop** -- only if `searches_used < max_searches * 0.6`:" in content
    assert "**Tier 3 loop** -- only if `searches_used < max_searches * 0.8`:" in content
    assert "**Hard rules for this step:**" in content
    assert "A -> B -> C -> D -> save -> cache-query -> score -> format/send" in content
    assert "Do **not** perform any WebSearch or WebFetch after Phase D completes." in content
    assert "Do **not** call `cache-query` before `save` except in the documented `--cached-only` path." in content
    assert "Every phase must end with either a `skip` log or a `phase_summary` log before moving on." in content
    assert "one-call transport files for CLI payloads" in content
    assert "not persistent cache" in content
    assert "always write a fresh" in content
    assert "Do NOT batch log-search calls at the end of a phase." in content
    assert "Do NOT re-fetch a URL already fetched in this run." in content
    assert "After Phase A completes, continue only to Phase B." in content
    assert "Phase B is URL-based extraction. Use only `FETCH_STEP` for queued page work, not ad hoc substitute search-only flows." in content
    assert "Follow the emitted tier order exactly." in content
    assert "Do not start Phase D until Phase C ends with `phase_summary` or `skip`." in content
    assert "After Phase D completes, discovery work is over. Do not return to targeted or broad searching." in content
    assert "Discovery must already be complete before this step starts." in content
    assert "budget_checkpoint" not in content
    assert "`log-action --action phase_summary`" in content
    assert "`log-action --action run_complete`" in content
    assert "unique-event set keyed by `(event_name, city, start_date)`" in content
    assert "runtime dedupe rule `(event_name, city, start_date)`" in content
    assert "Do **not** call `save` during phases" in content
    assert "`save --events` / `save --events-file` must receive a **JSON array**" in content
    assert "`format-message --city-events` / `--city-events-file` must receive a **JSON array** of event dicts." in content
    assert "`format-message --trips` / `--trips-file` must receive a **JSON array** of trip dicts." in content
    assert '`preview`: plain-text digest preview for showing in the conversation' in content
    assert "Do **not** read the written HTML file back into the conversation." in content
    assert "top `max_city_options` in home city + up to `max_trip_options` road trip options" in content
    assert "Build up to `max_trip_options` options" in content
    assert "Label them `01` through `NN` in the final message only." in content
    assert "--city-events '<top_city_events_json>'" in content
    assert '"name":   "Łódź Day Trip"' in content
    assert '"name":   "A. Łódź Day Trip"' not in content
    assert '"sent": <true|false>' in content
    assert '"send_reason": "<sent|telegram_not_configured|send_failed>"' in content
    assert '"served_marked": <true|false>' in content
    assert '"uncovered_tier1": ["<city>", "<city>"]' in content
    assert "city_meta" not in content
    assert "targeted_by_country" in content
    assert "targeted_template" not in content
    assert "choose the targeted-search language with this mapping" not in content
    assert "A through J" not in content
    assert "top 3 in home city + up to 10 road trip options" not in content
