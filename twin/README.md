# Twin (digital twin snapshot)

Generated after ingest by `build_twin_profile.py` (`make sync` or `python scripts/cli.py twin`).

Lives at repo-root `twin/` (outside the iCloud vault) so launchd/background jobs can write without Full Disk Access.

- **`PROFILE.md`** — human-readable snapshot (principles, judged hypotheses, tensions, evolution)
- **`principles.json`** — machine catalog for query/lint context
- **`Self-Hypotheses.md`** — user-judged claims; supported/revised feed into PROFILE
