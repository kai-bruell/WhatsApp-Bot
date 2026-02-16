# TODO

## database is locked bei /datenschutz

**Problem:** `delete_user_data()` und `mark_deletion_requested()` öffnen jeweils eigene DB-Connections via `get_db()`. Zwei gleichzeitige Write-Transactions -> SQLite Lock.

**Ursache:** Jede Funktion in `database.py` ruft `get_db()` auf, das jedes Mal eine neue Connection erstellt. `delete_user_data()` ruft `mark_deletion_requested()` auf bevor es selbst committed hat.

**Fix:** Entweder:
1. Singleton-Connection (eine globale Connection statt jedes Mal neu) oder
2. `mark_deletion_requested` inline in `delete_user_data` statt als separaten Call (gleiche Connection, ein Commit)
