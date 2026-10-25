import os, datetime
from dataclasses import dataclass
import bcrypt, jwt, psycopg2, psycopg2.extras
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel

DSN = os.getenv("DATABASE_URL",
    "dbname=agencydesk user=postgres password=pw123 host=localhost port=5432")
SECRET = os.getenv("JWT_SECRET", "dev-secret")
app = FastAPI()

def get_db():
    conn = psycopg2.connect(DSN, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@dataclass
class Ctx:
    user_id: int
    membership_id: int
    agency_id: int
    role: str
    client_id: int | None

def get_ctx(authorization: str = Header(None), db=Depends(get_db)) -> Ctx:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401)
    try:
        p = jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401)
    cur = db.cursor()
    cur.execute("""SELECT id, user_id, agency_id, role, client_id
                   FROM memberships WHERE id=%s AND user_id=%s""",
                [p["membership_id"], p["user_id"]])
    r = cur.fetchone()
    if r is None:
        raise HTTPException(401)
    return Ctx(r["user_id"], r["id"], r["agency_id"], r["role"], r["client_id"])

class LoginIn(BaseModel):
    email: str
    password: str
    membership_id: int | None = None

@app.post("/login")
def login(body: LoginIn, db=Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE email=%s",
                [body.email.lower()])
    u = cur.fetchone()
    if not u or not bcrypt.checkpw(body.password.encode(), u["password_hash"].encode()):
        raise HTTPException(401, "Invalid credentials")
    cur.execute("""SELECT m.id, m.role, a.name AS agency FROM memberships m
                   JOIN agencies a ON a.id = m.agency_id WHERE m.user_id=%s""",
                [u["id"]])
    ms = cur.fetchall()
    if body.membership_id is None:
        return {"memberships": ms}          # step 1: which agency?
    if body.membership_id not in [m["id"] for m in ms]:
        raise HTTPException(403)
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    token = jwt.encode({"user_id": u["id"], "membership_id": body.membership_id,
                        "exp": exp}, SECRET, algorithm="HS256")
    return {"access_token": token}           # step 2

def visible_task_sql(ctx: Ctx):
    """Common scope for every task query, depends on role."""
    sql = " t.agency_id = %s"
    params = [ctx.agency_id]
    if ctx.role == "client_user":
        sql += " AND t.is_internal = false AND p.client_id = %s"
        params.append(ctx.client_id)
    elif ctx.role == "agency_member":
        sql += """ AND EXISTS (SELECT 1 FROM project_members pm
                   WHERE pm.project_id = p.id AND pm.membership_id = %s)"""
        params.append(ctx.membership_id)
    return sql, params

@app.get("/tasks/{task_id}")
def get_task(task_id: int, ctx: Ctx = Depends(get_ctx), db=Depends(get_db)):
    scope, params = visible_task_sql(ctx)
    cur = db.cursor()
    cur.execute(f"""SELECT t.* FROM tasks t
                    JOIN projects p ON p.id = t.project_id AND p.agency_id = t.agency_id
                    WHERE t.id = %s AND {scope}""", [task_id] + params)
    row = cur.fetchone()
    if row is None:
        raise HTTPException(404)             # 404 not 403: do not leak existence
    return row

@app.get("/projects/{project_id}/tasks")
def list_tasks(project_id: int, ctx: Ctx = Depends(get_ctx), db=Depends(get_db)):
    scope, params = visible_task_sql(ctx)
    cur = db.cursor()
    cur.execute(f"""SELECT t.* FROM tasks t
                    JOIN projects p ON p.id = t.project_id AND p.agency_id = t.agency_id
                    WHERE p.id = %s AND {scope} ORDER BY t.id""",
                [project_id] + params)
    return cur.fetchall()
