"""
Logical backup of the platform database with pg_dump (custom format, compressed), plus a checksum file.

    python scripts/backup_db.py --out /backups/amanah        # writes amanah_YYYYmmdd_HHMMSS.dump and .sha256

Settings come from the same environment variables as the application (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT).
A logical dump gives a daily recovery point. The BRD target (RPO <= 15 minutes) additionally needs continuous WAL
archiving on the database server (for example pgBackRest or Barman); this script does not replace that.
"""

import argparse
import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def env(name, default=None):
    value = os.environ.get(name, default)
    if value is None:
        sys.exit(f"{name} is not set")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Directory for the dump (created if missing).")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"amanah_{datetime.now():%Y%m%d_%H%M%S}.dump"
    command = [
        "pg_dump", "--format=custom", "--compress=6", "--no-owner",
        "--host", env("DB_HOST", "localhost"), "--port", env("DB_PORT", "5432"),
        "--username", env("DB_USER"), "--file", str(target), env("DB_NAME"),
    ]
    subprocess.run(command, check=True, env={**os.environ, "PGPASSWORD": env("DB_PASSWORD")})
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (target.parent / f"{target.name}.sha256").write_text(f"{digest}  {target.name}\n")
    print(f"Backup written: {target} ({target.stat().st_size / 1_048_576:.1f} MB), sha256 {digest[:16]}...")


if __name__ == "__main__":
    main()
