from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import User, Project, Task
from schemas import UserCreate, TaskCreate, TaskUpdate

SECRET_KEY = "taskflow_secret_key_change_in_production_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440


#  Auth helpers

def hash_password(password: str) -> str:
    pwd_bytes = password[:72].encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password[:72].encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except JWTError:
        return None



#  User CRUD

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        name=user.name,
        password_hash=hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    default_project = Project(name="Inbox", owner_id=db_user.id)
    db.add(default_project)
    db.commit()
    db.refresh(default_project)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


#  Project CRUD

def get_project_by_owner(db: Session, owner_id: int) -> Optional[Project]:
    return db.query(Project).filter(Project.owner_id == owner_id).first()


def get_project_by_id(db: Session, project_id: int) -> Optional[Project]:
    return db.query(Project).filter(Project.id == project_id).first()


#  Task CRUD

def create_task(db: Session, task: TaskCreate) -> Task:
    db_task = Task(
        title=task.title,
        category=task.category,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_tasks_by_project(db: Session, project_id: int) -> list[Task]:
    return db.query(Task).filter(Task.project_id == project_id).all()


def get_task_by_id(db: Session, task_id: int) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id).first()


def update_task(db: Session, task: Task, updates: TaskUpdate) -> Task:
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()


def toggle_task_complete(db: Session, task: Task) -> Task:
    task.status = "completed" if task.status == "pending" else "pending"
    db.commit()
    db.refresh(task)
    return task


def clear_all_tasks(db: Session, project_id: int) -> int:
    count = db.query(Task).filter(Task.project_id == project_id).delete()
    db.commit()
    return count


#  Stats

def get_task_stats(db: Session, project_id: int) -> dict:
    total = db.query(func.count(Task.id)).filter(Task.project_id == project_id).scalar()
    total = total or 0

    priority_rows = (
        db.query(Task.priority, func.count(Task.id))
        .filter(Task.project_id == project_id)
        .group_by(Task.priority)
        .all()
    )
    by_priority = {"low": 0, "medium": 0, "high": 0}
    for priority, count in priority_rows:
        if priority in by_priority:
            by_priority[priority] = count

    category_rows = (
        db.query(Task.category, func.count(Task.id))
        .filter(Task.project_id == project_id)
        .group_by(Task.category)
        .all()
    )
    by_category = {}
    for category, count in category_rows:
        label = category or "General"
        by_category[label] = count

    status_rows = (
        db.query(Task.status, func.count(Task.id))
        .filter(Task.project_id == project_id)
        .group_by(Task.status)
        .all()
    )
    by_status = {"pending": 0, "completed": 0}
    for status, count in status_rows:
        if status in by_status:
            by_status[status] = count

    return {
        "total": total,
        "by_priority": by_priority,
        "by_category": by_category,
        "by_status": by_status,
    }
