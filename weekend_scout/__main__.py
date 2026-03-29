"""CLI entry point for Weekend Scout.

Provides subcommands:
  setup             -- interactive first-run setup wizard
  config            -- show current configuration
  init              -- load config + cities + cache for a scout run (JSON)
  find-city         -- look up a city in the GeoNames database
  save              -- save discovered events to cache
  send              -- send formatted message to Telegram
  cache-query       -- query cached events for a weekend date
  log-search        -- log a completed search to the search log
  cache-mark-served -- mark events as sent to Telegram
  format-message    -- format scout message and write to file
  run               -- full automated run
"""

import argparse
import json
import sys


def cmd_setup(args: argparse.Namespace) -> None:
    """Run interactive setup wizard, or apply a JSON config payload directly."""
    if args.json_data:
        from weekend_scout.config import load_config, save_config, get_config_path, get_cache_dir
        from pathlib import Path as _P
        incoming = json.loads(args.json_data)
        old_config = load_config()
        config = dict(old_config)
        config.update(incoming)
        save_config(config)
        # Invalidate city cache when city name or coordinates change
        old_city = old_config.get("home_city", "")
        new_city = config.get("home_city", "")
        old_coords = old_config.get("home_coordinates", {})
        new_coords = config.get("home_coordinates", {})
        if old_city != new_city or old_coords != new_coords:
            cache_dir = get_cache_dir(config)
            for city in {old_city, new_city} - {""}:
                for radius in {old_config.get("radius_km", 150), config.get("radius_km", 150)}:
                    stale = _P(cache_dir) / f"cities_{city}_{radius}.json"
                    if stale.exists():
                        stale.unlink()
        print(json.dumps({"saved": True, "config_path": str(get_config_path())}, ensure_ascii=False))
    else:
        from weekend_scout.config import run_setup_wizard
        run_setup_wizard()


def cmd_find_city(args: argparse.Namespace) -> None:
    """Look up a city in the GeoNames database and return matching entries."""
    from weekend_scout.cities import find_city_candidates, ensure_geonames

    geonames_path = ensure_geonames()
    matches = find_city_candidates(args.name, geonames_path, country_filter=args.country)
    print(json.dumps({"matches": matches}, ensure_ascii=False))


def cmd_config(args: argparse.Namespace) -> None:
    """Print current configuration as JSON, or set a key."""
    from weekend_scout.config import load_config, save_config
    config = load_config()

    if args.key:
        key = args.key
        value = args.value
        if key not in config:
            print(json.dumps({"error": f"Unknown config key: {key}"}))
            sys.exit(1)
        if value is None:
            print(json.dumps({key: config[key]}, ensure_ascii=False))
            return
        # Coerce type to match existing value
        existing = config[key]
        try:
            if isinstance(existing, bool):
                value = value.lower() in ("true", "1", "yes")
            elif isinstance(existing, int):
                value = int(value)
            elif isinstance(existing, float):
                value = float(value)
            elif isinstance(existing, (dict, list)):
                value = json.loads(value)
                if not isinstance(value, type(existing)):
                    raise ValueError
        except (ValueError, TypeError, json.JSONDecodeError):
            print(json.dumps({"error": f"Invalid value for {key}: expected {type(existing).__name__}"}))
            sys.exit(1)
        config[key] = value
        save_config(config)
        print(json.dumps({"set": {key: value}}))
    else:
        print(json.dumps(config, indent=2, ensure_ascii=False))


def cmd_init(args: argparse.Namespace) -> None:
    """Load config, city list, cache state, and query suggestions. Output JSON."""
    import datetime
    from weekend_scout.config import load_config, get_config_path, COUNTRY_CODE_MAP, COUNTRY_LANGUAGE_MAP
    from weekend_scout.cities import (
        get_city_list, generate_broad_queries, generate_targeted_template,
        find_city_coords, ensure_geonames,
    )
    from weekend_scout.cache import query_events, get_searches_this_week, log_action
    from weekend_scout.distance import next_weekend_dates

    config = load_config()

    # Guard: unconfigured state — home_city is required
    if not config.get("home_city"):
        print(json.dumps({
            "needs_setup": True,
            "message": "Weekend Scout is not configured. Run: python -m weekend_scout setup",
            "config_path": str(get_config_path()),
        }, ensure_ascii=False))
        return

    # Allow CLI overrides
    city_geocoded: bool | None = None
    if args.city:
        config["home_city"] = args.city
        geonames_path = ensure_geonames()
        if geonames_path.exists():
            city_data = find_city_coords(args.city, geonames_path)
            if city_data:
                config["home_coordinates"] = {"lat": city_data["lat"], "lon": city_data["lon"]}
                country = COUNTRY_CODE_MAP.get(city_data["country"], "")
                if country:
                    config["home_country"] = country
                    config["search_language"] = COUNTRY_LANGUAGE_MAP.get(country, "en")
                city_geocoded = True
            else:
                city_geocoded = False

    if args.radius:
        try:
            config["radius_km"] = int(args.radius)
        except ValueError:
            print(json.dumps({"error": "radius must be an integer"}))
            sys.exit(1)

    saturday, sunday = next_weekend_dates()
    target_weekend = {"saturday": saturday, "sunday": sunday}
    run_id = f"{saturday}_{datetime.datetime.now().strftime('%H%M')}"

    # Skip city list when coordinates are unset (0,0 sentinel) to avoid a
    # pointless GeoNames parse and prevent overwriting a valid cache with
    # an empty one.
    coords = config.get("home_coordinates", {})
    coords_valid = not (coords.get("lat", 0.0) == 0.0 and coords.get("lon", 0.0) == 0.0)

    if coords_valid:
        cities = get_city_list(config, bypass_cache=args.city is not None)
    else:
        cities = {"tier1": [], "tier2": [], "tier3": []}

    cached_events = query_events(config, saturday)
    searches_this_week = get_searches_this_week(config, saturday)
    broad_result = generate_broad_queries(config, saturday, sunday)
    targeted_tmpl = generate_targeted_template(config.get("search_language", "en"))

    config_block: dict = {
        "home_city": config.get("home_city"),
        "home_country": config.get("home_country", ""),
        "radius_km": config.get("radius_km"),
        "search_language": config.get("search_language"),
        "target_weekend": target_weekend,
        "max_searches": config.get("max_searches", 30),
        "max_fetches": config.get("max_fetches", 30),
    }
    if city_geocoded is not None:
        config_block["city_geocoded"] = city_geocoded

    output = {
        "run_id": run_id,
        "config": config_block,
        "cities": cities,
        "cached_events": cached_events,
        "searches_this_week": searches_this_week,
        "suggested_queries": {
            "vars": broad_result["vars"],
            "broad": broad_result["templates"],
            "targeted_template": targeted_tmpl,
        },
    }
    if not coords_valid:
        output["warnings"] = ["coordinates_not_set: nearby city suggestions disabled"]
    log_action(config, "run_init", run_id=run_id, target_weekend=saturday,
               detail={"home_city": config.get("home_city"),
                       "radius_km": config.get("radius_km"),
                       "cached_count": len(cached_events),
                       "tier1": cities.get("tier1", [])})
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_save(args: argparse.Namespace) -> None:
    """Save events (JSON array) to the cache."""
    from weekend_scout.config import load_config
    from weekend_scout.cache import save_events, log_action

    config = load_config()
    events = json.loads(args.events)
    saved, skipped = save_events(config, events)
    log_action(config, "events_saved", run_id=args.run_id,
               detail={"saved": saved, "skipped": skipped})
    print(json.dumps({"saved": saved, "skipped": skipped}))


def cmd_send(args: argparse.Namespace) -> None:
    """Send a formatted message to Telegram."""
    from weekend_scout.config import load_config
    from weekend_scout.telegram import send_telegram
    from weekend_scout.cache import log_action

    config = load_config()

    if args.file:
        from pathlib import Path
        try:
            message = Path(args.file).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(json.dumps({"error": f"File not found: {args.file}"}))
            sys.exit(1)
    elif args.message:
        message = args.message
    else:
        print(json.dumps({"error": "Provide --message or --file"}))
        sys.exit(1)

    success = send_telegram(config, message)
    log_action(config, "telegram_send", run_id=args.run_id,
               detail={"success": success, "char_count": len(message)})
    print(json.dumps({"sent": success}))


def cmd_cache_query(args: argparse.Namespace) -> None:
    """Query cached events for the weekend containing the given date."""
    from weekend_scout.config import load_config
    from weekend_scout.cache import query_events

    config = load_config()
    events = query_events(config, args.date)
    print(json.dumps(events, indent=2, ensure_ascii=False))


def cmd_log_search(args: argparse.Namespace) -> None:
    """Log a completed web search to the search log."""
    from weekend_scout.config import load_config
    from weekend_scout.cache import log_search

    config = load_config()
    cities = json.loads(args.cities) if args.cities else []
    log_search(
        config=config,
        query=args.query,
        target_weekend=args.target_weekend,
        result_count=args.result_count,
        cities_covered=cities,
        phase=args.phase,
        run_id=args.run_id,
        events_discovered=args.events_discovered,
    )
    print(json.dumps({"logged": True}))


def cmd_log_action(args: argparse.Namespace) -> None:
    """Append a structured action log entry to action_log.jsonl."""
    from weekend_scout.config import load_config
    from weekend_scout.cache import log_action

    config = load_config()
    detail = json.loads(args.detail) if args.detail else {}
    log_action(
        config,
        args.action,
        phase=args.phase,
        detail=detail,
        run_id=args.run_id,
        source=args.source,
        target_weekend=args.target_weekend,
    )
    print(json.dumps({"logged": True}))


def cmd_cache_mark_served(args: argparse.Namespace) -> None:
    """Mark all events for the given weekend date as served."""
    from weekend_scout.config import load_config
    from weekend_scout.cache import mark_served, log_action

    config = load_config()
    count = mark_served(config, args.date)
    log_action(config, "events_served", target_weekend=args.date, detail={"count": count})
    print(json.dumps({"marked": count}))


def cmd_download_data(args: argparse.Namespace) -> None:
    """Download and unzip GeoNames cities15000.zip into the cache directory."""
    from weekend_scout.cities import download_geonames
    path = download_geonames(force=args.force)
    print(json.dumps({"path": str(path)}))


def cmd_format_message(args: argparse.Namespace) -> None:
    """Format a scout message and write it to a file."""
    from pathlib import Path
    from weekend_scout.config import load_config, get_cache_dir
    from weekend_scout.telegram import format_scout_message
    from weekend_scout.cache import log_action

    config = load_config()
    city_events = json.loads(args.city_events)
    trips = json.loads(args.trips)
    low_results = args.low_results.lower() in ("true", "1", "yes") if args.low_results else False
    msg = format_scout_message(
        config.get("home_city", ""),
        args.saturday,
        args.sunday,
        city_events,
        trips,
        low_results_hint=low_results,
    )
    output_path = Path(args.output) if args.output else get_cache_dir(config) / "scout_message.txt"
    output_path.write_text(msg, encoding="utf-8")
    log_action(config, "message_formatted", run_id=args.run_id,
               target_weekend=args.saturday,
               detail={"city_events": len(city_events), "trips": len(trips),
                       "char_count": len(msg)})
    print(json.dumps({"written": str(output_path)}))


def cmd_run(args: argparse.Namespace) -> None:
    """Print instructions for a manual /weekend-scout run."""
    print(json.dumps({
        "message": "Run /weekend-scout in Claude Code to start an automated scout.",
        "automation": "planned",
    }))


_INSTALL_TARGETS: dict[str, "Path"] = {}


def _get_install_targets() -> dict[str, "Path"]:
    from pathlib import Path as _P
    return {
        "claude-code": _P.home() / ".claude"   / "skills" / "weekend-scout",
        "codex":       _P.home() / ".codex"    / "skills" / "weekend-scout",
        "openclaw":    _P.home() / ".openclaw" / "skills" / "weekend-scout",
    }


def _resolve_platforms(platform_arg: str | None) -> list[str]:
    """Determine which platforms to install for."""
    targets = _get_install_targets()
    if platform_arg == "all":
        return list(targets.keys())
    if platform_arg:
        return [platform_arg]
    # Auto-detect: check which platform base dirs exist (e.g. ~/.claude/)
    detected = [
        name for name, target in targets.items()
        if target.parent.parent.exists()
    ]
    return detected if detected else ["claude-code"]


def _copy_tree(src: "Path", dst: "Path") -> None:
    """Recursively copy all files from src to dst."""
    import shutil as _shutil
    for item in src.rglob("*"):
        if item.is_file():
            rel = item.relative_to(src)
            target_file = dst / rel
            target_file.parent.mkdir(parents=True, exist_ok=True)
            _shutil.copy2(item, target_file)


def cmd_install_skill(args: argparse.Namespace) -> None:
    """Copy bundled SKILL.md from the installed package to the global skills dir."""
    from pathlib import Path
    skill_data_dir = Path(__file__).resolve().parent / "skill_data"
    if not skill_data_dir.exists():
        print(json.dumps({"error": "skill_data directory not found in package"}))
        sys.exit(1)

    platforms = _resolve_platforms(args.platform)
    install_targets = _get_install_targets()

    results = []
    for platform in platforms:
        source_dir = skill_data_dir / platform
        if not source_dir.exists():
            results.append({"platform": platform, "status": "skipped",
                            "reason": f"no skill data for {platform}"})
            continue
        target_dir = install_targets[platform]
        target_dir.mkdir(parents=True, exist_ok=True)
        _copy_tree(source_dir, target_dir)
        results.append({"platform": platform, "status": "installed",
                        "path": str(target_dir)})

    print(json.dumps({"installed": results}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weekend_scout",
        description="Weekend Scout -- discover outdoor events near your city",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # setup
    p_setup = sub.add_parser("setup", help="Interactive first-run setup wizard")
    p_setup.add_argument(
        "--json", dest="json_data", default=None, metavar="JSON",
        help="Apply JSON config payload directly (no wizard)",
    )

    # config
    p_cfg = sub.add_parser("config", help="Show or set configuration")
    p_cfg.add_argument("key", nargs="?", help="Config key to set (omit to show all)")
    p_cfg.add_argument("value", nargs="?", help="Value to set")

    # init
    p_init = sub.add_parser("init", help="Load config + cities + cache for a scout run")
    p_init.add_argument("--city", help="Override home city")
    p_init.add_argument("--radius", help="Override search radius in km")

    # save
    p_save = sub.add_parser("save", help="Save discovered events to cache")
    p_save.add_argument("--events", required=True, help="JSON array of event objects")
    p_save.add_argument("--run-id", default=None, dest="run_id", help="Run identifier from init")

    # send
    p_send = sub.add_parser("send", help="Send formatted message to Telegram")
    grp = p_send.add_mutually_exclusive_group(required=True)
    grp.add_argument("--message", help="Message text")
    grp.add_argument("--file", help="Path to file containing message text")
    p_send.add_argument("--run-id", default=None, dest="run_id",
                        help="Run identifier from init")

    # cache-query
    p_cq = sub.add_parser("cache-query", help="Query cached events for a weekend date")
    p_cq.add_argument("--date", required=True, help="ISO date (Saturday of target weekend)")

    # log-search
    p_ls = sub.add_parser("log-search", help="Log a completed search")
    p_ls.add_argument("--query", required=True, help="Search query string")
    p_ls.add_argument("--target-weekend", required=True, help="ISO date of target Saturday")
    p_ls.add_argument("--result-count", type=int, default=0, help="Number of results returned")
    p_ls.add_argument("--cities", help="JSON array of city names covered")
    p_ls.add_argument("--phase", default="broad", choices=["broad", "aggregator", "targeted", "verification"])
    p_ls.add_argument("--run-id", default=None, dest="run_id", help="Run identifier from init")
    p_ls.add_argument("--events-discovered", type=int, default=0, dest="events_discovered",
                      help="Number of events extracted from this search")

    # log-action
    p_la = sub.add_parser("log-action", help="Append a structured action log entry")
    p_la.add_argument("--action", required=True, help="Action type (phase_start, score_summary, ...)")
    p_la.add_argument("--phase", default=None, help="Search phase context (A, B, C, D, ...)")
    p_la.add_argument("--detail", default=None, help="JSON object with action-specific data")
    p_la.add_argument("--run-id", default=None, dest="run_id", help="Run identifier from init")
    p_la.add_argument("--source", default="skill", help="Source: skill or python")
    p_la.add_argument("--target-weekend", default=None, dest="target_weekend", help="ISO Saturday date")

    # cache-mark-served
    p_cms = sub.add_parser("cache-mark-served", help="Mark weekend events as served")
    p_cms.add_argument("--date", required=True, help="ISO date (Saturday of target weekend)")

    # format-message
    p_fm = sub.add_parser("format-message", help="Format scout message and write to file")
    p_fm.add_argument("--saturday", required=True, help="ISO date of target Saturday")
    p_fm.add_argument("--sunday", required=True, help="ISO date of target Sunday")
    p_fm.add_argument("--city-events", default="[]", help="JSON array of up to 3 event dicts")
    p_fm.add_argument("--trips", default="[]", help="JSON array of trip option dicts")
    p_fm.add_argument("--output", default=None, help="Output file path (default: app cache dir)")
    p_fm.add_argument("--low-results", default=None, dest="low_results",
                      help="Pass 'true' to append a budget-increase hint to the message")
    p_fm.add_argument("--run-id", default=None, dest="run_id",
                      help="Run identifier from init")

    # install-skill
    p_is = sub.add_parser(
        "install-skill",
        help="Copy bundled SKILL.md from the installed package to your global skills directory",
    )
    p_is.add_argument(
        "--platform",
        choices=["claude-code", "codex", "openclaw", "all"],
        default=None,
        help="Target platform (auto-detected if not specified)",
    )

    # find-city
    p_fc = sub.add_parser("find-city", help="Look up a city in the GeoNames database")
    p_fc.add_argument("--name", required=True, help="City name to search")
    p_fc.add_argument("--country", default=None, help="Optional country filter (full English name)")

    # download-data
    p_dd = sub.add_parser("download-data", help="Download GeoNames cities15000.zip into cache dir")
    p_dd.add_argument("--force", action="store_true", help="Re-download even if file already exists")

    # run
    sub.add_parser("run", help="Full automated run (instructions)")

    return parser


COMMANDS = {
    "setup": cmd_setup,
    "config": cmd_config,
    "init": cmd_init,
    "find-city": cmd_find_city,
    "save": cmd_save,
    "send": cmd_send,
    "cache-query": cmd_cache_query,
    "log-search": cmd_log_search,
    "log-action": cmd_log_action,
    "cache-mark-served": cmd_cache_mark_served,
    "format-message": cmd_format_message,
    "install-skill": cmd_install_skill,
    "download-data": cmd_download_data,
    "run": cmd_run,
}


def main() -> None:
    # Ensure Unicode output works on Windows (cp1251/cp850 consoles)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()
    handler = COMMANDS.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
