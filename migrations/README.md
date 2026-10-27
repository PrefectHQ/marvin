# Database migrations

These Alembic migrations apply to Marvin's thread/message database. Vector-memory providers manage their own storage.

```bash
uv run marvin db status
uv run marvin db history
uv run marvin db upgrade
```

Use the same `MARVIN_DATABASE_URL` as the application. SQLite URLs use the `sqlite+aiosqlite` driver.

To create a revision from model changes in a checkout:

```bash
uv run marvin dev db revision --autogenerate -m "Describe the schema change"
```

Review the generated migration before applying it. Back up stored history first. `db downgrade` and `db reset` can remove data; they prompt for confirmation, and `--yes` bypasses the prompt.

See [the migration guide](../docs/guides/database-migrations.mdx) for configuration and command details.
