"""Link every Postcranial character to Wood & Brummel 2023 (role: Character definition).

Run from the project folder on your Mac:   venv/bin/python link_wood2023.py
Safe to run more than once: characters already linked are skipped.
"""
import sqlite3
from datetime import datetime, timezone

DB = "db.sqlite3"
CITATION_KEY = "Wood&Brummel2023"
ROLE = "CHAR"

con = sqlite3.connect(DB)  # opening read-write also finishes any interrupted write (rolls it back)
print("Integrity check:", con.execute("PRAGMA integrity_check").fetchone()[0])

row = con.execute("SELECT id FROM hcdb_publication WHERE citation_key = ?", (CITATION_KEY,)).fetchone()
if row is None:
    raise SystemExit(f"No publication with citation_key {CITATION_KEY!r} found - check the admin.")
pub_id = row[0]

todo = [r[0] for r in con.execute(
    """SELECT id FROM hcdb_character
       WHERE anatomical_region = 'POST'
         AND id NOT IN (SELECT character_id FROM hcdb_characterpublication
                        WHERE publication_id = ? AND role = ?)
       ORDER BY id""", (pub_id, ROLE))]

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
with con:
    con.executemany(
        """INSERT INTO hcdb_characterpublication
           (role, character_number, original_wording, original_states, page, notes,
            created_at, updated_at, character_id, publication_id)
           VALUES (?, NULL, NULL, NULL, NULL, NULL, ?, ?, ?, ?)""",
        [(ROLE, now, now, cid, pub_id) for cid in todo])

linked = con.execute("SELECT COUNT(*) FROM hcdb_characterpublication WHERE publication_id = ?", (pub_id,)).fetchone()[0]
post = con.execute("SELECT COUNT(*) FROM hcdb_character WHERE anatomical_region = 'POST'").fetchone()[0]
nosrc = con.execute("""SELECT COUNT(*) FROM hcdb_character
                       WHERE id NOT IN (SELECT character_id FROM hcdb_characterpublication)""").fetchone()[0]
print(f"Linked {len(todo)} new characters to {CITATION_KEY}.")
print(f"{CITATION_KEY} now has {linked} links; database has {post} postcranial characters.")
print(f"Characters with no source left: {nosrc}")
con.close()
