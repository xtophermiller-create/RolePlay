# Local Docker development

This setup runs the Flask app on Python 3.14 with a private MySQL 8.4
container. MySQL data persists in the `mysql_data` named volume. The project
directory is bind-mounted at `/app`, so edits made on Windows are immediately
available in the app container and the existing `storage/` files remain on the
host.

## First start (PowerShell)

1. Create the untracked local environment file:

   ```powershell
   Copy-Item .env.docker.example .env.docker
   ```

2. Replace both placeholder secrets in `.env.docker`. Use an
   URL-safe database password and put the same value in `MYSQL_PASSWORD` and
   the password part of `DATABASE_URL`. Generate values with:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. Build and start:

   ```powershell
   docker compose up --build
   ```

Schema migrations run automatically before Gunicorn starts. Open
`http://127.0.0.1:5000`, or `http://<LAN-IP>:5000` from another device.
Windows Defender Firewall may require an inbound rule for TCP port 5000.
This HTTP/LAN configuration is for trusted local networks only.

## Common commands

```powershell
# Show container and health status
docker compose ps

# Run migrations explicitly
docker compose run --rm app flask --app run:app db upgrade

# Open a Flask shell
docker compose run --rm app flask --app run:app shell

# Stop containers while preserving MySQL
docker compose down
```

The app container does not publish MySQL's port. `docker compose down` keeps
the named volume; `docker compose down --volumes` permanently deletes the
local Docker MySQL database and should only be used intentionally.

## Optional legacy SQLite import

The normal Docker startup does not read, modify, or delete the existing SQLite
database. After making a separate backup and reviewing the source paths, import
it explicitly:

```powershell
docker compose run --rm app python scripts/import_sqlite_to_mysql.py `
  --sqlite /app/storage/db/roleplay_trainer.db `
  --scenario-dir /app/storage/scenarios `
  --media-dir /app/storage/media `
  --backup-dir /app/backups
```

The importer creates a timestamped source backup before reading, requires a
MySQL target, and is idempotent. Do not run it against unreviewed production
data.
