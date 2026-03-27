"""CLI entry point for Weekend Scout.

Provides subcommands:
  setup             -- interactive first-run setup wizard
  config            -- show current configuration
  init              -- load config + cities + cache for a scout run (JSON)
  save              -- save discovered events to cache
  send              -- send formatted message to Telegram
  cache-query       -- query cached events for a weekend date
  log-search        -- log a completed search to the search log
  cache-mark-served -- mark events as sent to Telegram
  run               -- full automated run
"""

import argparse
import json
import sys


def cmd_setup(args: argparse.Namespace) -> None:
    """Run interactive setup wizard."""
    from weekend_scout.config import run_setup_wizard
    run_setup_wizard()


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
            print(json.dumps({"error": f"Provide a value: config {key} <value>"}))
            sys.exit(1)
        # Coerce type to match existing value
        existing = config[key]
        if isinstance(existing, bool):
            value = value.lower() in ("true", "1", "yes")
        elif isinstance(existing, int):
            value = int(value)
        elif isinstance(existing, float):
            value = float(value)
        config[key] = value
        save_config(config)
        print(json.dumps({"set": {key: value}}))
    else:
        print(json.dumps(config, indent=2, ensure_ascii=False))


def cmd_init(args: argparse.Namespace) -> None:
    """Load config, city list, cache state, and query suggestions. Output JSON."""
    from weekend_scout.config import load_config
    from weekend_scout.cities import get_city_list, generate_broad_queries, generate_targeted_queries
    from weekend_scout.cache import query_events, get_searches_this_week
    from weekend_scout.distance import next_weekend_dates

    config = load_config()

    # Allow CLI overrides
    if args.city:
        config["home_city"] = args.city
    if args.radius:
        config["radius_km"] = int(args.radius)

    saturday, sunday = next_weekend_dates()
    target_weekend = {"saturday": saturday, "sunday": sunday}

    cities = get_city_list(config)
    cached_events = query_events(config, saturday)
    searches_this_week = get_searches_this_week(config, saturday)
    broad_queries = generate_broad_queries(config, saturday, sunday)
    targeted_queries = generate_targeted_queries(
        cities.get("tier1", []), config.get("search_language", "en"), saturday
    )

    output = {
        "config": {
            "home_city": config.get("home_city"),
            "radius_km": config.get("radius_km"),
            "search_language": config.get("search_language"),
            "precise_location": config.get("precise_location"),
            "target_weekend": target_weekend,
        },
        "cities": cities,
        "cached_events": cached_events,
        "searches_this_week": searches_this_week,
        "suggested_queries": {
            "broad": broad_queries,
            "targeted": targeted_queries,
        },
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_save(args: argparse.Namespace) -> None:
    """Save events (JSON array) to the cache."""
    from weekend_scout.config import load_config
    from weekend_scout.cache import save_events

    config = load_config()
    events = json.loads(args.events)
    saved, skipped = save_events(config, events)
    print(json.dumps({"saved": saved, "skipped": skipped}))


def cmd_send(args: argparse.Namespace) -> None:
    """Send a formatted message to Telegram."""
    from weekend_scout.config import load_config
    from weekend_scout.telegram import send_telegram

    config = load_config()

    if args.file:
        from pathlib import Path
        message = Path(args.file).read_text(encoding="utf-8")
    elif args.message:
        message = args.message
    else:
        print(json.dumps({"error": "Provide --message or --file"}))
        sys.exit(1)

    success = send_telegram(config, message)
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
    )
    print(json.dumps({"logged": True}))


def cmd_cache_mark_served(args: argparse.Namespace) -> None:
    """Mark all events for the given weekend date as served."""
    from weekend_scout.config import load_config
    from weekend_scout.cache import mark_served

    config = load_config()
    count = mark_served(config, args.date)
    print(json.dumps({"marked": count}))


def cmd_download_data(args: argparse.Namespace) -> None:
    """Download and unzip GeoNames cities15000.zip into data/."""
    from weekend_scout.cities import download_geonames
    path = download_geonames(force=args.force)
    print(json.dumps({"path": str(path)}))


def cmd_run(args: argparse.Namespace) -> None:
    """Print instructions for a manual /weekend-scout run."""
    print(
        "Run /weekend-scout in Claude Code to start an automated scout.\n"
        "Full programmatic automation (cron + Claude Code SDK) is planned for a future release."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weekend_scout",
        description="Weekend Scout -- discover outdoor events near your city",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # setup
    sub.add_parser("setup", help="Interactive first-run setup wizard")

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

    # send
    p_send = sub.add_parser("send", help="Send formatted message to Telegram")
    grp = p_send.add_mutually_exclusive_group(required=True)
    grp.add_argument("--message", help="Message text")
    grp.add_argument("--file", help="Path to file containing message text")

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

    # cache-mark-served
    p_cms = sub.add_parser("cache-mark-served", help="Mark weekend events as served")
    p_cms.add_argument("--date", required=True, help="ISO date (Saturday of target weekend)")

    # download-data
    p_dd = sub.add_parser("download-data", help="Download GeoNames cities15000.zip into data/")
    p_dd.add_argument("--force", action="store_true", help="Re-download even if file already exists")

    # run
    sub.add_parser("run", help="Full automated run (instructions)")

    return parser


COMMANDS = {
    "setup": cmd_setup,
    "config": cmd_config,
    "init": cmd_init,
    "save": cmd_save,
    "send": cmd_send,
    "cache-query": cmd_cache_query,
    "log-search": cmd_log_search,
    "cache-mark-served": cmd_cache_mark_served,
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
