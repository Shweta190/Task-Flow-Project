"""Seed script  populates the database with a demo user and sample tasks.
Run: python seed.py
"""

from database import engine, SessionLocal, Base
from models import User, Project, Task
import crud
from schemas import UserCreate, TaskCreate

Base.metadata.create_all(bind=engine)

db = SessionLocal()

DEMO_EMAIL = "demo@taskflow.io"
DEMO_PASSWORD = "demo1234"

existing = crud.get_user_by_email(db, DEMO_EMAIL)
if existing:
    print(f"Demo user already exists ({DEMO_EMAIL}). Skipping seed.")
    db.close()
    exit(0)

print("Creating demo user...")
user = crud.create_user(db, UserCreate(email=DEMO_EMAIL, name="Demo User", password=DEMO_PASSWORD))
project = crud.get_project_by_owner(db, user.id)
print(f"Created user id={user.id}, project id={project.id}")

sample_tasks = [
    ("Write project proposal", "Work", "high", "tomorrow"),
    ("Buy groceries", "Personal", "low", "today"),
    ("Review pull requests", "Work", "medium", "next monday"),
    ("Call dentist", "Personal", "medium", None),
    ("Fix login bug", "Work", "high", "today"),
    ("Plan weekend trip", "Personal", "low", "next week"),
    ("Submit expense report", "Work", "medium", "tomorrow"),
    ("Read chapter 5", "Learning", "low", "next friday"),
    ("Urgent server patch", "Work", "high", "today"),
    ("Organize desk", "Personal", "low", None),
]

for title, category, priority, due_date in sample_tasks:
    task = TaskCreate(
        title=title,
        category=category,
        priority=priority,
        due_date=due_date,
        project_id=project.id,
    )
    crud.create_task(db, task)

print(f"Inserted {len(sample_tasks)} sample tasks.")
print(f"\nLogin with: email={DEMO_EMAIL}  password={DEMO_PASSWORD}")

db.close()
