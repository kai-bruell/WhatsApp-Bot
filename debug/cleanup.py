"""DB-Cleanup: Alte processed_messages und verwaiste Sessions löschen.

Nutzung:
  python debug/cleanup.py          # Normaler Lauf
  python debug/cleanup.py --dry    # Nur anzeigen, nichts löschen

Cron-Beispiel (täglich 3 Uhr):
  0 3 * * * cd /path/to/project && python debug/cleanup.py >> data/cleanup.log 2>&1
"""

import sqlite3
import os
import sys
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "bot.db"))

dry_run = "--dry" in sys.argv


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    print(f"[{datetime.now().isoformat()}] Cleanup gestartet (DB: {DB_PATH})")
    if dry_run:
        print("  DRY RUN — nichts wird gelöscht")

    # 1. processed_messages älter als 24h
    cur.execute("SELECT COUNT(*) FROM processed_messages WHERE timestamp < datetime('now', '-1 day')")
    count_msgs = cur.fetchone()[0]
    print(f"  processed_messages >24h: {count_msgs}")
    if not dry_run and count_msgs:
        cur.execute("DELETE FROM processed_messages WHERE timestamp < datetime('now', '-1 day')")

    # 2. Abgeschlossene Sessions
    cur.execute("SELECT COUNT(*) FROM sessions WHERE step = 'COMPLETED'")
    count_completed = cur.fetchone()[0]
    print(f"  sessions COMPLETED: {count_completed}")
    if not dry_run and count_completed:
        cur.execute("DELETE FROM sessions WHERE step = 'COMPLETED'")

    # 3. Verwaiste Sessions älter als 7 Tage
    cur.execute("SELECT COUNT(*) FROM sessions WHERE updated_at < datetime('now', '-7 days')")
    count_stale = cur.fetchone()[0]
    print(f"  sessions >7 Tage inaktiv: {count_stale}")
    if not dry_run and count_stale:
        cur.execute("DELETE FROM sessions WHERE updated_at < datetime('now', '-7 days')")

    if not dry_run:
        conn.commit()
        total = count_msgs + count_completed + count_stale
        print(f"  {total} Zeilen gelöscht.")

    conn.close()


if __name__ == "__main__":
    main()
