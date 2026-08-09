# Database migration

1. Back up the SQLite database and all of `storage/` independently.
2. Configure `DATABASE_URL` for a new MySQL database.
3. Run `flask --app run:app db upgrade`.
4. Import without deleting the source:
   `python ops/scripts/import_sqlite_to_mysql.py --sqlite storage/db/roleplay_trainer.db`.
5. Confirm the reported counts and inspect users/scenario ownership before
   switching traffic.

The importer refuses a non-MySQL target, creates a timestamped SQLite backup,
keeps existing matching rows, aborts on ID/file conflicts, copies scenario
files atomically, and rolls back newly copied files on a database error. It
does not delete or alter the SQLite source.

For a database already in use, back it up and run
`python ops/scripts/migrate_password_hashes.py` once. Successful legacy logins also
upgrade their password hash automatically. Neither command prints passwords.
