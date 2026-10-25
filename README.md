# AgencyDesk

Multi-tenant client & project management backend (FastAPI + PostgreSQL).

## Setup
1. Install PostgreSQL and Python 3.11+
2. Create the database: `CREATE DATABASE agencydesk;`
3. Create tables: `psql -U postgres -d agencydesk -f schema.sql`
4. `python -m venv venv` then activate it
5. `pip install -r requirements.txt`
6. Set `DATABASE_URL` if your credentials differ from the default in `main.py`
7. `python seed.py`
8. `pytest -v`
9. `uvicorn main:app --reload` then open http://127.0.0.1:8000/docs

## Seed logins (password: `password123`)
- alice@alpha.com: agency_admin at Alpha Agency
- mike@alpha.com: agency_member at Alpha (assigned to Acme Website only)
- sam@example.com: agency_admin at Alpha AND client_user at Beta
- bella@beta.com: agency_admin at Beta

Login is two steps: `POST /login` with email and password returns your
memberships; call it again with `membership_id` to get a token.

## Implemented
Schema for all entities, two-step login, `GET /tasks/{id}`,
`GET /projects/{id}/tasks`, and tests for tenant isolation and
client visibility.

## Not implemented (schema is ready)
Comment, file approval, time entry and dashboard endpoints, invite
endpoints, member removal endpoint, and the frontend.

## Video
LOOM-LINK-HERE

## AI disclosure
Built with AI assistance. I reviewed the code and can explain each part.
