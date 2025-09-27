## NLP Query Engine
-----------------

This project is built as part of the AI Engineering Internship Assignment (Ekam Apps).
It demonstrates a backend system that can:

Ingest a database and automatically reflect its schema.

Run natural language queries (NL → SQL → Results).

Provide REST APIs via FastAPI.
==========================================================================================

## Tech Stack
----------

Python 3.10+

FastAPI (API framework)

SQLite + SQLAlchemy (Database + ORM/Reflection)

Uvicorn (ASGI server)

Cachetools (query caching)
=============================================================================================

Project Structure
-----------------
nlp-query-engine/
│── backend/
│   ├── main.py          # FastAPI app with APIs
│   ├── seed_data.py     # Seeds sample DB data
│   ├── query_test.py    # Run direct SQL queries for testing
│   └── test.db          # SQLite DB
│
│── requirements.txt     # Dependencies
│── README.md            # Documentation

=============================================================================================

## Setup Instructions
------------------
1. Clone the repo:
   git clone <your-github-repo-url>
   cd nlp-query-engine

2. Create a virtual environment:
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   .venv\Scripts\Activate.ps1  # Windows PowerShell

3. Install dependencies:
   pip install -r requirements.txt

4. Seed the database with sample data:
   cd backend
   python seed_data.py

5. Run the FastAPI server:
   uvicorn main:app --reload

6. Open your browser at:
   http://127.0.0.1:8000/docs

=============================================================================================

## API Endpoints
-------------
1. Root
    GET / → Health check.

2. Ingest Database
    POST /api/ingest/database
    Provide connection string (e.g., "sqlite:///./test.db").

3. Get Schema
    GET /api/schema
    Returns last discovered DB schema.

4. List Employees
    GET /api/employees
    Lists all employees in the database.

5. Query DB (Natural Language)
    POST /api/query
    Send a question, get SQL + results.

Example Request:

{
  "question": "Show employees with salary greater than 100000"
}

Example Response:
{
  "query": "SELECT * FROM employees WHERE salary > :amount",
  "params": {"amount": 100000},
  "results": [
    {"id": 1, "name": "Alice Johnson", "role": "Backend Engineer", "salary": 120000, "department_id": 1}
  ]
}

==========================================================================================
## Author
Name: A S Samartha Rama
Email:Samartharama7@gmail.com
Contact: 9482711615
=========================================================================================
---

## 🚀 Future Improvements
- Add support for more complex natural language queries (joins, subqueries, aggregation).  
- Implement document ingestion + semantic search (vector embeddings).  
- Secure APIs with authentication & authorization.  
- Deploy backend to cloud (e.g., AWS, Render, or Railway).  
- Build a React/Next.js frontend to interact with the API visually.  

---


