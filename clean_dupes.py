import sqlite3
conn = sqlite3.connect("logicheck_users.db")
# Eliminar los duplicados del Excel (codigos numericos string: '1','2','3')
deleted = conn.execute("DELETE FROM materiales WHERE codigo IN ('1','2','3')")
conn.commit()
print("Eliminados:", deleted.rowcount, "duplicados")
remaining = conn.execute("SELECT id, codigo, nombre FROM materiales").fetchall()
print("Materiales restantes:")
for r in remaining:
    print(" ", r[0], r[1], r[2])
conn.close()
