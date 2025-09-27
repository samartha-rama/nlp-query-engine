import sqlite3

# connect to your test.db
conn = sqlite3.connect("test.db")
cursor = conn.cursor()

# show all employees
print("\nAll employees:")
for row in cursor.execute("SELECT * FROM employees"):
    print(row)

# show employees with salary > 100000
print("\nEmployees with salary > 100000:")
for row in cursor.execute("SELECT * FROM employees WHERE salary > ?", (100000,)):
    print(row)

conn.close()
