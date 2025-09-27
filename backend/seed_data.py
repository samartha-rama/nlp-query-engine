# backend/seed_data.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "test.db"

conn = sqlite3.connect(DB_PATH.as_posix())
cursor = conn.cursor()

# Insert sample departments (skip if already present)
cursor.execute("INSERT OR IGNORE INTO departments (id, name) VALUES (1, 'HR')")
cursor.execute("INSERT OR IGNORE INTO departments (id, name) VALUES (2, 'Engineering')")

# Insert sample employees (skip if already present)
cursor.execute(
    "INSERT OR IGNORE INTO employees (id, name, role, salary, department_id) "
    "VALUES (1, 'Alice', 'Manager', 7000, 1)"
)
cursor.execute(
    "INSERT OR IGNORE INTO employees (id, name, role, salary, department_id) "
    "VALUES (2, 'Bob', 'Engineer', 5000, 2)"
)
cursor.execute(
    "INSERT OR IGNORE INTO employees (id, name, role, salary, department_id) "
    "VALUES (3, 'Charlie', 'Engineer', 5500, 2)"
)

conn.commit()
conn.close()

print("Sample data inserted (if not already present). ✅")
