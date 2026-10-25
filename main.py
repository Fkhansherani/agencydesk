
import os
import datetime

import bcrypt
import jwt
import psycopg2
import psycopg2.extras

from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel


# Database and JWT configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "dbname=agencydesk user=postgres password=pw123 "
    "host=localhost port=5432"
)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")

app = FastAPI()


# Database connection
def get_db():
    connection = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# Logged-in user's membership details
class UserContext:
    def __init__(
        self,
        user_id: int,
        membership_id: int,
        agency_id: int,
        role: str,
        client_id: int | None
    ):
        self.user_id = user_id
        self.membership_id = membership_id
        self.agency_id = agency_id
        self.role = role
        self.client_id = client_id


# Authenticate the request using its JWT
def get_current_user(
    authorization: str | None = Header(default=None),
    db=Depends(get_db)
) -> UserContext:

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    token = authorization[len("Bearer "):]

    try:
        token_data = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )

        user_id = token_data["user_id"]
        membership_id = token_data["membership_id"]

    except (jwt.PyJWTError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    cursor = db.cursor()

    cursor.execute(
        """
        SELECT id, user_id, agency_id, role, client_id
        FROM memberships
        WHERE id = %s AND user_id = %s
        """,
        (membership_id, user_id)
    )

    membership = cursor.fetchone()

    if membership is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid membership"
        )

    return UserContext(
        user_id=membership["user_id"],
        membership_id=membership["id"],
        agency_id=membership["agency_id"],
        role=membership["role"],
        client_id=membership["client_id"]
    )


# Login request data
class LoginRequest(BaseModel):
    email: str
    password: str
    membership_id: int | None = None


# Login endpoint
@app.post("/login")
def login_user(
    login_data: LoginRequest,
    db=Depends(get_db)
):
    cursor = db.cursor()

    email = login_data.email.strip().lower()

    cursor.execute(
        """
        SELECT id, password_hash
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    user = cursor.fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    password_hash = user["password_hash"]

    if not bcrypt.checkpw(
        login_data.password.encode("utf-8"),
        password_hash.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    # Find all agencies associated with this user
    cursor.execute(
        """
        SELECT
            m.id,
            m.role,
            a.name AS agency
        FROM memberships AS m
        JOIN agencies AS a
            ON a.id = m.agency_id
        WHERE m.user_id = %s
        """,
        (user["id"],)
    )

    memberships = cursor.fetchall()

    # Step 1: Let the user choose an agency
    if login_data.membership_id is None:
        return {"memberships": memberships}

    selected_membership = next(
        (
            membership
            for membership in memberships
            if membership["id"] == login_data.membership_id
        ),
        None
    )

    if selected_membership is None:
        raise HTTPException(
            status_code=403,
            detail="Membership not allowed"
        )

    # Step 2: Create the access token
    expires_at = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=8)
    )

    access_token = jwt.encode(
        {
            "user_id": user["id"],
            "membership_id": selected_membership["id"],
            "exp": expires_at
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    return {"access_token": access_token}


# Build the access rules for task queries
def get_task_visibility(user: UserContext):
    conditions = ["t.agency_id = %s"]
    parameters = [user.agency_id]

    if user.role == "client_user":
        conditions.append("t.is_internal = FALSE")
        conditions.append("p.client_id = %s")
        parameters.append(user.client_id)

    elif user.role == "agency_member":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM project_members AS pm
                WHERE pm.project_id = p.id
                  AND pm.membership_id = %s
            )
            """
        )
        parameters.append(user.membership_id)

    return " AND ".join(conditions), parameters


# Get one task
@app.get("/tasks/{task_id}")
def get_task(
    task_id: int,
    user: UserContext = Depends(get_current_user),
    db=Depends(get_db)
):
    visibility_sql, parameters = get_task_visibility(user)

    cursor = db.cursor()

    query = f"""
        SELECT t.*
        FROM tasks AS t
        JOIN projects AS p
            ON p.id = t.project_id
           AND p.agency_id = t.agency_id
        WHERE t.id = %s
          AND {visibility_sql}
    """

    cursor.execute(
        query,
        [task_id] + parameters
    )

    task = cursor.fetchone()

    # Do not reveal whether an inaccessible task exists
    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return task


# Get all visible tasks for a project
@app.get("/projects/{project_id}/tasks")
def list_project_tasks(
    project_id: int,
    user: UserContext = Depends(get_current_user),
    db=Depends(get_db)
):
    visibility_sql, parameters = get_task_visibility(user)

    cursor = db.cursor()

    query = f"""
        SELECT t.*
        FROM tasks AS t
        JOIN projects AS p
            ON p.id = t.project_id
           AND p.agency_id = t.agency_id
        WHERE p.id = %s
          AND {visibility_sql}
        ORDER BY t.id
    """

    cursor.execute(
        query,
        [project_id] + parameters
    )

    return cursor.fetchall()
