# Codex Transport Rules

These examples are transport-only snippets. They show how to write fresh payload files and pass
`--*-file` flags. They are **not** full scout-run command shapes; the authoritative run commands
live in `onboarding.md`, `search-workflow.md`, `scoring-and-trips.md`, and `delivery-and-audit.md`.

<json-file-rule>
- For any `python -m weekend_scout ...` command that passes structured JSON, write the payload to a fresh UTF-8 file in `.weekend_scout/cache/`, then pass the matching `--*-file` flag.
- Use `_tmp_*.tmp` filenames only for one-call transport payloads.
- The CLI auto-deletes `_tmp_*.tmp` files after successful commands, so always write a fresh file immediately before the matching CLI call.
- Reuse the same cache directory, but do not assume any earlier `_tmp_*.tmp` file still exists.
</json-file-rule>

<recommended-paths>
- `setup_json_path` -> `_tmp_setup.tmp`
- `cities_json_path` -> `_tmp_cities.tmp`
- `detail_json_path` -> `_tmp_detail.tmp`
- `events_json_path` -> `_tmp_events.tmp`
- `city_events_json_path` -> `_tmp_city_events.tmp`
- `trips_json_path` -> `_tmp_trips.tmp`
- `covered_cities_path` -> `_tmp_covered_cities.tmp`
- `uncovered_tier1_path` -> `_tmp_uncovered_tier1.tmp`
</recommended-paths>

<powershell-example>
```powershell
$cache_dir = '.weekend_scout/cache'
New-Item -ItemType Directory -Force -Path $cache_dir | Out-Null
$payload_path = Join-Path $cache_dir '_tmp_detail.tmp'
@'
{"reason":"all_confirmed"}
'@ | Set-Content -LiteralPath $payload_path -Encoding utf8
python -m weekend_scout log-action --action skip --detail-file "$payload_path"
```
</powershell-example>

<posix-example>
```bash
cache_dir=".weekend_scout/cache"
mkdir -p "$cache_dir"
payload_path="$cache_dir/_tmp_detail.tmp"
cat > "$payload_path" <<'EOF'
{"reason":"all_confirmed"}
EOF
python -m weekend_scout log-action --action skip --detail-file "$payload_path"
```
</posix-example>
