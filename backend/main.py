# backend/main.py
import re
import time
from typing import Dict, Any, List, Tuple, Optional

from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, text
from cachetools import TTLCache, cached

app = FastAPI(title="NLP Query Engine")

# --- Globals ---
discovered_schema: Dict[str, Any] = {}
engine = create_engine("sqlite:///./test.db", echo=False)

# cache for query results
query_cache = TTLCache(maxsize=200, ttl=300)


# --- Pydantic models ---
class DBConnection(BaseModel):
    connection_string: str


class QueryRequest(BaseModel):
    question: str
    search_documents: bool = False


# --- Helper functions ---
def set_engine_from_conn_string(conn_str: str):
    global engine
    engine = create_engine(conn_str, echo=False)


def reflect_schema(conn_str: str) -> Dict[str, Any]:
    md = MetaData()
    tmp_engine = create_engine(conn_str, echo=False)
    md.reflect(bind=tmp_engine)
    schema = {}
    for tname, table in md.tables.items():
        schema[tname] = {
            "columns": [{"name": c.name, "type": str(c.type)} for c in table.columns],
            "primary_keys": [c.name for c in table.primary_key.columns],
        }
    return schema


def find_table_by_columns(schema: Dict[str, Any], required_cols: List[str]) -> Optional[str]:
    required = set(c.lower() for c in required_cols)
    best_table = None
    best_score = -1
    for tname, meta in schema.items():
        cols = set(c["name"].lower() for c in meta["columns"])
        score = len(required & cols)
        if score > best_score:
            best_score = score
            best_table = tname
    return best_table


def guess_employees_and_departments(schema: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    emp_table = find_table_by_columns(schema, ["salary", "role", "department_id", "name"])
    dept_table = None
    if schema:
        for t, meta in schema.items():
            names = set(c["name"].lower() for c in meta["columns"])
            if "name" in names and ("id" in names or "dept" in t.lower() or "department" in t.lower()):
                dept_table = t
                break
    return emp_table or (list(schema.keys())[0] if schema else "employees"), dept_table


def sample_column_values(engine_, table: str, column: str, limit: int = 50) -> List[str]:
    try:
        with engine_.connect() as conn:
            sql = text(f"SELECT DISTINCT {column} AS val FROM {table} WHERE {column} IS NOT NULL LIMIT :lim")
            rows = conn.execute(sql, {"lim": limit}).mappings().all()
            return [str(r["val"]) for r in rows if r["val"] is not None]
    except Exception:
        return []


def safe_like_param(s: str) -> str:
    return f"%{s.replace('%', '').replace('_', '').strip()}%"


# --- SQL Generation ---
def generate_sql_from_question(question: str, schema: Dict[str, Any], engine_) -> Tuple[str, dict]:
    q = question.lower().strip()
    emp_table, dept_table = guess_employees_and_departments(schema)
    params = {}

    # Average salary by department
    if re.search(r"\b(avg|average)\b.*\bsalary\b", q) and dept_table:
        sql = f"""
        SELECT d.name AS department, AVG(e.salary) AS average_salary
        FROM {emp_table} e
        JOIN {dept_table} d ON e.department_id = d.id
        GROUP BY d.name
        ORDER BY average_salary DESC
        """
        return sql, params

    # Count employees
    if re.search(r"\b(how many|count|number of)\b.*\bemployees\b", q):
        if "department" in q and dept_table:
            m = re.search(r"department\s*(?:is|named)?\s*['\"]?([a-zA-Z0-9 &\-]+)['\"]?", q)
            if m:
                dept = m.group(1).strip()
                sql = f"""
                SELECT COUNT(*) AS cnt
                FROM {emp_table} e
                JOIN {dept_table} d ON e.department_id = d.id
                WHERE d.name LIKE :dept_name
                """
                params["dept_name"] = safe_like_param(dept)
                return sql, params
        sql = f"SELECT COUNT(*) AS cnt FROM {emp_table}"
        return sql, params

    # Top N highest paid
    m_top = re.search(r"\btop\s+(\d+)\b.*(highest|highest paid|paid)\b", q)
    if m_top:
        n = int(m_top.group(1))
        sql = f"SELECT * FROM {emp_table} ORDER BY salary DESC LIMIT :limit"
        params["limit"] = n
        return sql, params

    # Salary > or <
    m_gt = re.search(r"(?:salary|pay|compensation).*(greater than|over|above|>|>=)\s*\$?([\d,]+)", q)
    if not m_gt:
        m_gt = re.search(r">\s*\$?([\d,]+)", q)
    if m_gt:
        amount = int(m_gt.group(len(m_gt.groups())))
        sql = f"SELECT * FROM {emp_table} WHERE salary > :amount"
        params["amount"] = amount
        return sql, params

    m_lt = re.search(r"(?:salary|pay|compensation).*(less than|under|below|<|<=)\s*\$?([\d,]+)", q)
    if not m_lt:
        m_lt = re.search(r"<\s*\$?([\d,]+)", q)
    if m_lt:
        amount = int(m_lt.group(len(m_lt.groups())))
        sql = f"SELECT * FROM {emp_table} WHERE salary < :amount"
        params["amount"] = amount
        return sql, params

    # Department filter
    if "department" in q or "in " in q:
        m = re.search(r"(?:department\s*(?:is|named|:)?\s*['\"]?([a-zA-Z0-9 &\-]+)['\"]?)", q)
        if not m:
            m = re.search(r"\bin\s+([a-zA-Z0-9 &\-]+)\b", q)
        if m and dept_table:
            dept = m.group(1).strip()
            sql = f"""
            SELECT e.* FROM {emp_table} e
            JOIN {dept_table} d ON e.department_id = d.id
            WHERE d.name LIKE :dept_name
            """
            params["dept_name"] = safe_like_param(dept)
            return sql, params

    # Role filter
    role_values = sample_column_values(engine_, emp_table, "role", limit=200)
    for rv in role_values:
        if rv and rv.lower() in q:
            sql = f"SELECT * FROM {emp_table} WHERE role LIKE :role"
            params["role"] = safe_like_param(rv)
            return sql, params

    # Search by name
    m_name = re.search(r"(?:name|named|called)\s*[: ]\s*['\"]?([a-zA-Z .'-]+)['\"]?", q)
    if m_name:
        name = m_name.group(1).strip()
        sql = f"SELECT * FROM {emp_table} WHERE name LIKE :name"
        params["name"] = safe_like_param(name)
        return sql, params

    # Generic all employees
    if re.search(r"\b(all|list|show)\b.*\bemployees\b", q) or q.strip() in ("employees", "all employees", "list employees"):
        sql = f"SELECT * FROM {emp_table}"
        return sql, params

    # Fallback keyword search
    tokens = [t for t in re.split(r"\W+", q) if t and len(t) > 2]
    if tokens:
        token = max(tokens, key=len)
        sql = f"SELECT * FROM {emp_table} WHERE name LIKE :tok OR role LIKE :tok"
        params["tok"] = safe_like_param(token)
        return sql, params

    raise ValueError("Unable to parse the question into SQL with the current heuristics.")


# --- Endpoints ---
@app.get("/")
def root():
    return {"message": "NLP Query Engine backend is running"}


@app.post("/api/ingest/database")
def ingest_database(conn: DBConnection):
    try:
        schema = reflect_schema(conn.connection_string)
        set_engine_from_conn_string(conn.connection_string)
        global discovered_schema
        discovered_schema = schema
        return {"status": "success", "schema": schema}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/schema")
def get_schema():
    if not discovered_schema:
        return {"status": "no_schema", "detail": "Call POST /api/ingest/database first."}
    return {"status": "ok", "schema": discovered_schema}


@app.get("/api/employees")
def list_employees(limit: int = 100):
    try:
        with engine.connect() as conn:
            rs = conn.execute(text("SELECT * FROM employees LIMIT :lim"), {"lim": limit})
            rows = [dict(r) for r in rs.mappings().all()]
        return {"count": len(rows), "employees": rows}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# --- Caching ---
def schema_fingerprint(schema: Dict[str, Any]) -> str:
    if not schema:
        return "no_schema"
    parts = []
    for k, v in schema.items():
        cols = ",".join([c["name"] for c in v["columns"]])
        parts.append(f"{k}:{cols}")
    return "|".join(sorted(parts))


def cache_key_func(sql_text: str, params: dict):
    return f"{schema_fingerprint(discovered_schema)}::{sql_text}::{params}"


@cached(query_cache, key=lambda sql_text, params: cache_key_func(sql_text, params))
def run_and_cache_sql(sql_text: str, params: dict) -> List[dict]:
    with engine.connect() as conn:
        result = conn.execute(text(sql_text), params or {})
        return [dict(r) for r in result.mappings().all()]


@app.post("/api/query")
def query_db(request: QueryRequest):
    start = time.time()
    try:
        tmp_schema = discovered_schema or reflect_schema(str(engine.url))
        sql_text, params = generate_sql_from_question(request.question, tmp_schema, engine)
    except ValueError as ve:
        return {"status": "error", "detail": str(ve)}

    try:
        rows = run_and_cache_sql(sql_text, params)
        elapsed = int((time.time() - start) * 1000)
        return {"query": sql_text.strip(), "params": params, "results": rows, "time_ms": elapsed}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# --- Optional document ingestion ---
ingest_jobs: Dict[str, Dict[str, Any]] = {}


@app.post("/api/ingest/documents")
async def ingest_documents(files: List[UploadFile] = File(...), background_tasks: BackgroundTasks = None):
    job_id = str(int(time.time() * 1000))
    ingest_jobs[job_id] = {"status": "running", "processed": 0, "total": len(files)}

    def process():
        for f in files:
            content = f.file.read().decode("utf-8", errors="ignore")
            ingest_jobs[job_id].setdefault("documents", []).append({"filename": f.filename, "text": content[:5000]})
            ingest_jobs[job_id]["processed"] += 1
        ingest_jobs[job_id]["status"] = "complete"

    if background_tasks:
        background_tasks.add_task(process)
    else:
        process()
    return {"job_id": job_id}


@app.get("/api/ingest/status/{job_id}")
def get_ingest_status(job_id: str):
    if job_id not in ingest_jobs:
        return {"status": "error", "detail": "job_id not found"}
    return ingest_jobs[job_id]
