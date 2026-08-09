# REG.RU capability preflight

Before deployment, verify the following in the REG.RU control panel for the
specific hosting plan:

- Linux hosting with **ispmanager** (not Host-Lite or a panel without Python).
- Python 3.14 and CGI/Passenger WSGI application support.
- SSH access and the permitted site/application directory.
- MySQL credentials supplied by the hosting plan, with `utf8mb4`, plus host,
  port, database name, and whether remote/SSH access is permitted. A dedicated
  application-only database user is preferable, but is not a launch blocker
  when the low-cost plan does not provide one.
- Writable directories outside the public web root for `.env`, scenarios,
  avatars, backups, and logs.
- The documented Passenger restart mechanism and any cron availability.

Record, without committing passwords: SSH host/login/port, site root,
application root, Python executable/virtualenv path, MySQL host/port/database
and database username.

Actual verification cannot be completed from the source tree: it requires the
user's authenticated REG.RU panel access. If Python 3.14, CGI/Passenger, SSH,
or MySQL is unavailable, stop before deployment and change the plan/tariff
instead of exposing Flask's development server. Docker, Cloudflare, Turnstile,
cron, a separate database user, and advanced origin-firewall controls are
recommended follow-ups, not prerequisites for the initial low-cost MVP.
Keep `REGISTRATION_MODE=closed` until anti-bot controls are configured.
