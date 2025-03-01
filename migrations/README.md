# Marvin Database Migrations

This directory contains database migrations for Marvin. Migrations allow you to:

1. Manage database schema changes over time
2. Apply schema changes consistently across environments
3. Roll back schema changes if needed

## SQLite vs Other Databases

### SQLite (Default)

For SQLite databases (the default), Marvin will automatically create and update tables in these cases:
- In-memory SQLite databases (tables always created on startup)
- New SQLite file databases (tables created when the file doesn't exist)

For existing SQLite file databases, migrations can be applied manually or will be attempted automatically.

### Other Databases (PostgreSQL, etc.)

For production environments using databases like PostgreSQL, you should explicitly run migrations to manage schema changes. This provides better control and safety when updating the database.

## Using Migrations

### Creating a Migration (Developer)

To create a new migration (development task):

```bash
# Automatically determine changes based on model differences
marvin dev db revision --autogenerate -m "Add new column"

# Or create an empty migration for manual edits
marvin dev db revision -m "Custom migration"
```

### Applying Migrations

To apply all pending migrations:

```bash
marvin db upgrade
```

This will upgrade your database to the latest schema version.

### Rolling Back Migrations

To roll back migrations (requires confirmation with `-y` flag):

```bash
# Roll back to a specific migration ID
marvin db downgrade abc123 -y
```

### Resetting Database

To completely reset the database by downgrading to base and upgrading to latest version:

```bash
marvin db reset -y
```

This will roll back all migrations and then apply them from scratch.

### Migration Status

To check the current migration status:

```bash
# Show detailed database information
marvin db status

# Show current migration revision
marvin db current

# Show migration history
marvin db history
```

## Integration with Marvin

Marvin handles migrations based on the database type:

1. **SQLite in-memory databases:**
   - Tables are created automatically on every startup

2. **New SQLite file databases:**
   - Tables are created automatically when the file is first accessed

3. **Existing SQLite file databases:**
   - Migrations are attempted if available

4. **PostgreSQL/other databases:**
   - A warning is shown recommending manual migration

## Migration Best Practices

1. **Development:**
   - Use `marvin dev db revision` to create migrations
   - Include a descriptive message with `-m`
   - Review auto-generated migrations before committing

2. **Testing:**
   - Use `marvin db reset` to test migrations from scratch
   - Verify both upgrade and downgrade paths

3. **Production:**
   - Always back up your database before migrating
   - Run `marvin db upgrade` to apply pending migrations
   - Monitor migration logs for any issues

## Advanced Usage

The migration system is powered by Alembic. For advanced usage, you can:

1. Directly use Alembic commands:
   ```bash
   alembic -c migrations/alembic.ini <command>
   ```

2. Customize the environment in `migrations/env.py`

3. Create custom migration scripts for complex data migrations

See the [Alembic documentation](https://alembic.sqlalchemy.org/) for more information. 