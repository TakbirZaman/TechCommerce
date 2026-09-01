import sqlite3
conn = sqlite3.connect('techcommerce.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for row in c.fetchall():
    print(row[0])
conn.close()
