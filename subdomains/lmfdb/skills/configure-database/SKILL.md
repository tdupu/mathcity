---
name: configure-database
description: Interactively create the project-local lmfdb-pipeline.conf by walking through each value one at a time (PGDATABASE, PGSCHEMA, DATA_DIR, SCHEMA_MD). Gitignores the result. Run this once per project before using database or conversion-lattice skills. Companion setup skill per POLICY.md P1.12. Trigger phrases: "configure database", "set up the database conf", "the database skills can't find their conf", "configure lmfdb pipeline", or on a fresh clone.
---

# configure-database

Create the project-local gitignored conf that database and conversion-lattice
skills read. Private values never enter git (POLICY.md P1.10).

## Dependency check

```bash
CONF="$(git rev-parse --show-toplevel 2>/dev/null)/lmfdb-pipeline.conf"
if [ -f "$CONF" ]; then
  echo "I'm sorry, I can't do that — lmfdb-pipeline.conf already exists at $CONF."
  echo "Diff existing keys against the example before reconfiguring:"
  echo "  diff <(grep '^[A-Z_]*=' \"$CONF\" | cut -d= -f1 | sort) \\"
  echo "       <(grep '^[A-Z_]*=' <mathcity-pack-root>/subdomains/lmfdb/assets/lmfdb-pipeline.conf.example | cut -d= -f1 | sort)"
  echo "To start fresh: cp \"$CONF\" \"${CONF}.bak\" && rm \"$CONF\""
  exit 1
fi
```

## Procedure

1. **Check for existing conf.** Look for `lmfdb-pipeline.conf` at the project root
   (`$(git rev-parse --show-toplevel)/lmfdb-pipeline.conf`). If it already exists,
   diff its keys against the example and report any new keys; do not overwrite.
2. **Copy the example.**
   ```bash
   cp <mathcity-pack-root>/subdomains/lmfdb/assets/lmfdb-pipeline.conf.example \
      "$(git rev-parse --show-toplevel)/lmfdb-pipeline.conf"
   ```
3. **Fill in values interactively.** Ask one at a time (AskUserQuestion where available):
   - `PGDATABASE` — PostgreSQL database name
   - `PGSCHEMA` — schema name (often `lmfdb`)
   - `DATA_DIR` — project-relative flat-file cache dir (default: `DATA`)
   - `SCHEMA_MD` — path to your schema.md file (default: `schema.md`)
   Never echo values back or pass them in argv.
4. **Gitignore the conf.** Verify `lmfdb-pipeline.conf` is in the project's `.gitignore`
   and prove it:
   ```bash
   git -C "$(git rev-parse --show-toplevel)" check-ignore lmfdb-pipeline.conf && echo ignored
   ```
   If not ignored, add the entry and re-verify before proceeding.
5. **Validate.** `bash -n lmfdb-pipeline.conf` — must parse.
6. **Report** which database/conversion-lattice skills are now usable.

## Output

`ready` or `blocked` with the exact failing step. Never print conf contents.

## See also
- `assets/lmfdb-pipeline.conf.example` — the shipped template
- `mathcity-lmfdb.configure-server` — sets up the SSH/compute-server side
- POLICY.md P1.10 (no private values), P1.12 (setup skill required)
