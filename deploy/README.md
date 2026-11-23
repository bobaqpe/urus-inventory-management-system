# URUS operations

The systemd service and daily backup timer are defined in this directory. The
application loads `/root/projects/urus/.env`; this file must remain private.
The backup timer runs around 02:00 UTC and uses PostgreSQL's custom dump format.
Backups are written to `/root/projects/urus/.backups` with owner-only access.
They are not automatically deleted. Monitor disk space and copy encrypted
backups to separate storage: local copies alone do not survive server loss.

Check service and backup status:

```
systemctl status urus.service
systemctl list-timers urus-backup.timer
journalctl -u urus-backup.service
```

Create a backup on demand with `systemctl start urus-backup.service`. To verify
one, run `bash deploy/check-restore.sh /absolute/path/to/backup.dump` as the
local PostgreSQL role with permission to create databases. The script restores
into a uniquely named temporary database and removes it on exit; it does not
modify the live database. A successful restore check does not replace regular
application-level recovery exercises.

The application currently listens on port 5000 over HTTP. Configure a dedicated
HTTPS domain and reverse proxy, then restrict Gunicorn to localhost; do not
place the HTTP endpoint behind a proxy while leaving port 5000 publicly open.

## Firebase and Cloud Run migration

As of 2026-11-23 the main Cloud Run service uses Neon PostgreSQL. Its pooled
connection URL is stored in Secret Manager as `urus-neon-db-url`. The Neon CLI
link points to project `ancient-sky-53121708`, branch `production`; use a direct
connection for migrations and backups, and the pooled connection for the app.
For local configuration, `neon env pull --file .secrets/neon.env --service postgres`
keeps credentials separate from the existing `.env`. Use `DATABASE_URL_UNPOOLED`
as `DATABASE_URL` for Alembic. The `npm run build` command prepares Firebase
Hosting assets and checks Python compilation.

The preview environment and Cloud SQL instance were removed on 2026-11-23.
A Neon backup from before Cloud SQL removal is stored locally in
`.backups/neon-before-cloudsql-removal.dump`; its archive was checked for
readability but has not been restored. Store independent backups separately.

The Firebase Hosting site is `https://urus-ba98e.web.app`. Its `/api/**`
requests are routed to Cloud Run `urus-api` in `asia-southeast1`. The service
previously connected to Cloud SQL, which has been removed. The former local
`urus_dev` database and its final backup are retained for
rollback only. The local application service and its backup timer are disabled
to avoid writes to the old copy and misleading backups.

Rebuild public static files with `python3 deploy/build-firebase-public.py` before
any Hosting deployment. Deploying code or altering cloud infrastructure requires
appropriate Google Cloud credentials.
Do not restart the old service against the old database after cloud cutover:
it would create a second, divergent dataset.
