import bcrypt, psycopg2
from main import DSN

db = psycopg2.connect(DSN)
cur = db.cursor()

def one(sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()[0]

pw = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
cur.execute("""TRUNCATE agencies, users, clients, memberships, projects,
               project_members, tasks, comments, files, time_entries, invites
               RESTART IDENTITY CASCADE""")

def user(email):
    return one("INSERT INTO users(email,password_hash) VALUES(%s,%s) RETURNING id",
               [email, pw])

def member(u, agency, role, client=None):
    return one("""INSERT INTO memberships(user_id,agency_id,role,client_id)
                  VALUES(%s,%s,%s,%s) RETURNING id""", [u, agency, role, client])

alpha = one("INSERT INTO agencies(name) VALUES('Alpha Agency') RETURNING id")
beta = one("INSERT INTO agencies(name) VALUES('Beta Agency') RETURNING id")

acme = one("INSERT INTO clients(agency_id,name) VALUES(%s,'Acme') RETURNING id", [alpha])
zenith = one("INSERT INTO clients(agency_id,name) VALUES(%s,'Zenith') RETURNING id", [beta])

alice, mike, sam, bella = (user(e) for e in
    ["alice@alpha.com", "mike@alpha.com", "sam@example.com", "bella@beta.com"])

member(alice, alpha, "agency_admin")
mike_m = member(mike, alpha, "agency_member")
member(sam, alpha, "agency_admin")            # sam: admin at Alpha
member(sam, beta, "client_user", zenith)      # sam: client at Beta
member(bella, beta, "agency_admin")

pa = one("INSERT INTO projects(agency_id,client_id,name) VALUES(%s,%s,'Acme Website') RETURNING id", [alpha, acme])
pb = one("INSERT INTO projects(agency_id,client_id,name) VALUES(%s,%s,'Zenith App') RETURNING id", [beta, zenith])
cur.execute("INSERT INTO project_members VALUES(%s,%s,%s)", [pa, mike_m, alpha])

def task(agency, project, title, internal):
    cur.execute("""INSERT INTO tasks(agency_id,project_id,title,is_internal)
                   VALUES(%s,%s,%s,%s)""", [agency, project, title, internal])

task(alpha, pa, "Alpha internal task", True)
task(alpha, pa, "Alpha visible task", False)
task(beta, pb, "Beta internal task", True)
task(beta, pb, "Beta visible task", False)

db.commit()
print("seeded")
