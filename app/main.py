import os
import secrets
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from .auth import hash_password, login_user, logout_user, require_user, verify_password
from .db import get_session, init_db
from .models import (
    Household,
    PointTransaction,
    PointTransactionType,
    Priority,
    RewardStatus,
    RewardTemplate,
    RewardUse,
    Task,
    TaskStatus,
    TaskTemplate,
    User,
)

app = FastAPI(title="Household chore board")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret"),
    session_cookie="ordersession",
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


@app.on_event("startup")
def on_startup():
    init_db()


def flash(request: Request, message: str, category: str = "info"):
    messages = request.session.get("flash", [])
    messages.append({"message": message, "category": category})
    request.session["flash"] = messages


def pop_flash(request: Request):
    messages = request.session.pop("flash", [])
    return messages


def calculate_user_balance(session: Session, user_id: int) -> int:
    total = session.exec(
        select(func.coalesce(func.sum(PointTransaction.amount), 0)).where(
            PointTransaction.user_id == user_id
        )
    ).one()
    return int(total or 0)


def calculate_household_balance(session: Session, household_id: int) -> dict[int, int]:
    rows = session.exec(
        select(PointTransaction.user_id, func.coalesce(func.sum(PointTransaction.amount), 0)).where(
            PointTransaction.household_id == household_id
        ).group_by(PointTransaction.user_id)
    ).all()
    return {user_id: int(total) for user_id, total in rows}


def get_household_users(session: Session, household_id: int):
    return session.exec(select(User).where(User.household_id == household_id)).all()


def next_order_number(session: Session, household_id: int) -> int:
    current_max = session.exec(
        select(func.max(Task.order_number)).where(Task.household_id == household_id)
    ).one()
    return int(current_max or 0) + 1


def get_task(session: Session, household_id: int, task_id: int) -> Task:
    task = session.exec(
        select(Task).where(Task.id == task_id, Task.household_id == household_id)
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def get_reward_use(session: Session, household_id: int, reward_use_id: int) -> RewardUse:
    reward_use = session.exec(
        select(RewardUse).where(
            RewardUse.id == reward_use_id, RewardUse.household_id == household_id
        )
    ).first()
    if not reward_use:
        raise HTTPException(status_code=404, detail="Reward use not found")
    return reward_use


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
): 
    user_balance = calculate_user_balance(session, user.id)
    household_balances = calculate_household_balance(session, user.household_id)
    household_users = get_household_users(session, user.household_id)
    user_lookup = {u.id: u for u in household_users}
    assigned_tasks = session.exec(
        select(Task).where(
            Task.household_id == user.household_id,
            Task.assignee_user_id == user.id,
            Task.status.in_([TaskStatus.assigned, TaskStatus.in_progress, TaskStatus.completed]),
        ).order_by(Task.due_date)
    ).all()
    open_tasks = session.exec(
        select(Task)
        .where(Task.household_id == user.household_id, Task.status == TaskStatus.open)
        .order_by(Task.due_date)
    ).all()
    recent_transactions = session.exec(
        select(PointTransaction)
        .where(PointTransaction.user_id == user.id)
        .order_by(PointTransaction.created_at.desc())
        .limit(10)
    ).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "user_balance": user_balance,
            "household_balances": household_balances,
            "household_users": user_lookup,
            "assigned_tasks": assigned_tasks,
            "open_tasks": open_tasks,
            "transactions": recent_transactions,
            "flash_messages": pop_flash(request),
        },
    )


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request, session: Session = Depends(get_session)):
    households = session.exec(select(Household)).all()
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "households": households, "flash_messages": pop_flash(request)},
    )


@app.post("/register")
async def register(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    create_household: Optional[str] = Form(None),
    household_name: Optional[str] = Form(None),
    join_code: Optional[str] = Form(None),
    household_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
):
    if create_household:
        if not household_name:
            flash(request, "Household name required", "error")
            return RedirectResponse("/register", status_code=303)
        code = join_code or secrets.token_hex(3)
        household = Household(name=household_name, join_code=code)
        session.add(household)
        session.commit()
        session.refresh(household)
    else:
        if not household_id:
            flash(request, "Select a household", "error")
            return RedirectResponse("/register", status_code=303)
        household = session.get(Household, household_id)
        if not household:
            flash(request, "Household not found", "error")
            return RedirectResponse("/register", status_code=303)
        if household.join_code and join_code != household.join_code:
            flash(request, "Invalid join code", "error")
            return RedirectResponse("/register", status_code=303)
    existing = session.exec(
        select(User).where(User.email == email, User.household_id == household.id)
    ).first()
    if existing:
        flash(request, "User already exists", "error")
        return RedirectResponse("/register", status_code=303)
    is_admin = not session.exec(select(User).where(User.household_id == household.id)).first()
    user = User(
        household_id=household.id,
        email=email,
        display_name=display_name,
        hashed_password=hash_password(password),
        is_admin=is_admin,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    login_user(request, user)
    flash(request, "Registered and logged in")
    return RedirectResponse("/", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, session: Session = Depends(get_session)):
    households = session.exec(select(Household)).all()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "households": households, "flash_messages": pop_flash(request)},
    )


@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    household_id: int = Form(...),
    session: Session = Depends(get_session),
):
    household = session.get(Household, household_id)
    if not household:
        flash(request, "Household not found", "error")
        return RedirectResponse("/login", status_code=303)
    user = session.exec(
        select(User).where(User.email == email, User.household_id == household_id)
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        flash(request, "Invalid credentials", "error")
        return RedirectResponse("/login", status_code=303)
    login_user(request, user)
    flash(request, "Logged in")
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    logout_user(request)
    response = RedirectResponse("/login", status_code=303)
    flash(request, "Logged out")
    return response


@app.get("/tasks", response_class=HTMLResponse)
def list_tasks(
    request: Request,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    query = select(Task).where(Task.household_id == user.household_id)
    if status:
        query = query.where(Task.status == TaskStatus(status))
    tasks = session.exec(query.order_by(Task.due_date)).all()
    user_map = {u.id: u for u in get_household_users(session, user.household_id)}
    templates_list = session.exec(
        select(TaskTemplate).where(TaskTemplate.household_id == user.household_id)
    ).all()
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "tasks": tasks,
            "user": user,
            "templates": templates_list,
            "user_map": user_map,
            "flash_messages": pop_flash(request),
        },
    )


@app.get("/tasks/new", response_class=HTMLResponse)
def new_task_form(
    request: Request,
    template_id: Optional[int] = None,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    template_data = None
    default_due_date = date.today()
    if template_id:
        template_data = session.exec(
            select(TaskTemplate).where(
                TaskTemplate.id == template_id,
                TaskTemplate.household_id == user.household_id,
            )
        ).first()
        if template_data and template_data.relative_due_days is not None:
            default_due_date = date.today() + timedelta(days=template_data.relative_due_days)
    return templates.TemplateResponse(
        "task_form.html",
        {
            "request": request,
            "user": user,
            "template": template_data,
            "default_due_date": default_due_date,
            "flash_messages": pop_flash(request),
        },
    )


@app.post("/tasks/new")
async def create_task(
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form(...),
    due_date: date = Form(...),
    due_time: Optional[str] = Form(None),
    proposed_points: int = Form(...),
    priority: str = Form("medium"),
    notes: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    order_num = next_order_number(session, user.household_id)
    parsed_time: Optional[time] = None
    if due_time:
        try:
            parsed_time = datetime.strptime(due_time, "%H:%M").time()
        except ValueError:
            flash(request, "Invalid time format", "error")
            return RedirectResponse("/tasks/new", status_code=303)
    task = Task(
        household_id=user.household_id,
        order_number=order_num,
        title=title,
        description=description,
        category=category,
        due_date=due_date,
        due_time=parsed_time,
        proposed_points=proposed_points,
        priority=Priority(priority),
        status=TaskStatus.open,
        created_by_user_id=user.id,
        notes=notes,
    )
    session.add(task)
    session.commit()
    flash(request, "Task created")
    return RedirectResponse(f"/tasks/{task.id}", status_code=303)


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_detail(
    request: Request,
    task_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    task = get_task(session, user.household_id, task_id)
    assignee = session.get(User, task.assignee_user_id) if task.assignee_user_id else None
    creator = session.get(User, task.created_by_user_id)
    related_tx = session.exec(
        select(PointTransaction).where(PointTransaction.related_task_id == task.id)
    ).first()
    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "task": task,
            "user": user,
            "assignee": assignee,
            "creator": creator,
            "related_tx": related_tx,
            "flash_messages": pop_flash(request),
        },
    )


@app.post("/tasks/{task_id}/action")
async def update_task_status(
    request: Request,
    task_id: int,
    action: str = Form(...),
    actual_points: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    task = get_task(session, user.household_id, task_id)
    now = datetime.utcnow()
    if action == "claim" and task.status == TaskStatus.open:
        task.assignee_user_id = user.id
        task.status = TaskStatus.assigned
    elif action == "start" and task.status in [TaskStatus.assigned, TaskStatus.open]:
        task.assignee_user_id = task.assignee_user_id or user.id
        task.status = TaskStatus.in_progress
    elif action == "complete" and task.status in [TaskStatus.in_progress, TaskStatus.assigned]:
        task.assignee_user_id = task.assignee_user_id or user.id
        task.status = TaskStatus.completed
        if actual_points is not None:
            task.actual_points = actual_points
    elif action == "approve" and task.status == TaskStatus.completed:
        task.status = TaskStatus.approved
        task.actual_points = actual_points or task.actual_points or task.proposed_points
        existing_tx = session.exec(
            select(PointTransaction).where(PointTransaction.related_task_id == task.id)
        ).first()
        if not existing_tx:
            target_user_id = task.assignee_user_id or task.created_by_user_id
            tx = PointTransaction(
                household_id=user.household_id,
                user_id=target_user_id,
                amount=task.actual_points,
                transaction_type=PointTransactionType.earn,
                description=f"Task {task.title} approved",
                related_task_id=task.id,
            )
            session.add(tx)
            flash(request, "Points awarded")
    elif action == "cancel" and task.status not in [TaskStatus.approved, TaskStatus.cancelled]:
        task.status = TaskStatus.cancelled
    else:
        flash(request, "Invalid action", "error")
        return RedirectResponse(f"/tasks/{task.id}", status_code=303)
    task.updated_at = now
    session.add(task)
    session.commit()
    flash(request, "Task updated")
    return RedirectResponse(f"/tasks/{task.id}", status_code=303)


@app.get("/templates/tasks", response_class=HTMLResponse)
def task_templates(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    templates_list = session.exec(
        select(TaskTemplate).where(TaskTemplate.household_id == user.household_id)
    ).all()
    return templates.TemplateResponse(
        "task_templates.html",
        {
            "request": request,
            "templates": templates_list,
            "user": user,
            "flash_messages": pop_flash(request),
        },
    )


@app.post("/templates/tasks")
async def create_task_template(
    request: Request,
    title: str = Form(...),
    default_category: Optional[str] = Form(None),
    default_points: Optional[int] = Form(None),
    relative_due_days: Optional[int] = Form(None),
    memo: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    template = TaskTemplate(
        household_id=user.household_id,
        title=title,
        default_category=default_category,
        default_points=default_points,
        relative_due_days=relative_due_days,
        memo=memo,
    )
    session.add(template)
    session.commit()
    flash(request, "Template created")
    return RedirectResponse("/templates/tasks", status_code=303)


@app.post("/templates/tasks/{template_id}/delete")
async def delete_task_template(
    request: Request,
    template_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    template = session.exec(
        select(TaskTemplate).where(
            TaskTemplate.id == template_id, TaskTemplate.household_id == user.household_id
        )
    ).first()
    if not template:
        flash(request, "Template not found", "error")
        return RedirectResponse("/templates/tasks", status_code=303)
    session.delete(template)
    session.commit()
    flash(request, "Template deleted")
    return RedirectResponse("/templates/tasks", status_code=303)


@app.get("/rewards", response_class=HTMLResponse)
def reward_templates(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    templates_list = session.exec(
        select(RewardTemplate).where(RewardTemplate.household_id == user.household_id)
    ).all()
    reward_uses = session.exec(
        select(RewardUse).where(RewardUse.household_id == user.household_id)
    ).all()
    user_map = {u.id: u for u in get_household_users(session, user.household_id)}
    return templates.TemplateResponse(
        "rewards.html",
        {
            "request": request,
            "templates": templates_list,
            "reward_uses": reward_uses,
            "user": user,
            "user_map": user_map,
            "flash_messages": pop_flash(request),
        },
    )


@app.post("/rewards/templates")
async def create_reward_template(
    request: Request,
    title: str = Form(...),
    cost_points: int = Form(...),
    memo: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    template = RewardTemplate(
        household_id=user.household_id,
        title=title,
        cost_points=cost_points,
        memo=memo,
    )
    session.add(template)
    session.commit()
    flash(request, "Reward template created")
    return RedirectResponse("/rewards", status_code=303)


@app.post("/rewards/templates/{template_id}/delete")
async def delete_reward_template(
    request: Request,
    template_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    template = session.exec(
        select(RewardTemplate).where(
            RewardTemplate.id == template_id,
            RewardTemplate.household_id == user.household_id,
        )
    ).first()
    if not template:
        flash(request, "Template not found", "error")
        return RedirectResponse("/rewards", status_code=303)
    session.delete(template)
    session.commit()
    flash(request, "Reward template deleted")
    return RedirectResponse("/rewards", status_code=303)


@app.post("/rewards/use")
async def request_reward_use(
    request: Request,
    title: str = Form(...),
    cost_points: int = Form(...),
    reward_template_id: Optional[int] = Form(None),
    note: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    reward_use = RewardUse(
        household_id=user.household_id,
        user_id=user.id,
        reward_template_id=reward_template_id,
        title=title,
        cost_points=cost_points,
        note=note,
    )
    session.add(reward_use)
    session.commit()
    flash(request, "Reward request submitted")
    return RedirectResponse("/rewards", status_code=303)


@app.post("/rewards/use/{reward_use_id}/action")
async def handle_reward_use(
    request: Request,
    reward_use_id: int,
    action: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    reward_use = get_reward_use(session, user.household_id, reward_use_id)
    if action == "approve" and reward_use.status == RewardStatus.pending:
        reward_use.status = RewardStatus.approved
        reward_use.approved_by_user_id = user.id
        reward_use.approved_at = datetime.utcnow()
        existing = session.exec(
            select(PointTransaction).where(
                PointTransaction.related_reward_use_id == reward_use.id
            )
        ).first()
        if not existing:
            tx = PointTransaction(
                household_id=user.household_id,
                user_id=reward_use.user_id,
                amount=-abs(reward_use.cost_points),
                transaction_type=PointTransactionType.spend,
                description=f"Reward approved: {reward_use.title}",
                related_reward_use_id=reward_use.id,
            )
            session.add(tx)
    elif action == "reject" and reward_use.status == RewardStatus.pending:
        reward_use.status = RewardStatus.rejected
    else:
        flash(request, "Invalid action", "error")
        return RedirectResponse("/rewards", status_code=303)
    session.add(reward_use)
    session.commit()
    flash(request, "Reward updated")
    return RedirectResponse("/rewards", status_code=303)


@app.get("/points", response_class=HTMLResponse)
def point_history(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    transactions = session.exec(
        select(PointTransaction)
        .where(PointTransaction.household_id == user.household_id)
        .order_by(PointTransaction.created_at.desc())
    ).all()
    balances = calculate_household_balance(session, user.household_id)
    users = session.exec(select(User).where(User.household_id == user.household_id)).all()
    user_map = {u.id: u for u in users}
    return templates.TemplateResponse(
        "points.html",
        {
            "request": request,
            "transactions": transactions,
            "balances": balances,
            "users": user_map,
            "user": user,
            "flash_messages": pop_flash(request),
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
