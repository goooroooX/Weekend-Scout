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
</recommended-paths>

<approval-retry-rule>
- Only request Codex approval / outside-sandbox execution when a stage reference explicitly authorizes it.
- For Telegram resend fallback, rerun the exact same `python -m weekend_scout send ...` command once with approval-gated outside-sandbox execution.
- Do not change arguments, do not rerun `format-message`, and do not broaden this to any other command or failure class.
- If approval is denied, or the retried command still returns `{"sent": false, ...}`, stop retrying and treat that result as final.
</approval-retry-rule>

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

<setup-powershell-example>
Use this exact pattern for onboarding setup payloads:

```powershell
$cache_dir = '.weekend_scout/cache'
New-Item -ItemType Directory -Force -Path $cache_dir | Out-Null
$setup_json_path = Join-Path $cache_dir '_tmp_setup.tmp'
@'
{"home_city":"<city>","home_country":"<country>","home_coordinates":{"lat":<lat>,"lon":<lon>},"radius_km":<radius>,"search_language":"<language>"}
'@ | Set-Content -LiteralPath $setup_json_path -Encoding utf8
python -m weekend_scout setup --json-file "$setup_json_path"
```
</setup-powershell-example>

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
