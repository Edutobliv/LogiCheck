import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "logicheck_users.db")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    name = t[0]
    print(f"\n=== Tabla: {name} ===")
    cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
    for c in cols:
        print(f"  {c['cid']:2} | {c['name']:<30} | {c['type']:<15} | notnull={c['notnull']} | pk={c['pk']}")
    count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    print(f"  -> Filas: {count}")

conn.close()
