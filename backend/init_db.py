# backend/init_db.py
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey

# SQLite file will be created as ./test.db
DB_URL = "sqlite:///./test.db"

engine = create_engine(DB_URL, echo=False)
metadata = MetaData()

departments = Table(
    "departments", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
)

employees = Table(
    "employees", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("role", String),
    Column("salary", Integer),
    Column("department_id", Integer, ForeignKey("departments.id")),
)

def init_db():
    metadata.create_all(engine)
    # Insert sample rows (id provided for clarity)
    with engine.begin() as conn:
        # simple check to avoid duplicate inserts on re-run
        existing = conn.execute(departments.select().limit(1)).first()
        if existing:
            print("Sample data already exists; skipping inserts.")
            return
        conn.execute(departments.insert(), [
            {"id": 1, "name": "Engineering"},
            {"id": 2, "name": "HR"},
            {"id": 3, "name": "Sales"},
        ])
        conn.execute(employees.insert(), [
            {"id": 1, "name": "Alice Johnson", "role": "Backend Engineer", "salary": 120000, "department_id": 1},
            {"id": 2, "name": "Bob Singh", "role": "Data Scientist", "salary": 115000, "department_id": 1},
            {"id": 3, "name": "Carol Gupta", "role": "HR Manager", "salary": 90000, "department_id": 2},
            {"id": 4, "name": "Dave Patel", "role": "Sales Executive", "salary": 85000, "department_id": 3},
        ])
        print("Inserted sample departments and employees.")

if __name__ == "__main__":
    init_db()
    print("✅ test.db initialized in backend/ (SQLite)")
