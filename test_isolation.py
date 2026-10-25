import psycopg2
from fastapi.testclient import TestClient
from main import app, DSN

c = TestClient(app)

def task_id(title):
    conn = psycopg2.connect(DSN); cur = conn.cursor()
    cur.execute("SELECT id FROM tasks WHERE title=%s", [title])
    r = cur.fetchone()[0]; conn.close(); return r

def token(email, agency):
    ms = c.post("/login", json={"email": email, "password": "password123"}).json()["memberships"]
    mid = next(m["id"] for m in ms if m["agency"] == agency)
    r = c.post("/login", json={"email": email, "password": "password123", "membership_id": mid})
    return {"Authorization": "Bearer " + r.json()["access_token"]}

def test_cross_tenant_returns_404():
    h = token("alice@alpha.com", "Alpha Agency")
    assert c.get(f"/tasks/{task_id('Beta visible task')}", headers=h).status_code == 404

def test_client_cannot_see_internal_task():
    h = token("sam@example.com", "Beta Agency")
    assert c.get(f"/tasks/{task_id('Beta internal task')}", headers=h).status_code == 404

def test_client_can_see_visible_task():
    h = token("sam@example.com", "Beta Agency")
    assert c.get(f"/tasks/{task_id('Beta visible task')}", headers=h).status_code == 200

def test_client_list_hides_internal():
    h = token("sam@example.com", "Beta Agency")
    titles = [t["title"] for t in c.get("/projects/2/tasks", headers=h).json()]
    assert titles == ["Beta visible task"]

def test_same_email_two_agencies_two_roles():
    ms = c.post("/login", json={"email": "sam@example.com", "password": "password123"}).json()["memberships"]
    assert {m["role"] for m in ms} == {"agency_admin", "client_user"}

def test_admin_sees_internal_in_own_agency():
    h = token("alice@alpha.com", "Alpha Agency")
    assert c.get(f"/tasks/{task_id('Alpha internal task')}", headers=h).status_code == 200
