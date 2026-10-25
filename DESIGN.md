# Design Notes

## Tenant isolation
Every table carries agency_id. Child tables use composite foreign keys
such as (project_id, agency_id) -> projects(id, agency_id), so a row
cannot point at a parent in another agency. The database rejects it,
not just the application. Every query also filters on the agency_id
from the logged-in user's membership, never from the request.
Cross-tenant IDs return 404, so existence is not leaked.

## Blocking clients from internal content
tasks, comments and files have is_internal, defaulting to TRUE so a
forgotten flag stays hidden. Client queries add is_internal = false
and project.client_id = the client's own id. This lives in one helper,
visible_task_sql(), used by both the detail and list endpoints.
Comments and files must also check the parent task's flag.

## One person, two agencies
users holds only email and password. Role lives on memberships
(user_id, agency_id, role, client_id), unique per user and agency.
Login returns the memberships, then the user picks one. The token
carries only user_id and membership_id; role and agency are re-read
from the database on each request, so removing a membership revokes
access immediately.

## Edge case: invites
A partial unique index on (agency_id, lower(email)) WHERE
accepted_at IS NULL allows one pending invite per email, so resending
reuses the row. Accepting uses one atomic statement:
UPDATE invites SET accepted_at = now() WHERE token = :t AND
accepted_at IS NULL RETURNING *. Concurrent accepts: only one wins.

## Removing a member mid-task
In one transaction: delete the project_members row, then set
assignee_id = NULL on that project's tasks assigned to them.
Tasks become unassigned instead of orphaned.
(Designed, endpoint not yet built.)
