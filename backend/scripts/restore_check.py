"""
Proves that a backup can actually be restored: verifies its checksum, restores it into a scratch database, compares row
counts of the key tables with the live database, and drops the scratch database again. Run it after every backup, or at
least on a schedule - a backup that was never restored is a hope, not a backup.

    python scripts/restore_check.py /backups/amanah/amanah_20261012_020000.dump
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

TABLES = [
    "accounts_user", "tenants_tenant", "pools_pool", "pools_dailybalance", "allocation_allocationrun",
    "accounting_journalbatch", "accounting_journalentry", "core_auditlog", "participants_participant",
]


def env(name, default=None):
    value = os.environ.get(name, default)
    if value is None:
        sys.exit(f"{name} is not set")
    return value


def psql(database, sql, host, port, user):
    result = subprocess.run(
        ["psql", "--host", host, "--port", port, "--username", user, "--dbname", database, "--tuples-only", "--no-align", "-c", sql],
        check=True, capture_output=True, text=True, env={**os.environ, "PGPASSWORD": env("DB_PASSWORD")},
    )
    return result.stdout.strip()


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    dump = Path(sys.argv[1])
    expected = dump.with_name(dump.name + ".sha256").read_text().split()[0]
    if hashlib.sha256(dump.read_bytes()).hexdigest() != expected:
        sys.exit("Checksum mismatch: the backup file is damaged.")
    host, port, user, live = env("DB_HOST", "localhost"), env("DB_PORT", "5432"), env("DB_USER"), env("DB_NAME")
    scratch = f"{live}_restore_check"
    subprocess.run(["dropdb", "--if-exists", "--host", host, "--port", port, "--username", user, scratch], check=True, env={**os.environ, "PGPASSWORD": env("DB_PASSWORD")})
    subprocess.run(["createdb", "--host", host, "--port", port, "--username", user, scratch], check=True, env={**os.environ, "PGPASSWORD": env("DB_PASSWORD")})
    try:
        subprocess.run(
            ["pg_restore", "--no-owner", "--host", host, "--port", port, "--username", user, "--dbname", scratch, str(dump)],
            check=True, env={**os.environ, "PGPASSWORD": env("DB_PASSWORD")},
        )
        problems = []
        for table in TABLES:
            restored = int(psql(scratch, f"select count(*) from {table}", host, port, user))
            live_count = int(psql(live, f"select count(*) from {table}", host, port, user))
            note = "" if restored <= live_count else "  <-- more rows than live (unexpected)"
            print(f"{table:32} restored {restored:>10}   live {live_count:>10}{note}")
            if restored > live_count:
                problems.append(table)
        if problems:
            sys.exit(f"Restore check found problems in: {', '.join(problems)}")
        print("Restore check passed: the backup restores and its contents are consistent with the live database.")
    finally:
        subprocess.run(["dropdb", "--if-exists", "--host", host, "--port", port, "--username", user, scratch], check=False, env={**os.environ, "PGPASSWORD": env("DB_PASSWORD")})


if __name__ == "__main__":
    main()
