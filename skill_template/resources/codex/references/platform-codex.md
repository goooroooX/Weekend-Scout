# Codex Transport Rules

<json-file-rule>
- For any `python -m weekend_scout ...` command that passes structured JSON, write the payload to a fresh UTF-8 file in `.weekend_scout/cache/`, then pass the matching `--*-file` flag.
- Use `_tmp_*.tmp` filenames only for one-call transport payloads.
- The CLI auto-deletes `_tmp_*.tmp` files after successful commands, so always write a fresh file immediately before the matching CLI call.
- Reuse the same cache directory, but do not assume any earlier `_tmp_*.tmp` file still exists.
</json-file-rule>

<recommended-paths>
- `setup_json_path`
- `cities_json_path`
- `detail_json_path`
- `events_json_path`
- `city_events_json_path`
- `trips_json_path`
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
