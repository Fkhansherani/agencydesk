
import bcrypt
import psycopg2

from main import DSN


# Connect to the PostgreSQL database
connection = psycopg2.connect(DSN)
cursor = connection.cursor()


# Execute a query and return the first column of its result
def get_inserted_id(query, values=()):
    cursor.execute(query, values)
    return cursor.fetchone()[0]


# Create a password hash for all test users
password_hash = bcrypt.hashpw(
    b"password123",
    bcrypt.gensalt()
).decode("utf-8")


try:
    # Clear existing test data and reset generated IDs
    cursor.execute("""
        TRUNCATE TABLE
            agencies,
            users,
            clients,
            memberships,
            projects,
            project_members,
            tasks,
            comments,
            files,
            time_entries,
            invites
        RESTART IDENTITY CASCADE
    """)

    # Create a user account
    def create_user(email):
        query = """
            INSERT INTO users (email, password_hash)
            VALUES (%s, %s)
            RETURNING id
        """

        return get_inserted_id(
            query,
            (email, password_hash)
        )

    # Add a user to an agency with a specific role
    def create_membership(user_id, agency_id, role, client_id=None):
        query = """
            INSERT INTO memberships (
                user_id,
                agency_id,
                role,
                client_id
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """

        return get_inserted_id(
            query,
            (user_id, agency_id, role, client_id)
        )

    # Create two agencies
    alpha_agency_id = get_inserted_id(
        "INSERT INTO agencies (name) VALUES (%s) RETURNING id",
        ("Alpha Agency",)
    )

    beta_agency_id = get_inserted_id(
        "INSERT INTO agencies (name) VALUES (%s) RETURNING id",
        ("Beta Agency",)
    )

    # Add one client to each agency
    acme_client_id = get_inserted_id(
        """
        INSERT INTO clients (agency_id, name)
        VALUES (%s, %s)
        RETURNING id
        """,
        (alpha_agency_id, "Acme")
    )

    zenith_client_id = get_inserted_id(
        """
        INSERT INTO clients (agency_id, name)
        VALUES (%s, %s)
        RETURNING id
        """,
        (beta_agency_id, "Zenith")
    )

    # Create four test users
    alice_id = create_user("alice@alpha.com")
    mike_id = create_user("mike@alpha.com")
    sam_id = create_user("sam@example.com")
    bella_id = create_user("bella@beta.com")

    # Assign agency roles and client access
    create_membership(
        alice_id,
        alpha_agency_id,
        "agency_admin"
    )

    mike_membership_id = create_membership(
        mike_id,
        alpha_agency_id,
        "agency_member"
    )

    # Sam belongs to two agencies with different roles
    create_membership(
        sam_id,
        alpha_agency_id,
        "agency_admin"
    )

    create_membership(
        sam_id,
        beta_agency_id,
        "client_user",
        zenith_client_id
    )

    create_membership(
        bella_id,
        beta_agency_id,
        "agency_admin"
    )

    # Create a project for each agency
    alpha_project_id = get_inserted_id(
        """
        INSERT INTO projects (agency_id, client_id, name)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (
            alpha_agency_id,
            acme_client_id,
            "Acme Website"
        )
    )

    beta_project_id = get_inserted_id(
        """
        INSERT INTO projects (agency_id, client_id, name)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (
            beta_agency_id,
            zenith_client_id,
            "Zenith App"
        )
    )

    # Give Mike access to the Alpha project
    cursor.execute(
        """
        INSERT INTO project_members
        VALUES (%s, %s, %s)
        """,
        (
            alpha_project_id,
            mike_membership_id,
            alpha_agency_id
        )
    )

    # Create a task for testing access permissions
    def create_task(agency_id, project_id, title, is_internal):
        cursor.execute(
            """
            INSERT INTO tasks (
                agency_id,
                project_id,
                title,
                is_internal
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                agency_id,
                project_id,
                title,
                is_internal
            )
        )

    # Alpha Agency tasks
    create_task(
        alpha_agency_id,
        alpha_project_id,
        "Alpha internal task",
        True
    )

    create_task(
        alpha_agency_id,
        alpha_project_id,
        "Alpha visible task",
        False
    )

    # Beta Agency tasks
    create_task(
        beta_agency_id,
        beta_project_id,
        "Beta internal task",
        True
    )

    create_task(
        beta_agency_id,
        beta_project_id,
        "Beta visible task",
        False
    )

    # Save all inserted records
    connection.commit()

    print("Test data inserted successfully.")

except Exception:
    connection.rollback()
    raise

finally:
    cursor.close()
    connection.close()
