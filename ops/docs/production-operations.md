# REG.RU production deployment and operations

This runbook targets a low-cost Linux REG.RU MVP with ispmanager, SSH, MySQL,
Python 3.14, and CGI/Passenger. The automated deploy also needs `unzip`,
`curl`, and `sha256sum`; backup jobs need cron, `mysqldump`, and `mysql`.
Missing optional backup automation or edge services does not prevent the
initial closed-registration deployment. Do not substitute Flask's development
server.

## Values that must be supplied

Obtain these from REG.RU/ispmanager before the first deployment:

- SSH host, login, port, and optionally a private-key path.
- Absolute application root outside the public document root, referred to
  below as `<SiteRoot>` (for example `/home/login/apps/roleplay-trainer`).
- Public HTTPS URL and all accepted hostnames.
- Exact Python 3.14 executable (`python3.14` or an absolute path).
- MySQL host, port, database, username, and URL-encoded password.
- Confirmed Passenger application-root/startup-file/interpreter fields,
  restart mechanism, reverse-proxy hop count, and cron support.
- Domain registrar access and, if used later, Cloudflare access and the REG.RU
  origin IP.

The deploy script deliberately has no defaults for host, login, site path, or
public URL and rejects unsafe path syntax. It does not use or require Git.

## One-time server setup

Create private shared state over SSH:

```bash
mkdir -p <SiteRoot>/shared/storage/{scenarios,media/avatars} \
  <SiteRoot>/shared/{backups,logs}
chmod 700 <SiteRoot>/shared <SiteRoot>/shared/storage \
  <SiteRoot>/shared/backups <SiteRoot>/shared/logs
vi <SiteRoot>/shared/.env
chmod 600 <SiteRoot>/shared/.env
```

Use `.env.example` as the key list. Production must at least set:

```dotenv
APP_ENV=production
SECRET_KEY=<at-least-32-random-characters>
DATABASE_URL=mysql+pymysql://USER:URL_ENCODED_PASSWORD@DB_HOST:3306/DB?charset=utf8mb4
SCENARIOS_DIR=<SiteRoot>/shared/storage/scenarios
MEDIA_DIR=<SiteRoot>/shared/storage/media
TRUSTED_HOSTS=example.ru,www.example.ru
TRUSTED_PROXY_COUNT=<REG.RU-confirmed-hop-count>
SESSION_COOKIE_SECURE=true
HSTS_ENABLED=true
REGISTRATION_MODE=closed
TURNSTILE_REQUIRED=false
```

The closed-registration MVP remains protected by CSRF, database-backed login
throttling, secure cookies, request limits, and security headers without
Turnstile. Before changing `REGISTRATION_MODE` to `open` or `invite`, configure
the Turnstile site/secret keys and set `TURNSTILE_REQUIRED=true`.

Keep `.env`, `shared/storage`, `shared/backups`, and `shared/logs` outside the
domain document root. Never create a symlink to `shared` below a public static
directory. The release archive contains neither `.env` nor `storage`.

After the first successful deploy, configure Passenger in ispmanager:

- application root: `<SiteRoot>/current`
- startup file: `passenger_wsgi.py`
- callable: `application`
- Python interpreter: `<SiteRoot>/current/.venv/bin/python`
- environment: production

Point the domain through the panel's Python/Passenger application mapping, not
at the source directory as a generic static document root. Confirm directly
that requests for `/.env`, `/storage/`, `/backups/`, `/migrations/`, and
`/passenger_wsgi.py` return 404/403.

## Deploy from Windows

Run from any directory in PowerShell; the script locates the project itself.
It performs `npm ci`, builds the frontend, syntax-compiles Python to a temporary
cache, creates an allowlist-only ZIP, verifies its SHA-256 remotely, installs a
release-local virtualenv, backs up, migrates, runs readiness, switches the
`current` symlink, restarts Passenger, and checks public readiness.

```powershell
.\ops\scripts\deploy.ps1 `
  -SshHost "<ssh-host>" `
  -SshUser "<ssh-login>" `
  -SshPort 22 `
  -SiteRoot "/home/<login>/apps/roleplay-trainer" `
  -PublicBaseUrl "https://example.ru" `
  -RemotePython "python3.14" `
  -IdentityFile "$HOME\.ssh\id_ed25519"
```

Or use the project wrapper with baked-in host settings. Copy
`ops/deploy.example.ps1` to `ops/deploy.ps1` (and `ops/logs.example.ps1` to
`ops/logs.ps1`) and fill in the real host values; both copies are git-ignored:

```powershell
.\ops\deploy.ps1
.\ops\deploy.ps1 -BuildFrontend
```

Omit `-IdentityFile` when the SSH agent or password authentication is used.
`-SkipFrontendBuild` is intended only when the committed/generated bundle was
already built and independently verified.

Migration or pre-switch readiness failure leaves `current` unchanged. If the
public probe fails after switching, the remote script atomically restores the
previous symlink and restarts it. Database migrations are intentionally not
auto-downgraded: many MySQL DDL operations are not transaction-safe. The
pre-migration backup is the recovery point; write backward-compatible
expand/migrate/contract migrations.

## Health and logs

- `GET /health/live` proves only that the Passenger process responds.
- `GET /health/ready` checks MySQL and actual create/delete access in scenarios
  and media storage. It returns 503 without exception details when unavailable.
- `GET /health` is a compatibility alias for readiness.

Production application access logs go to stderr with method, path (never query
string), status, duration, and remote address. A redaction filter removes
common password/token/cookie assignments from application log messages. Do not
add request bodies, headers, session cookies, full URLs, `.env`, or SQL
parameters to logs. Configure REG.RU/ispmanager log rotation and access
permissions; provider proxy logs are outside the application filter.

## Daily backup and restore

Add a daily cron entry after the first deployment (adjust the time):

```cron
17 3 * * * /bin/bash <SiteRoot>/current/scripts/cron_backup.sh <SiteRoot>
```

The job creates a private `tar.gz` containing a consistent MySQL dump,
scenarios, avatars, and a manifest. Backups older than 14 days and backup logs
older than 30 days are removed. REG.RU account storage is not an independent
backup: regularly copy encrypted archives to separate storage and test restore
on a disposable MySQL database/account.

Before a production restore, close registration and stop writes (maintenance
mode in the panel). Verify the archive and run:

```bash
<SiteRoot>/current/.venv/bin/python <SiteRoot>/current/scripts/restore.py \
  --archive <SiteRoot>/shared/backups/roleplay-trainer-YYYYMMDDTHHMMSSZ.tar.gz \
  --safety-backup-destination <SiteRoot>/shared/backups \
  --confirm RESTORE-PRODUCTION
touch <SiteRoot>/current/tmp/restart.txt
curl --fail https://example.ru/health/ready
```

Restore first makes another safety backup. It imports MySQL and then replaces
scenario/avatar directories, retaining pre-restore files in hidden sibling
directories. Review and remove those only after application-level checks.

## Domain, HTTPS, and optional edge hardening

1. Point the domain to the REG.RU application using the provider's documented
   DNS and Passenger mapping.
2. Install a valid REG.RU/Let's Encrypt certificate and redirect HTTP to HTTPS.
   If Cloudflare is added later, use **Full (strict)**; never use Flexible.
3. Enable a single canonical-host redirect. Enable HSTS
   only after origin and edge HTTPS work for every intended subdomain.
4. Keep registration closed initially. Configure Turnstile before opening it;
   an edge WAF and additional rate limits are recommended follow-up hardening.
5. If Cloudflare is used, prefer an origin firewall allowlist for its IP ranges plus required
   administration access, or Cloudflare Authenticated Origin Pulls if REG.RU
   supports it. Shared hosting often exposes no tenant firewall; ask REG.RU.
   `TRUSTED_HOSTS` and a non-serving default virtual host reduce accidental
   direct access but cannot stop an attacker who reaches the origin IP and
   spoofs the Host header. Do not claim the origin is closed without a network
   control confirmed by the provider.
6. Confirm Cloudflare restores the client IP as documented by REG.RU and set
   `TRUSTED_PROXY_COUNT` to the exact trusted proxy chain. Guessing this value
   can let clients spoof addresses or can break rate limiting.

Keep `REGISTRATION_MODE=closed` through initial deployment and the production
smoke test. Docker runtime, Cloudflare, a separate database user, and advanced
origin controls are not launch gates for this low-cost MVP; document and add
them later where the hosting plan permits.
