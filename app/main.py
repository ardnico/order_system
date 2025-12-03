import os
import secrets
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
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
    RecurringTaskRule,
    RecurringFrequency,
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

UI_STRINGS = {
    "en": {
        "brand": "Household Chore Board",
        "nav.dashboard": "Dashboard",
        "nav.tasks": "Tasks",
        "nav.templates": "Task Templates",
        "nav.rewards": "Rewards",
        "nav.points": "Point History",
        "nav.settings": "Settings",
        "nav.logout": "Logout",
        "dashboard.title": "Welcome",
        "tasks.heading": "Tasks",
        "tasks.assigned": "Assigned to me",
        "tasks.all": "All tasks",
        "tasks.completed": "Completed",
        "tasks.orderSheet": "Order sheet",
        "tasks.new": "New Task",
        "tasks.edit": "Edit Task",
        "tasks.save": "Save Task",
        "tasks.assignee": "Assignee",
        "templates.heading": "Task Templates",
        "templates.instructions": "Instructions",
        "settings.heading": "Settings",
        "settings.language": "Language",
        "settings.recurring": "Recurring tasks",
        "settings.language.ja": "Japanese",
        "settings.language.en": "English",
        "settings.recurring.add": "Add recurring rule",
        "settings.recurring.next": "Next run date",
    },
    "ja": {
        "brand": "おうちタスクボード",
        "nav.dashboard": "ダッシュボード",
        "nav.tasks": "タスク",
        "nav.templates": "タスクテンプレート",
        "nav.rewards": "ごほうび",
        "nav.points": "ポイント履歴",
        "nav.settings": "設定",
        "nav.logout": "ログアウト",
        "dashboard.title": "ようこそ",
        "tasks.heading": "タスク一覧",
        "tasks.assigned": "担当タスク",
        "tasks.all": "全て",
        "tasks.completed": "完了済み",
        "tasks.orderSheet": "発注書ビュー",
        "tasks.new": "新規タスク",
        "tasks.edit": "タスク編集",
        "tasks.save": "保存",
        "tasks.assignee": "担当",
        "templates.heading": "タスクテンプレート",
        "templates.instructions": "実施手順",
        "settings.heading": "設定",
        "settings.language": "言語",
        "settings.recurring": "定期タスク設定",
        "settings.language.ja": "日本語",
        "settings.language.en": "英語",
        "settings.recurring.add": "定期ルール追加",
        "settings.recurring.next": "次回作成日",
    },
}

STATUS_LABELS = {
    "open": {"en": "Open", "ja": "発注中"},
    "assigned": {"en": "Assigned", "ja": "担当決定"},
    "in_progress": {"en": "In progress", "ja": "作業中"},
    "completed": {"en": "Completed", "ja": "完了報告"},
    "approved": {"en": "Approved", "ja": "承認済み"},
    "cancelled": {"en": "Cancelled", "ja": "キャンセル"},
}

PRIORITY_LABELS = {
    "high": {"en": "High", "ja": "高"},
    "medium": {"en": "Medium", "ja": "中"},
    "low": {"en": "Low", "ja": "低"},
}


def get_strings(language: str) -> dict:
    base = UI_STRINGS.get("en", {})
    localized = UI_STRINGS.get(language, {})
    merged = base.copy()
    merged.update(localized)
    return merged


def get_language(request: Request, session: Session, user: Optional[User] = None) -> str:
    lang = request.session.get("language")
    if not lang and user:
        household = session.get(Household, user.household_id)
        if household:
            lang = household.language
    lang = lang or "en"
    request.session["language"] = lang
    return lang


def translate_status(status: TaskStatus, language: str) -> str:
    return STATUS_LABELS.get(status.value, {}).get(language, status.value)


def translate_priority(priority: Priority, language: str) -> str:
    return PRIORITY_LABELS.get(priority.value, {}).get(language, priority.value)


def render_instructions(text: Optional[str]) -> Markup:
    if not text:
        return Markup("")
    lines = text.splitlines()
    html_parts: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{escape(stripped[2:])}</li>")
            continue
        if in_list:
            html_parts.append("</ul>")
            in_list = False
        if stripped.startswith("image::") and stripped.endswith("[]"):
            url = stripped[len("image::") : -2]
            html_parts.append(
                f"<div class='instruction-image-wrap'><img src='{escape(url)}' alt='instruction image' class='instruction-image'/></div>"
            )
        elif stripped.startswith("== "):
            html_parts.append(f"<h3>{escape(stripped[3:])}</h3>")
        elif stripped.startswith("= "):
            html_parts.append(f"<h2>{escape(stripped[2:])}</h2>")
        elif stripped:
            html_parts.append(f"<p>{escape(stripped)}</p>")
    if in_list:
        html_parts.append("</ul>")
    return Markup("\n".join(html_parts))


def build_context(
    request: Request, session: Session, user: Optional[User] = None, extra: Optional[dict] = None
) -> dict:
    language = get_language(request, session, user)
    context = {
        "request": request,
        "user": user,
        "language": language,
        "strings": get_strings(language),
        "flash_messages": pop_flash(request),
        "translate_status": translate_status,
        "translate_priority": translate_priority,
        "render_instructions": render_instructions,
    }
    if extra:
        context.update(extra)
    return context


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


def run_recurring_rules(session: Session, household_id: int, created_by_user_id: int):
    today = date.today()
    rules = session.exec(
        select(RecurringTaskRule).where(
            RecurringTaskRule.household_id == household_id,
            RecurringTaskRule.active == True,  # noqa: E712
            RecurringTaskRule.next_run_date <= today,
        )
    ).all()
    created_tasks: list[Task] = []
    for rule in rules:
        template = session.get(TaskTemplate, rule.task_template_id)
        if not template:
            continue
        due_date = today
        if template.relative_due_days is not None:
            due_date = today + timedelta(days=template.relative_due_days)
        order_num = next_order_number(session, household_id)
        task = Task(
            household_id=household_id,
            order_number=order_num,
            title=template.title,
            description=template.memo,
            category=template.default_category or "",
            due_date=due_date,
            proposed_points=template.default_points or 0,
            priority=Priority.medium,
            status=TaskStatus.open,
            created_by_user_id=created_by_user_id,
            assignee_user_id=rule.assignee_user_id,
            task_template_id=template.id,
            notes=template.memo,
        )
        session.add(task)
        created_tasks.append(task)
        if rule.frequency == RecurringFrequency.daily:
            rule.next_run_date = today + timedelta(days=1)
        elif rule.frequency == RecurringFrequency.weekly:
            rule.next_run_date = today + timedelta(days=7)
        else:
            rule.next_run_date = today + timedelta(days=30)
        session.add(rule)
    if created_tasks:
        session.commit()
    return created_tasks


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    run_recurring_rules(session, user.household_id, user.id)
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
        build_context(
            request,
            session,
            user,
            {
                "user_balance": user_balance,
                "household_balances": household_balances,
                "household_users": user_lookup,
                "assigned_tasks": assigned_tasks,
                "open_tasks": open_tasks,
                "transactions": recent_transactions,
            },
        ),
    )


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request, session: Session = Depends(get_session)):
    households = session.exec(select(Household)).all()
    return templates.TemplateResponse(
        "register.html",
        build_context(
            request,
            session,
            None,
            {"households": households},
        ),
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
        build_context(
            request,
            session,
            None,
            {"households": households},
        ),
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


@app.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    templates_list = session.exec(
        select(TaskTemplate).where(TaskTemplate.household_id == user.household_id)
    ).all()
    recurring_rules = session.exec(
        select(RecurringTaskRule).where(RecurringTaskRule.household_id == user.household_id)
    ).all()
    household_users = get_household_users(session, user.household_id)
    assignee_map = {u.id: u for u in household_users}
    household = session.get(Household, user.household_id)
    return templates.TemplateResponse(
        "settings.html",
        build_context(
            request,
            session,
            user,
            {
                "templates": templates_list,
                "recurring_rules": recurring_rules,
                "assignees": household_users,
                "assignee_map": assignee_map,
                "household": household,
                "today": date.today(),
            },
        ),
    )


@app.post("/settings/language")
async def update_language(
    request: Request,
    language: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    household = session.get(Household, user.household_id)
    if household:
        household.language = language
        session.add(household)
        session.commit()
    request.session["language"] = language
    flash(request, "Language updated")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/recurring")
async def add_recurring_rule(
    request: Request,
    task_template_id: int = Form(...),
    frequency: str = Form(...),
    next_run_date: Optional[date] = Form(None),
    assignee_user_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    rule = RecurringTaskRule(
        household_id=user.household_id,
        task_template_id=task_template_id,
        frequency=RecurringFrequency(frequency),
        next_run_date=next_run_date or date.today(),
        assignee_user_id=assignee_user_id,
    )
    session.add(rule)
    session.commit()
    flash(request, "Recurring rule added")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/recurring/{rule_id}/toggle")
async def toggle_recurring_rule(
    request: Request,
    rule_id: int,
    active: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    rule = session.exec(
        select(RecurringTaskRule).where(
            RecurringTaskRule.id == rule_id, RecurringTaskRule.household_id == user.household_id
        )
    ).first()
    if not rule:
        flash(request, "Rule not found", "error")
        return RedirectResponse("/settings", status_code=303)
    rule.active = active == "on"
    session.add(rule)
    session.commit()
    flash(request, "Rule updated")
    return RedirectResponse("/settings", status_code=303)


@app.get("/tasks", response_class=HTMLResponse)
def list_tasks(
    request: Request,
    status: Optional[str] = None,
    scope: str = "assigned",
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    run_recurring_rules(session, user.household_id, user.id)
    query = select(Task).where(Task.household_id == user.household_id)
    if status:
        query = query.where(Task.status == TaskStatus(status))
    elif scope == "completed":
        query = query.where(Task.status.in_([TaskStatus.completed, TaskStatus.approved]))
    elif scope == "all":
        query = query
    else:
        query = query.where(Task.assignee_user_id == user.id)
    tasks = session.exec(query.order_by(Task.due_date)).all()
    user_map = {u.id: u for u in get_household_users(session, user.household_id)}
    templates_list = session.exec(
        select(TaskTemplate).where(TaskTemplate.household_id == user.household_id)
    ).all()
    return templates.TemplateResponse(
        "tasks.html",
        build_context(
            request,
            session,
            user,
            {
                "tasks": tasks,
                "scope": scope,
                "status_filter": status,
                "templates": templates_list,
                "user_map": user_map,
            },
        ),
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
        build_context(
            request,
            session,
            user,
            {
                "template": template_data,
                "default_due_date": default_due_date,
                "assignees": get_household_users(session, user.household_id),
            },
        ),
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
    assignee_user_id: Optional[int] = Form(None),
    task_template_id: Optional[int] = Form(None),
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
        assignee_user_id=assignee_user_id or user.id,
        task_template_id=task_template_id,
        notes=notes,
    )
    session.add(task)
    session.commit()
    flash(request, "Task created")
    return RedirectResponse(f"/tasks/{task.id}", status_code=303)


@app.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_task_form(
    request: Request,
    task_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    task = get_task(session, user.household_id, task_id)
    return templates.TemplateResponse(
        "task_form.html",
        build_context(
            request,
            session,
            user,
            {
                "task": task,
                "default_due_date": task.due_date,
                "assignees": get_household_users(session, user.household_id),
            },
        ),
    )


@app.post("/tasks/{task_id}/edit")
async def edit_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form(...),
    due_date: date = Form(...),
    due_time: Optional[str] = Form(None),
    proposed_points: int = Form(...),
    priority: str = Form("medium"),
    notes: Optional[str] = Form(None),
    assignee_user_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    task = get_task(session, user.household_id, task_id)
    parsed_time: Optional[time] = None
    if due_time:
        try:
            parsed_time = datetime.strptime(due_time, "%H:%M").time()
        except ValueError:
            flash(request, "Invalid time format", "error")
            return RedirectResponse(f"/tasks/{task_id}/edit", status_code=303)
    task.title = title
    task.description = description
    task.category = category
    task.due_date = due_date
    task.due_time = parsed_time
    task.proposed_points = proposed_points
    task.priority = Priority(priority)
    task.notes = notes
    task.assignee_user_id = assignee_user_id or task.assignee_user_id or user.id
    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()
    flash(request, "Task updated")
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
        build_context(
            request,
            session,
            user,
            {
                "task": task,
                "assignee": assignee,
                "creator": creator,
                "related_tx": related_tx,
                "template": session.get(TaskTemplate, task.task_template_id)
                if task.task_template_id
                else None,
            },
        ),
    )


@app.get("/tasks/{task_id}/order", response_class=HTMLResponse)
def task_order_sheet(
    request: Request,
    task_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    task = get_task(session, user.household_id, task_id)
    assignee = session.get(User, task.assignee_user_id) if task.assignee_user_id else None
    creator = session.get(User, task.created_by_user_id)
    return templates.TemplateResponse(
        "task_order.html",
        build_context(
            request,
            session,
            user,
            {
                "task": task,
                "assignee": assignee,
                "creator": creator,
                "template": session.get(TaskTemplate, task.task_template_id)
                if task.task_template_id
                else None,
            },
        ),
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
        build_context(
            request,
            session,
            user,
            {"templates": templates_list},
        ),
    )


@app.post("/templates/tasks")
async def create_task_template(
    request: Request,
    title: str = Form(...),
    default_category: Optional[str] = Form(None),
    default_points: Optional[int] = Form(None),
    relative_due_days: Optional[int] = Form(None),
    memo: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    instruction_image_url: Optional[str] = Form(None),
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
        instructions=instructions,
        instruction_image_url=instruction_image_url,
    )
    session.add(template)
    session.commit()
    flash(request, "Template created")
    return RedirectResponse("/templates/tasks", status_code=303)


@app.post("/templates/tasks/{template_id}/edit")
async def edit_task_template(
    request: Request,
    template_id: int,
    title: str = Form(...),
    default_category: Optional[str] = Form(None),
    default_points: Optional[int] = Form(None),
    relative_due_days: Optional[int] = Form(None),
    memo: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    instruction_image_url: Optional[str] = Form(None),
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
    template.title = title
    template.default_category = default_category
    template.default_points = default_points
    template.relative_due_days = relative_due_days
    template.memo = memo
    template.instructions = instructions
    template.instruction_image_url = instruction_image_url
    session.add(template)
    session.commit()
    flash(request, "Template updated")
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
        build_context(
            request,
            session,
            user,
            {
                "templates": templates_list,
                "reward_uses": reward_uses,
                "user_map": user_map,
            },
        ),
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
        build_context(
            request,
            session,
            user,
            {
                "transactions": transactions,
                "balances": balances,
                "users": user_map,
            },
        ),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
