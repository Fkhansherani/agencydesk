
import psycopg2
from fastapi.testclient import TestClient

from main import app, DSN


client = TestClient(app)


# Find a task ID using its title
def get_task_id(title):
    with psycopg2.connect(DSN) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM tasks WHERE title = %s",
                (title,)
            )

            result = cursor.fetchone()

            if result is None:
                raise ValueError(f"Task not found: {title}")

            return result[0]


# Log in and select the required agency
def get_auth_headers(email, agency_name):
    login_response = client.post(
        "/login",
        json={
            "email": email,
            "password": "password123"
        }
    )

    assert login_response.status_code == 200

    memberships = login_response.json()["memberships"]

    selected_membership = next(
        (
            membership
            for membership in memberships
            if membership["agency"] == agency_name
        ),
        None
    )

    assert selected_membership is not None

    token_response = client.post(
        "/login",
        json={
            "email": email,
            "password": "password123",
            "membership_id": selected_membership["id"]
        }
    )

    assert token_response.status_code == 200

    access_token = token_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}"
    }


# Test 1: A user cannot access another agency's task
def test_cross_agency_task_returns_404():
    headers = get_auth_headers(
        "alice@alpha.com",
        "Alpha Agency"
    )

    beta_task_id = get_task_id("Beta visible task")

    response = client.get(
        f"/tasks/{beta_task_id}",
        headers=headers
    )

    assert response.status_code == 404


# Test 2: A client cannot access an internal task
def test_client_cannot_access_internal_task():
    headers = get_auth_headers(
        "sam@example.com",
        "Beta Agency"
    )

    internal_task_id = get_task_id("Beta internal task")

    response = client.get(
        f"/tasks/{internal_task_id}",
        headers=headers
    )

    assert response.status_code == 404


# Test 3: A client can access a visible task
def test_client_can_access_visible_task():
    headers = get_auth_headers(
        "sam@example.com",
        "Beta Agency"
    )

    visible_task_id = get_task_id("Beta visible task")

    response = client.get(
        f"/tasks/{visible_task_id}",
        headers=headers
    )

    assert response.status_code == 200


# Test 4: The task list must hide internal tasks from clients
def test_client_task_list_excludes_internal_tasks():
    headers = get_auth_headers(
        "sam@example.com",
        "Beta Agency"
    )

    response = client.get(
        "/projects/2/tasks",
        headers=headers
    )

    assert response.status_code == 200

    task_titles = [
        task["title"]
        for task in response.json()
    ]

    assert task_titles == ["Beta visible task"]


# Test 5: One user can have different roles in different agencies
def test_user_can_have_multiple_agency_roles():
    response = client.post(
        "/login",
        json={
            "email": "sam@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200

    memberships = response.json()["memberships"]

    user_roles = {
        membership["role"]
        for membership in memberships
    }

    assert user_roles == {
        "agency_admin",
        "client_user"
    }


# Test 6: An agency admin can access internal tasks in their agency
def test_admin_can_access_own_internal_task():
    headers = get_auth_headers(
        "alice@alpha.com",
        "Alpha Agency"
    )

    internal_task_id = get_task_id("Alpha internal task")

    response = client.get(
        f"/tasks/{internal_task_id}",
        headers=headers
    )

    assert response.status_code == 200
