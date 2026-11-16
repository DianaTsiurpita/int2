# Docker Compose secrets

Run `setup-secrets.ps1` in Windows PowerShell to generate the two required random secret files. Never commit `db_password` or `jwt_secret_key`. For Docker Compose, both files are mounted read-only at `/run/secrets/`.

On Linux set permissions with `chmod 600 secrets/db_password secrets/jwt_secret_key`. On Windows, restrict access to your user account using NTFS ACLs.

If you rotate `db_password` after the PostgreSQL volume was initialized, the database user password must also be updated with SQL; changing the file alone does not rotate the database password. Do not run `docker compose down -v` on valuable data.
