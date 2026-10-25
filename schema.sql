CREATE TABLE agencies (id SERIAL PRIMARY KEY, name TEXT NOT NULL);

CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL
);

CREATE TABLE clients (
  id SERIAL PRIMARY KEY,
  agency_id INTEGER NOT NULL REFERENCES agencies(id),
  name TEXT NOT NULL,
  UNIQUE (id, agency_id)
);

CREATE TABLE memberships (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  agency_id INTEGER NOT NULL REFERENCES agencies(id),
  role TEXT NOT NULL CHECK (role IN ('agency_admin','agency_member','client_user')),
  client_id INTEGER,
  UNIQUE (user_id, agency_id),
  UNIQUE (id, agency_id),
  FOREIGN KEY (client_id, agency_id) REFERENCES clients(id, agency_id),
  CHECK ((role = 'client_user') = (client_id IS NOT NULL))
);

CREATE TABLE projects (
  id SERIAL PRIMARY KEY,
  agency_id INTEGER NOT NULL REFERENCES agencies(id),
  client_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  UNIQUE (id, agency_id),
  FOREIGN KEY (client_id, agency_id) REFERENCES clients(id, agency_id)
);

CREATE TABLE project_members (
  project_id INTEGER NOT NULL,
  membership_id INTEGER NOT NULL,
  agency_id INTEGER NOT NULL,
  PRIMARY KEY (project_id, membership_id),
  FOREIGN KEY (project_id, agency_id) REFERENCES projects(id, agency_id),
  FOREIGN KEY (membership_id, agency_id) REFERENCES memberships(id, agency_id)
);

CREATE TABLE tasks (
  id SERIAL PRIMARY KEY,
  agency_id INTEGER NOT NULL REFERENCES agencies(id),
  project_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','in_progress','done')),
  priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
  assignee_id INTEGER,
  due_date DATE,
  is_internal BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (id, agency_id),
  FOREIGN KEY (project_id, agency_id) REFERENCES projects(id, agency_id),
  FOREIGN KEY (assignee_id, agency_id) REFERENCES memberships(id, agency_id)
);

CREATE TABLE comments (
  id SERIAL PRIMARY KEY,
  agency_id INTEGER NOT NULL REFERENCES agencies(id),
  task_id INTEGER NOT NULL,
  author_membership_id INTEGER NOT NULL,
  body TEXT NOT NULL,
  is_internal BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (task_id, agency_id) REFERENCES tasks(id, agency_id),
  FOREIGN KEY (author_membership_id, agency_id) REFERENCES memberships(id, agency_id)
);

CREATE TABLE files (
  id SERIAL PRIMARY KEY,
  agency_id INTEGER NOT NULL REFERENCES agencies(id),
  task_id INTEGER NOT NULL,
  filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  is_internal BOOLEAN NOT NULL DEFAULT TRUE,
  approval_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (approval_status IN ('pending','approved','needs_changes')),
  FOREIGN KEY (task_id, agency_id) REFERENCES tasks(id, agency_id)
);

CREATE TABLE time_entries (
  id SERIAL PRIMARY KEY,
  agency_id INTEGER NOT NULL REFERENCES agencies(id),
  task_id INTEGER NOT NULL,
  membership_id INTEGER NOT NULL,
  minutes INTEGER NOT NULL CHECK (minutes > 0),
  note TEXT,
  entry_date DATE NOT NULL,
  FOREIGN KEY (task_id, agency_id) REFERENCES tasks(id, agency_id),
  FOREIGN KEY (membership_id, agency_id) REFERENCES memberships(id, agency_id)
);

CREATE TABLE invites (
  id SERIAL PRIMARY KEY,
  agency_id INTEGER NOT NULL REFERENCES agencies(id),
  email TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('agency_admin','agency_member','client_user')),
  client_id INTEGER,
  token TEXT NOT NULL UNIQUE,
  accepted_at TIMESTAMPTZ,
  FOREIGN KEY (client_id, agency_id) REFERENCES clients(id, agency_id)
);
CREATE UNIQUE INDEX one_pending_invite
  ON invites (agency_id, lower(email)) WHERE accepted_at IS NULL;
