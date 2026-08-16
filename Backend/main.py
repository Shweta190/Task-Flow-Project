
import time
import re
import os
import json
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import engine, get_db, Base
from models import User, Project, Task
from schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    ProjectCreate,
    ProjectResponse,
)
from algorithms import insertion_sort, binary_search, linear_search
import crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaskFlow API", version="2.0.0")

# A. Middleware: Log "METHOD PATH - TIMEms"
@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed_ms = (time.time() - start) * 1000
    print(f"{request.method} {request.url.path} - {elapsed_ms:.2f}ms")
    return response

# B. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")



# ─── Auth dependency ───

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = crud.decode_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = crud.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ─── Auth endpoints ───

@app.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=422, detail="email already registered")
    db_user = crud.create_user(db, user)
    token = crud.create_access_token({"user_id": db_user.id})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(db_user),
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = crud.create_access_token({"user_id": user.id})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@app.get("/auth/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


# ─── Users (legacy, still available) ───

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=422, detail="email already registered")
    db_user = crud.create_user(db, user)
    return db_user


@app.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


# ─── Projects ───

@app.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owner_id = project.owner_id or current_user.id
    owner = crud.get_user_by_id(db, owner_id)
    if not owner:
        raise HTTPException(status_code=422, detail="owner_id does not exist")
    db_project = Project(name=project.name, owner_id=owner_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@app.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Project).filter(Project.owner_id == current_user.id).all()


# ─── Tasks CRUD ───

@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if task.project_id is None:
        project = crud.get_project_by_owner(db, current_user.id)
        if not project:
            project = Project(name="Inbox", owner_id=current_user.id)
            db.add(project)
            db.commit()
            db.refresh(project)
        task.project_id = project.id
    else:
        project = crud.get_project_by_id(db, task.project_id)
        if not project or project.owner_id != current_user.id:
            raise HTTPException(status_code=422, detail="project_id does not exist")
    return crud.create_task(db, task)



@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    sort: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud.get_project_by_owner(db, current_user.id)
    if not project:
        return []
    tasks = crud.get_tasks_by_project(db, project.id)

    if sort == "none" or sort is None:
        return tasks

    sort_key_map = {"low": 1, "medium": 2, "high": 3}

    if sort == "priority":
        records = [
            {**_task_to_dict(t), "_sort_key": sort_key_map.get(t.priority, 2)}
            for t in tasks
        ]
        insertion_sort(records, "_sort_key")
        for r in records:
            r.pop("_sort_key", None)
        return records
    elif sort == "due_date":
        records = [{**_task_to_dict(t), "_sort_key": t.due_date or ""} for t in tasks]
        insertion_sort(records, "_sort_key")
        for r in records:
            r.pop("_sort_key", None)
        return records
    elif sort == "category":
        records = [{**_task_to_dict(t), "_sort_key": t.category or "General"} for t in tasks]
        insertion_sort(records, "_sort_key")
        for r in records:
            r.pop("_sort_key", None)
        return records
    elif sort == "title":
        records = [{**_task_to_dict(t), "_sort_key": t.title} for t in tasks]
        insertion_sort(records, "_sort_key")
        for r in records:
            r.pop("_sort_key", None)
        return records

    return tasks


def _task_to_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "category": t.category,
        "priority": t.priority,
        "due_date": t.due_date,
        "project_id": t.project_id,
        "status": t.status,
    }


# ─── Search endpoint (must come before /tasks/{task_id}) ───

@app.get("/tasks/search")
def search_tasks(
    title: str = Query(...),
    algo: str = Query("binary"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud.get_project_by_owner(db, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="task not found")
    tasks = crud.get_tasks_by_project(db, project.id)
    records = [{"id": t.id, "title": t.title} for t in tasks]

    if algo == "none":
        for r in records:
            if r["title"] == title:
                return r
        raise HTTPException(status_code=404, detail="task not found")

    insertion_sort(records, "title")

    if algo == "binary":
        index = binary_search(records, title, "title")
    elif algo == "linear":
        index = linear_search(records, title, "title")
    else:
        raise HTTPException(status_code=422, detail="algo must be 'binary', 'linear', or 'none'")

    if index == -1:
        raise HTTPException(status_code=404, detail="task not found")
    return records[index]


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = crud.get_task_by_id(db, task_id)
    if not task or task.project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = crud.get_task_by_id(db, task_id)
    if not task or task.project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="task not found")
    return crud.update_task(db, task, task_update)


@app.delete("/tasks/clear-all", status_code=200)
def clear_all_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud.get_project_by_owner(db, current_user.id)
    if not project:
        return {"detail": "no tasks to clear", "deleted": 0}
    count = crud.clear_all_tasks(db, project.id)
    return {"detail": "all tasks cleared", "deleted": count}


@app.delete("/tasks/{task_id}", status_code=200)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = crud.get_task_by_id(db, task_id)
    if not task or task.project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="task not found")
    crud.delete_task(db, task)
    return {"detail": "task deleted"}


@app.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = crud.get_task_by_id(db, task_id)
    if not task or task.project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="task not found")
    return crud.toggle_task_complete(db, task)


# ─── Stats ───

@app.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud.get_project_by_owner(db, current_user.id)
    if not project:
        return {
            "total": 0,
            "by_priority": {"low": 0, "medium": 0, "high": 0},
            "by_category": {},
            "by_status": {"pending": 0, "completed": 0},
        }
    return crud.get_task_stats(db, project.id)


@app.get("/projects/{project_id}/stats")
def project_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud.get_project_by_id(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="project not found")
    return crud.get_task_stats(db, project_id)


# ─── Section 3: AI Quick-Add ───

PRIORITY_KEYWORDS = {
    "high": ["urgent", "asap"],
    "low": ["whenever", "low priority"],
}

DATE_PHRASES = [
    "next monday", "next tuesday", "next wednesday",
    "next thursday", "next friday", "next saturday", "next sunday",
    "next week", "today", "tomorrow",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
]


@app.post("/tasks/quick-add", response_model=TaskResponse, status_code=201)
def quick_add(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    description = body.get("description", "")
    project = crud.get_project_by_owner(db, current_user.id)
    if not project:
        project = Project(name="Inbox", owner_id=current_user.id)
        db.add(project)
        db.commit()
        db.refresh(project)

    desc_lower = description.lower()

    priority = "medium"
    if any(kw in desc_lower for kw in PRIORITY_KEYWORDS["high"]):
        priority = "high"
    elif any(kw in desc_lower for kw in PRIORITY_KEYWORDS["low"]):
        priority = "low"

    due_date_hint = None
    matched_phrase = None
    for phrase in DATE_PHRASES:
        if phrase in desc_lower:
            due_date_hint = phrase
            matched_phrase = phrase
            break

    title = description
    for kw in PRIORITY_KEYWORDS["high"] + PRIORITY_KEYWORDS["low"]:
        title = re.sub(re.escape(kw), "", title, flags=re.IGNORECASE)
    if matched_phrase:
        title = re.sub(re.escape(matched_phrase), "", title, flags=re.IGNORECASE)
    title = title.strip()
    if not title:
        title = "Untitled task"

    task_data = TaskCreate(
        title=title,
        priority=priority,
        due_date=due_date_hint,
        project_id=project.id,
    )
    return crud.create_task(db, task_data)


# ─── Serve frontend static files ───

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

if os.path.isdir(FRONTEND_DIR):
    @app.get("/styles.css")
    def serve_styles():
        file_path = os.path.join(FRONTEND_DIR, "styles.css")
        if os.path.isfile(file_path):
            return FileResponse(file_path, media_type="text/css")
        raise HTTPException(status_code=404, detail="styles.css not found")

    @app.get("/script.js")
    def serve_script():
        file_path = os.path.join(FRONTEND_DIR, "script.js")
        if os.path.isfile(file_path):
            return FileResponse(file_path, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="script.js not found")

    @app.get("/")
    def serve_index():
        file_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.isfile(file_path):
            return FileResponse(file_path, media_type="text/html")
        return {"name": "TaskFlow API", "version": "2.0.0", "docs": "/docs"}

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")
        return {"detail": "Not found"}


