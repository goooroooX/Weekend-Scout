# Weekend Scout -- Design Changes Log

Changes from the original design (docs/weekend-scout-mvp-design.md).

| Date | Design Section | Change | Reason |
|------|---------------|--------|--------|
| 2026-03-26 | 5.2 SKILL.md | Added `disable-model-invocation: true` | Prevent auto-triggering during unrelated work |
| 2026-03-26 | 6. Project Structure | Skill lives in project .claude/ not ~/.claude/ | Keeps everything version-controlled together |
| 2026-03-26 | 4.1 Config | Using `platformdirs` for cross-platform config path | Windows compatibility (AppData vs ~/.weekend-scout) |
