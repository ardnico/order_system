import json
import os
import secrets
from datetime import date, datetime, time, timedelta
from typing import Optional

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from sqlalchemy import func
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from .auth import (
    get_current_user,
    hash_password,
    login_user,
    logout_user,
    require_user,
    verify_password,
)
from .db import get_session, init_db
from .models import (
    Household,
    PointTransaction,
    PointTransactionType,
    RewardStatus,
    RewardTemplate,
    RewardUse,
    Task,
    TaskStatus,
    TaskCategory,
    TaskTemplate,
    User,
    RecurringTaskRule,
    RecurringFrequency,
    Ingredient,
    DishType,
    UnitOption,
    MealSlot,
    Menu,
    MenuIngredient,
    MealPlan,
    MealPlanDay,
    MealSetTemplate,
    MealSetRequirement,
    MealPlanSelection,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Household chore board", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret"),
    session_cookie="ordersession",
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
uploads_dir = os.path.join(static_dir, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
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
        "nav.mealPlans": "Meal Plans",
        "nav.menus": "Menus",
        "nav.settings": "Settings",
        "nav.ingredients": "Ingredients",
        "nav.help": "How to use",
        "nav.logout": "Logout",
        "auth.login.title": "Login",
        "auth.login.email": "Email",
        "auth.login.password": "Password",
        "auth.login.household": "Household",
        "auth.login.submit": "Login",
        "auth.login.noAccount": "No account? Register",
        "auth.register.title": "Register",
        "auth.register.displayName": "Display name",
        "auth.register.email": "Email",
        "auth.register.password": "Password",
        "auth.register.createHousehold": "Create household",
        "auth.register.joinExisting": "Join existing",
        "auth.register.householdName": "Household name",
        "auth.register.joinCodeOptional": "Join code (optional)",
        "auth.register.joinCodeExisting": "Join code",
        "auth.register.selectHousehold": "Select household",
        "auth.register.submit": "Register",
        "auth.register.loginLink": "Already registered?",
        "auth.selectPlaceholder": "-- choose --",
        "dashboard.title": "Welcome",
        "dashboard.balance": "My balance",
        "dashboard.house": "Household balances",
        "dashboard.noAssigned": "No assigned tasks",
        "dashboard.open": "Open tasks",
        "dashboard.noOpen": "No open tasks",
        "dashboard.recent": "Recent transactions",
        "dashboard.noHistory": "No history yet",
        "tasks.heading": "Tasks",
        "tasks.assigned": "Assigned to me",
        "tasks.all": "All tasks",
        "tasks.completed": "Completed",
        "tasks.orderSheet": "Order sheet",
        "tasks.new": "New Task",
        "tasks.edit": "Edit Task",
        "tasks.save": "Save Task",
        "tasks.assignee": "Assignee",
        "tasks.detail": "Detail",
        "tasks.detailLink": "Detail",
        "tasks.createFromTemplate": "Create from template",
        "tasks.none": "(No tasks in this view)",
        "tasks.noTemplates": "No templates yet.",
        "tasks.category": "Category",
        "tasks.due": "Due",
        "tasks.priority": "Priority",
        "tasks.points": "Points",
        "tasks.creator": "Creator",
        "tasks.description": "Description",
        "tasks.notes": "Notes",
        "tasks.claim": "Claim",
        "tasks.start": "Start",
        "tasks.submit": "Submit completion",
        "tasks.approve": "Approve",
        "tasks.cancel": "Cancel",
        "tasks.active": "Active",
        "tasks.pointsAwarded": "Points awarded",
        "tasks.instructionsHint": "Use image::<url>[] to embed photos.",
        "templates.heading": "Task Templates",
        "templates.instructions": "Instructions",
        "templates.new": "New template",
        "templates.existing": "Existing templates",
        "templates.relative": "Relative due days",
        "templates.memo": "Memo",
        "templates.save": "Save",
        "templates.update": "Update",
        "templates.delete": "Delete",
        "templates.upload": "Upload instruction image",
        "templates.uploaded": "Uploaded image",
        "templates.embedGuide": "Embed with image::<url>[] inside instructions.",
        "menus.heading": "Menus",
        "menus.new": "Add menu",
        "menus.name": "Menu name",
        "menus.description": "Description",
        "menus.ingredients": "Ingredients",
        "menus.unit": "Unit",
        "menus.quantity": "Quantity",
        "menus.save": "Save menu",
        "menus.edit": "Edit menu",
        "menus.delete": "Delete",
        "menus.none": "No menus yet.",
        "mealPlans.heading": "Meal plans",
        "mealPlans.new": "Create plan",
        "mealPlans.name": "Plan name",
        "mealPlans.start": "Start date",
        "mealPlans.end": "End date",
        "mealPlans.open": "Open plan",
        "mealPlans.none": "No meal plans yet.",
        "mealPlans.detail": "Meal plan",
        "mealPlans.lunch": "Lunch",
        "mealPlans.dinner": "Dinner",
        "mealPlans.save": "Save plan",
        "mealPlans.ingredients": "Ingredients list",
        "ingredients.heading": "Ingredients",
        "ingredients.total": "Total quantity",
        "ingredients.unit": "Unit",
        "settings.heading": "Settings",
        "settings.language": "Language",
        "settings.recurring": "Recurring tasks",
        "settings.language.ja": "Japanese",
        "settings.language.en": "English",
        "settings.recurring.add": "Add recurring rule",
        "settings.recurring.next": "Next run date",
        "settings.frequency.daily": "Daily",
        "settings.frequency.weekly": "Weekly",
        "settings.frequency.monthly": "Monthly",
        "settings.recurring.none": "No recurring rules yet.",
        "settings.theme": "Color theme",
        "settings.theme.sakura": "Sakura pastel",
        "settings.theme.mint": "Mint soda",
        "settings.theme.creamsicle": "Creamsicle",
        "settings.theme.night": "Twilight",
        "settings.font": "Font",
        "settings.font.modern": "Modern sans",
        "settings.font.serif": "Serif",
        "settings.font.rounded": "Rounded",
        "settings.categories": "Task categories",
        "settings.categories.add": "Add category",
        "settings.dishTypes": "Dish types",
        "settings.mealSets": "Meal set templates",
        "settings.update": "Update",
        "settings.householdName": "Household name",
        "settings.joinCode": "Join code",
        "settings.joinCode.description": "Share this code so others can register.",
        "settings.joinCode.regenerate": "Regenerate code",
        "settings.joinCode.placeholder": "autogenerated if blank",
        "settings.updated": "Settings updated",
        "rewards.heading": "Rewards",
        "rewards.create": "Create reward template",
        "rewards.title": "Title",
        "rewards.cost": "Cost points",
        "rewards.memo": "Memo",
        "rewards.save": "Save",
        "rewards.templates": "Reward templates",
        "rewards.delete": "Delete",
        "rewards.request": "Request",
        "rewards.list": "Reward requests",
        "rewards.status": "Status",
        "rewards.owner": "Owner",
        "rewards.action": "Action",
        "rewards.none": "No reward requests yet.",
        "points.heading": "Point History",
        "points.balances": "Balances",
        "points.date": "Date",
        "points.user": "User",
        "points.amount": "Amount",
        "points.type": "Type",
        "points.description": "Description",
        "help.title": "How to use",
        "help.overview": "Organize chores, rewards, and meals with your household. Start here:",
        "help.step.signup": "Sign up: create a household or join an existing one with the join code.",
        "help.step.invite": "Invite: share the join code from Settings so others can register.",
        "help.step.tasks": "Tasks: create tasks or templates, assign or claim them, and submit for approval.",
        "help.step.rewards": "Rewards: set reward templates and approve requests when points are spent.",
        "help.step.mealPlans": "Meals: manage menus and meal plans, using dish types and sets.",
        "help.step.settings": "Settings: choose language (default Japanese), theme, font, and manage categories.",
        "help.section.heading": "Quick tips",
        "help.language": "Language switching updates immediately after saving in Settings. Japanese is the default for new sessions.",
        "help.joinCode": "Find your household join code in Settings; members must enter it during registration.",
        "help.settingsDetail": "Use Settings to align the household name, join code, language, theme, and font so everyone sees the same defaults.",
        "help.tasksDetail": "Task templates speed up recurring chores; assign or claim tasks from the Tasks page.",
        "help.support": "Need help? Check the navigation for this page anytime.",
        "ingredients.heading": "Ingredients",
        "ingredients.subhead": "Keep a reusable pantry list for menus and meal plans.",
        "ingredients.name": "Ingredient name",
        "ingredients.unit": "Unit",
        "ingredients.create": "Add ingredient",
        "ingredients.delete": "Delete",
        "ingredients.deleteBlocked": "Cannot delete while used in menus",
        "ingredients.empty": "No ingredients yet",
        "data.heading": "Data", 
        "data.export": "Export data",
        "data.import": "Import data",
        "data.description": "Download a JSON backup of household settings and menus, or import one to restore.",
        "data.file": "Choose JSON file",
        "data.importSuccess": "Data imported",
        "data.importError": "Import failed: invalid file",
        "help.hero": "Cozy guidebook",
        "help.cta.register": "Register",
        "help.cta.login": "Login",
        "help.ribbon.tasks": "Tasks & points",
        "help.ribbon.meals": "Meals & ingredients",
        "help.ribbon.data": "Backups",
        "help.quickstart.title": "Quick start",
        "help.quickstart.invite": "Invite with the join code",
        "help.quickstart.customize": "Customize the theme",
        "help.quickstart.menus": "Save favorite menus",
        "help.quickstart.export": "Export household data",
        "help.sections.tasks": "Create templates for chores, claim tasks, and approve completions to award points.",
        "help.sections.rewards": "Set rewards and approve requests when someone spends points.",
        "help.sections.meals": "Plan meals with menus, dish types, and ingredient totals.",
        "help.sections.data": "Use export/import as a safety net before big edits.",
    },
    "ja": {
        "brand": "おうちタスクボード",
        "nav.dashboard": "ダッシュボード",
        "nav.tasks": "タスク",
        "nav.templates": "タスクテンプレート",
        "nav.rewards": "ごほうび",
        "nav.points": "ポイント履歴",
        "nav.mealPlans": "献立",
        "nav.menus": "メニュー",
        "nav.ingredients": "材料リスト",
        "nav.settings": "設定",
        "nav.help": "使い方",
        "nav.logout": "ログアウト",
        "auth.login.title": "ログイン",
        "auth.login.email": "メールアドレス",
        "auth.login.password": "パスワード",
        "auth.login.household": "参加先",
        "auth.login.submit": "ログイン",
        "auth.login.noAccount": "未登録の方はこちら",
        "auth.register.title": "新規登録",
        "auth.register.displayName": "表示名",
        "auth.register.email": "メールアドレス",
        "auth.register.password": "パスワード",
        "auth.register.createHousehold": "世帯を作成",
        "auth.register.joinExisting": "既存の世帯に参加",
        "auth.register.householdName": "世帯名",
        "auth.register.joinCodeOptional": "参加コード (任意)",
        "auth.register.joinCodeExisting": "参加コード",
        "auth.register.selectHousehold": "世帯を選択",
        "auth.register.submit": "登録",
        "auth.register.loginLink": "登録済みの方はこちら",
        "auth.selectPlaceholder": "-- 選択 --",
        "dashboard.title": "ようこそ",
        "dashboard.balance": "自分の残高",
        "dashboard.house": "家族の残高一覧",
        "dashboard.noAssigned": "担当タスクなし",
        "dashboard.open": "未対応タスク",
        "dashboard.noOpen": "未対応タスクなし",
        "dashboard.recent": "最近の取引",
        "dashboard.noHistory": "履歴はまだありません",
        "tasks.heading": "タスク一覧",
        "tasks.assigned": "担当タスク",
        "tasks.all": "全て",
        "tasks.completed": "完了済み",
        "tasks.orderSheet": "発注書ビュー",
        "tasks.new": "新規タスク",
        "tasks.edit": "タスク編集",
        "tasks.save": "保存",
        "tasks.assignee": "担当",
        "tasks.detail": "詳細",
        "tasks.detailLink": "詳細",
        "tasks.createFromTemplate": "テンプレートから作成",
        "tasks.none": "(該当タスクなし)",
        "tasks.noTemplates": "テンプレートがまだありません",
        "tasks.category": "カテゴリ",
        "tasks.due": "期限",
        "tasks.priority": "優先度",
        "tasks.points": "ポイント",
        "tasks.creator": "作成者",
        "tasks.description": "説明",
        "tasks.notes": "メモ",
        "tasks.claim": "受注する",
        "tasks.start": "開始する",
        "tasks.submit": "完了を提出",
        "tasks.approve": "承認する",
        "tasks.cancel": "キャンセル",
        "tasks.active": "有効",
        "tasks.pointsAwarded": "ポイント付与済み",
        "tasks.instructionsHint": "image::<url>[] で写真を挿入できます",
        "templates.heading": "タスクテンプレート",
        "templates.instructions": "実施手順",
        "templates.new": "新規テンプレート",
        "templates.existing": "テンプレート一覧",
        "templates.relative": "相対期限(日)",
        "templates.memo": "メモ",
        "templates.save": "保存",
        "templates.update": "更新",
        "templates.delete": "削除",
        "templates.upload": "手順用の画像をアップロード",
        "templates.uploaded": "アップロード済み画像",
        "templates.embedGuide": "手順に image::<url>[] を差し込んで表示できます",
        "menus.heading": "メニュー",
        "menus.new": "メニュー追加",
        "menus.name": "メニュー名",
        "menus.description": "説明",
        "menus.ingredients": "材料",
        "menus.unit": "単位",
        "menus.quantity": "数量",
        "menus.save": "メニューを保存",
        "menus.edit": "メニュー編集",
        "menus.delete": "削除",
        "menus.none": "メニューはまだありません",
        "mealPlans.heading": "献立",
        "mealPlans.new": "献立を作成",
        "mealPlans.name": "献立名",
        "mealPlans.start": "開始日",
        "mealPlans.end": "終了日",
        "mealPlans.open": "開く",
        "mealPlans.none": "献立はまだありません",
        "mealPlans.detail": "献立詳細",
        "mealPlans.lunch": "昼",
        "mealPlans.dinner": "夜",
        "mealPlans.save": "献立を保存",
        "mealPlans.ingredients": "材料一覧",
        "ingredients.heading": "材料",
        "ingredients.total": "合計数量",
        "ingredients.unit": "単位",
        "settings.heading": "設定",
        "settings.language": "言語",
        "settings.recurring": "定期タスク設定",
        "settings.language.ja": "日本語",
        "settings.language.en": "英語",
        "settings.recurring.add": "定期ルール追加",
        "settings.recurring.next": "次回作成日",
        "settings.frequency.daily": "毎日",
        "settings.frequency.weekly": "毎週",
        "settings.frequency.monthly": "毎月",
        "settings.recurring.none": "定期ルールはまだありません",
        "settings.theme": "カラーテーマ",
        "settings.theme.sakura": "さくらパステル",
        "settings.theme.mint": "ミントソーダ",
        "settings.theme.creamsicle": "クリームソーダ",
        "settings.theme.night": "ゆめかわツイライト",
        "settings.font": "フォント",
        "settings.font.modern": "モダン",
        "settings.font.serif": "セリフ",
        "settings.font.rounded": "まるみ",
        "settings.categories": "タスクカテゴリ",
        "settings.categories.add": "カテゴリ追加",
        "settings.dishTypes": "料理タイプ",
        "settings.mealSets": "セットテンプレート",
        "settings.update": "更新",
        "settings.householdName": "世帯名",
        "settings.joinCode": "参加コード",
        "settings.joinCode.description": "家族に共有すると登録できます",
        "settings.joinCode.regenerate": "コードを再発行",
        "settings.joinCode.placeholder": "未入力なら自動生成",
        "settings.updated": "設定を保存しました",
        "rewards.heading": "ごほうび",
        "rewards.create": "ごほうびテンプレート作成",
        "rewards.title": "タイトル",
        "rewards.cost": "必要ポイント",
        "rewards.memo": "メモ",
        "rewards.save": "保存",
        "rewards.templates": "テンプレート一覧",
        "rewards.delete": "削除",
        "rewards.request": "申請",
        "rewards.list": "ごほうび申請一覧",
        "rewards.status": "ステータス",
        "rewards.owner": "申請者",
        "rewards.action": "操作",
        "rewards.none": "申請はまだありません。",
        "points.heading": "ポイント履歴",
        "points.balances": "残高一覧",
        "points.date": "日付",
        "points.user": "ユーザー",
        "points.amount": "ポイント",
        "points.type": "種別",
        "points.description": "詳細",
        "help.title": "使い方",
        "help.overview": "家事・ごほうび・献立を家族で共有するためのアプリです。始め方:",
        "help.step.signup": "登録: 世帯を作成するか、参加コードで既存の世帯に参加します。",
        "help.step.invite": "招待: 設定ページの参加コードを共有すると他のメンバーが登録できます。",
        "help.step.tasks": "タスク: タスクやテンプレートを作成し、担当を決めて完了を提出します。",
        "help.step.rewards": "ごほうび: テンプレートを作成し、ポイント使用の申請を承認します。",
        "help.step.mealPlans": "献立: メニューと献立を管理し、料理タイプやセットを活用します。",
        "help.step.settings": "設定: 言語(デフォルトは日本語)、テーマ、フォント、カテゴリを管理します。",
        "help.section.heading": "クイックヒント",
        "help.language": "言語切り替えは設定保存後すぐ反映されます。新しいセッションでは日本語が既定です。",
        "help.joinCode": "参加コードは設定ページに表示され、登録時に入力してもらいます。",
        "help.settingsDetail": "設定ページで世帯名、参加コード、言語、テーマ、フォントを整えると全員に反映されます。",
        "help.tasksDetail": "タスクテンプレートで定番の家事を素早く作成し、タスクページで担当や受注を管理できます。",
        "help.support": "困ったときはいつでもナビゲーションの「使い方」からこのページを開けます。",
        "ingredients.heading": "材料リスト",
        "ingredients.subhead": "メニューや献立で使い回せるパントリーを整えましょう。",
        "ingredients.name": "材料名",
        "ingredients.unit": "単位",
        "ingredients.create": "材料を追加",
        "ingredients.delete": "削除",
        "ingredients.deleteBlocked": "メニューで使われているため削除できません",
        "ingredients.empty": "まだ材料がありません",
        "data.heading": "データ",
        "data.export": "データを書き出す",
        "data.import": "データを取り込む",
        "data.description": "世帯の設定やメニューをJSONでバックアップし、必要なときに復元できます。",
        "data.file": "JSONファイルを選択",
        "data.importSuccess": "データを取り込みました",
        "data.importError": "ファイル形式が正しくありません",
        "help.hero": "たのしいガイド",
        "help.cta.register": "新規登録",
        "help.cta.login": "ログイン",
        "help.ribbon.tasks": "タスクとポイント",
        "help.ribbon.meals": "献立と材料",
        "help.ribbon.data": "バックアップ",
        "help.quickstart.title": "かんたん3ステップ",
        "help.quickstart.invite": "参加コードをシェア",
        "help.quickstart.customize": "テーマをおそろいに",
        "help.quickstart.menus": "お気に入りメニューを登録",
        "help.quickstart.export": "データを書き出して安心",
        "help.sections.tasks": "テンプレートで家事を作り、受注・承認でポイントを回します。",
        "help.sections.rewards": "ポイントでごほうびを申請し、承認してあげましょう。",
        "help.sections.meals": "料理タイプやセットを活用して献立と材料合計をチェック。",
        "help.sections.data": "大きな変更前にエクスポートしておくと安心です。",
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

THEME_CHOICES = ["sakura", "mint", "creamsicle", "night"]
FONT_STACKS = {
    "modern": "'Inter', 'Noto Sans JP', system-ui, -apple-system, sans-serif",
    "serif": "'Noto Serif JP', 'Times New Roman', 'Hiragino Mincho Pro', serif",
    "rounded": "'Nunito', 'Noto Sans JP', 'Hiragino Maru Gothic Pro', 'Rounded Mplus 1c', sans-serif",
}
FONT_CHOICES = list(FONT_STACKS.keys())
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def get_strings(language: str) -> dict:
    base = UI_STRINGS.get("en", {})
    localized = UI_STRINGS.get(language, {})
    merged = base.copy()
    merged.update(localized)
    return merged


def get_language(request: Request, session: Session, user: Optional[User] = None) -> str:
    lang = request.session.get("language")
    household_lang = None
    if user:
        household = session.get(Household, user.household_id)
        if household:
            household_lang = household.language
            if not lang:
                lang = household_lang
    if lang not in UI_STRINGS:
        lang = household_lang if household_lang in UI_STRINGS else "ja"
    request.session["language"] = lang
    return lang


def get_theme(request: Request, session: Session, user: Optional[User] = None) -> str:
    theme = request.session.get("theme")
    household_theme = None
    if user:
        household = session.get(Household, user.household_id)
        if household:
            household_theme = household.theme
            if not theme:
                theme = household_theme
    if theme not in THEME_CHOICES:
        theme = household_theme if household_theme in THEME_CHOICES else THEME_CHOICES[0]
    request.session["theme"] = theme
    return theme


def get_font(request: Request, session: Session, user: Optional[User] = None) -> str:
    font = request.session.get("font")
    household_font = None
    if user:
        household = session.get(Household, user.household_id)
        if household:
            household_font = household.font
            if not font:
                font = household_font
    if font not in FONT_CHOICES:
        font = household_font if household_font in FONT_CHOICES else FONT_CHOICES[0]
    request.session["font"] = font
    return font


def translate_status(status: TaskStatus, language: str) -> str:
    return STATUS_LABELS.get(status.value, {}).get(language, status.value)


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


async def store_instruction_upload(file: Optional[UploadFile]) -> Optional[str]:
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".png"
    filename = f"instruction-{secrets.token_hex(8)}{ext}"
    path = os.path.join(uploads_dir, filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return f"/static/uploads/{filename}"


def build_context(
    request: Request, session: Session, user: Optional[User] = None, extra: Optional[dict] = None
) -> dict:
    language = get_language(request, session, user)
    theme = get_theme(request, session, user)
    font = get_font(request, session, user)
    context = {
        "request": request,
        "user": user,
        "language": language,
        "theme": theme,
        "font": font,
        "font_stack": FONT_STACKS.get(font, FONT_STACKS[FONT_CHOICES[0]]),
        "strings": get_strings(language),
        "theme_choices": THEME_CHOICES,
        "font_choices": FONT_CHOICES,
        "flash_messages": pop_flash(request),
        "translate_status": translate_status,
        "render_instructions": render_instructions,
    }
    if extra:
        context.update(extra)
    return context


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


def get_or_create_ingredient(
    session: Session, household_id: int, name: str, unit: Optional[str]
):
    ingredient = session.exec(
        select(Ingredient).where(
            Ingredient.household_id == household_id, Ingredient.name == name, Ingredient.unit == unit
        )
    ).first()
    if not ingredient:
        ingredient = Ingredient(household_id=household_id, name=name, unit=unit)
        session.add(ingredient)
        session.commit()
        session.refresh(ingredient)
    return ingredient


def get_menus_for_household(session: Session, household_id: int):
    return (
        session.exec(select(Menu).where(Menu.household_id == household_id).order_by(Menu.name)).all()
    )


def get_dish_types(session: Session, household_id: int):
    return session.exec(
        select(DishType).where(DishType.household_id == household_id).order_by(DishType.name)
    ).all()


def get_unit_options(session: Session, household_id: int):
    return session.exec(
        select(UnitOption)
        .where(UnitOption.household_id == household_id, UnitOption.active == True)  # noqa: E712
        .order_by(UnitOption.name)
    ).all()


def get_ingredients(session: Session, household_id: int):
    return session.exec(
        select(Ingredient)
        .where(Ingredient.household_id == household_id)
        .order_by(Ingredient.name)
    ).all()


def ingredient_usage_counts(session: Session, household_id: int) -> dict[int, int]:
    rows = session.exec(
        select(MenuIngredient.ingredient_id, func.count())
        .join(Menu, Menu.id == MenuIngredient.menu_id)
        .where(Menu.household_id == household_id)
        .group_by(MenuIngredient.ingredient_id)
    ).all()
    return {ing_id: count for ing_id, count in rows}


def get_task_categories(session: Session, household_id: int):
    return session.exec(
        select(TaskCategory)
        .where(TaskCategory.household_id == household_id)
        .order_by(TaskCategory.name)
    ).all()


def seed_household_dish_types(session: Session, household_id: int):
    existing = {d.name for d in get_dish_types(session, household_id)}
    defaults = [
        {"name": "Main", "description": "メイン"},
        {"name": "Soup", "description": "汁物"},
        {"name": "Side", "description": "副菜"},
        {"name": "Salad", "description": "サラダ"},
    ]
    for entry in defaults:
        if entry["name"] in existing:
            continue
        session.add(DishType(household_id=household_id, **entry))
    session.commit()


def seed_household_unit_options(session: Session, household_id: int):
    existing = {u.name for u in get_unit_options(session, household_id)}
    defaults = ["個", "杯", "本", "g", "kg", "ml", "L", "枚", "パック", "丁", "切れ", "玉", "片", "束"]
    for name in defaults:
        if name in existing:
            continue
        session.add(UnitOption(household_id=household_id, name=name, active=True))
    session.commit()


def seed_task_categories(session: Session, household_id: int):
    existing = {c.name for c in get_task_categories(session, household_id)}
    defaults = ["cleaning", "cooking", "laundry", "shopping", "other"]
    for name in defaults:
        if name in existing:
            continue
        session.add(TaskCategory(household_id=household_id, name=name))
    session.commit()


def seed_default_meal_sets(session: Session, household_id: int):
    seed_household_dish_types(session, household_id)
    seed_household_unit_options(session, household_id)
    existing_set = session.exec(
        select(MealSetTemplate).where(MealSetTemplate.household_id == household_id)
    ).first()
    if existing_set:
        return
    template = MealSetTemplate(household_id=household_id, name="Aセット", description="汁物1・メイン1・サイド2")
    session.add(template)
    session.commit()
    session.refresh(template)
    dish_type_map = {d.name: d for d in get_dish_types(session, household_id)}
    requirements = [
        ("Soup", 1),
        ("Main", 1),
        ("Side", 2),
    ]
    for name, count in requirements:
        dt = dish_type_map.get(name)
        if not dt:
            continue
        session.add(
            MealSetRequirement(
                meal_set_template_id=template.id, dish_type_id=dt.id, required_count=count
            )
        )
    session.commit()


def seed_default_menus(session: Session, household_id: int):
    seed_household_dish_types(session, household_id)
    existing = session.exec(select(Menu).where(Menu.household_id == household_id)).first()
    if existing:
        return
    dish_types = {d.name: d for d in get_dish_types(session, household_id)}
    unit_options = {u.name: u for u in get_unit_options(session, household_id)}
    samples = [
        {
            "name": "味噌汁",
            "description": "豆腐とわかめの味噌汁",
            "dish_type": "Soup",
            "ingredients": [("豆腐", 1, "丁"), ("味噌", 30, "g"), ("だし", 400, "ml")],
        },
        {
            "name": "焼き魚",
            "description": "塩鮭のグリル",
            "dish_type": "Main",
            "ingredients": [("鮭", 2, "切れ"), ("塩", 2, "g")],
        },
        {
            "name": "サラダ",
            "description": "グリーンサラダ",
            "dish_type": "Side",
            "ingredients": [("レタス", 0.5, "玉"), ("トマト", 1, "個"), ("ドレッシング", 20, "ml")],
        },
        {
            "name": "きんぴらごぼう",
            "description": "ごぼうと人参",
            "dish_type": "Side",
            "ingredients": [("ごぼう", 1, "本"), ("人参", 0.5, "本"), ("醤油", 15, "ml")],
        },
        {
            "name": "カレーライス",
            "description": "野菜たっぷりカレー",
            "dish_type": "Main",
            "ingredients": [("豚肉", 200, "g"), ("じゃがいも", 1, "個"), ("人参", 0.5, "本"), ("玉ねぎ", 0.5, "個"), ("カレールー", 1, "パック"), ("水", 400, "ml")],
        },
        {
            "name": "唐揚げ",
            "description": "にんにく醤油ベース",
            "dish_type": "Main",
            "ingredients": [("鶏もも肉", 300, "g"), ("醤油", 20, "ml"), ("にんにく", 1, "片"), ("片栗粉", 30, "g")],
        },
        {
            "name": "豚汁",
            "description": "根菜たっぷりの汁物",
            "dish_type": "Soup",
            "ingredients": [("豚肉", 100, "g"), ("大根", 0.25, "本"), ("人参", 0.5, "本"), ("味噌", 40, "g"), ("だし", 500, "ml")],
        },
        {
            "name": "ひじき煮",
            "description": "乾物の常備菜",
            "dish_type": "Side",
            "ingredients": [("ひじき", 20, "g"), ("人参", 0.25, "本"), ("油揚げ", 1, "枚"), ("醤油", 15, "ml")],
        },
        {
            "name": "ポテトサラダ",
            "description": "ゆで卵入り",
            "dish_type": "Salad",
            "ingredients": [("じゃがいも", 2, "個"), ("きゅうり", 0.5, "本"), ("マヨネーズ", 30, "g"), ("ゆで卵", 1, "個")],
        },
        {
            "name": "ほうれん草のおひたし",
            "description": "シンプルな副菜",
            "dish_type": "Side",
            "ingredients": [("ほうれん草", 1, "束"), ("醤油", 10, "ml"), ("かつお節", 1, "パック")],
        },
    ]
    for sample in samples:
        dish_type = dish_types.get(sample["dish_type"])
        menu = Menu(
            household_id=household_id,
            name=sample["name"],
            description=sample.get("description"),
            dish_type_id=dish_type.id if dish_type else None,
        )
        session.add(menu)
        session.commit()
        session.refresh(menu)
        for ing_name, qty, unit in sample["ingredients"]:
            unit_option = unit_options.get(unit)
            ingredient = get_or_create_ingredient(session, household_id, ing_name, unit)
            session.add(
                MenuIngredient(
                    menu_id=menu.id,
                    ingredient_id=ingredient.id,
                    quantity=float(qty),
                    unit_option_id=unit_option.id if unit_option else None,
                )
            )
        session.commit()


def ensure_meal_seed_data(session: Session, household_id: int):
    seed_household_dish_types(session, household_id)
    seed_household_unit_options(session, household_id)
    seed_default_meal_sets(session, household_id)
    seed_default_menus(session, household_id)


def ensure_household_defaults(session: Session, household_id: int):
    ensure_meal_seed_data(session, household_id)
    seed_task_categories(session, household_id)


def get_menu_ingredients_map(session: Session, menu_ids: list[int]):
    if not menu_ids:
        return {}
    rows = session.exec(
        select(
            MenuIngredient.menu_id,
            Ingredient.name,
            MenuIngredient.quantity,
            Ingredient.unit,
            UnitOption.name,
        )
        .join(Ingredient, Ingredient.id == MenuIngredient.ingredient_id)
        .join(UnitOption, UnitOption.id == MenuIngredient.unit_option_id, isouter=True)
        .where(MenuIngredient.menu_id.in_(menu_ids))
    ).all()
    mapping: dict[int, list[dict]] = {}
    for menu_id, name, qty, unit, unit_option in rows:
        mapping.setdefault(menu_id, []).append(
            {"name": name, "quantity": qty, "unit": unit_option or unit}
        )
    return mapping


def get_meal_set_templates(session: Session, household_id: int):
    return session.exec(
        select(MealSetTemplate).where(MealSetTemplate.household_id == household_id).order_by(MealSetTemplate.name)
    ).all()


def get_meal_set_requirements(session: Session, template_ids: list[int]):
    if not template_ids:
        return {}
    reqs = session.exec(
        select(MealSetRequirement)
        .where(MealSetRequirement.meal_set_template_id.in_(template_ids))
        .order_by(MealSetRequirement.id)
    ).all()
    grouped: dict[int, list[MealSetRequirement]] = {}
    for r in reqs:
        grouped.setdefault(r.meal_set_template_id, []).append(r)
    return grouped


def set_meal_set_requirements(session: Session, template_id: int, counts: dict[int, int]):
    existing = session.exec(
        select(MealSetRequirement).where(
            MealSetRequirement.meal_set_template_id == template_id
        )
    ).all()
    for req in existing:
        session.delete(req)
    session.commit()
    for dish_type_id, count in counts.items():
        if count and count > 0:
            session.add(
                MealSetRequirement(
                    meal_set_template_id=template_id,
                    dish_type_id=dish_type_id,
                    required_count=count,
                )
            )
    session.commit()


def ensure_meal_plan_days(session: Session, plan: MealPlan):
    existing = session.exec(
        select(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id)
    ).all()
    existing_dates = {d.day_date for d in existing}
    day = plan.start_date
    while day <= plan.end_date:
        if day not in existing_dates:
            session.add(MealPlanDay(meal_plan_id=plan.id, day_date=day))
        day += timedelta(days=1)
    session.commit()


def aggregate_meal_plan_ingredients(session: Session, plan: MealPlan):
    days = session.exec(
        select(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id)
    ).all()
    menu_ids: set[int] = set()
    for d in days:
        if d.lunch_menu_id:
            menu_ids.add(d.lunch_menu_id)
        if d.dinner_menu_id:
            menu_ids.add(d.dinner_menu_id)
    selection_menu_ids = {
        mid
        for mid in session.exec(
            select(MealPlanSelection.menu_id)
            .join(MealPlanDay, MealPlanDay.id == MealPlanSelection.meal_plan_day_id)
            .where(MealPlanDay.meal_plan_id == plan.id, MealPlanSelection.menu_id.is_not(None))
        ).all()
        if mid
    }
    menu_ids.update(selection_menu_ids)
    if not menu_ids:
        return []
    rows = session.exec(
        select(Ingredient.name, Ingredient.unit, func.sum(MenuIngredient.quantity))
        .join(MenuIngredient, MenuIngredient.ingredient_id == Ingredient.id)
        .join(Menu, Menu.id == MenuIngredient.menu_id)
        .where(Menu.id.in_(list(menu_ids)), Menu.household_id == plan.household_id)
        .group_by(Ingredient.name, Ingredient.unit)
    ).all()
    return [
        {"name": name, "unit": unit, "quantity": float(total or 0)}
        for name, unit, total in rows
    ]


def export_household_data(session: Session, household_id: int) -> dict:
    unit_options = get_unit_options(session, household_id)
    dish_types = get_dish_types(session, household_id)
    ingredients = get_ingredients(session, household_id)
    menus = get_menus_for_household(session, household_id)
    dish_type_lookup = {d.id: d.name for d in dish_types}
    menu_payload: list[dict] = []
    for menu in menus:
        ingredient_rows = session.exec(
            select(
                Ingredient.name,
                MenuIngredient.quantity,
                Ingredient.unit,
                UnitOption.name,
            )
            .join(MenuIngredient, MenuIngredient.ingredient_id == Ingredient.id)
            .join(UnitOption, UnitOption.id == MenuIngredient.unit_option_id, isouter=True)
            .where(MenuIngredient.menu_id == menu.id)
        ).all()
        menu_payload.append(
            {
                "name": menu.name,
                "description": menu.description,
                "dish_type": session.get(DishType, menu.dish_type_id).name
                if menu.dish_type_id
                else None,
                "ingredients": [
                    {
                        "name": name,
                        "quantity": float(qty or 0),
                        "unit": unit_opt or unit,
                    }
                    for name, qty, unit, unit_opt in ingredient_rows
                ],
            }
        )
    meal_sets = get_meal_set_templates(session, household_id)
    meal_set_requirements = get_meal_set_requirements(session, [s.id for s in meal_sets if s.id])
    task_templates = session.exec(
        select(TaskTemplate).where(TaskTemplate.household_id == household_id)
    ).all()
    recurring_rules = session.exec(
        select(RecurringTaskRule).where(RecurringTaskRule.household_id == household_id)
    ).all()
    reward_templates = session.exec(
        select(RewardTemplate).where(RewardTemplate.household_id == household_id)
    ).all()
    categories = get_task_categories(session, household_id)
    return {
        "meta": {"version": 1, "exported_at": datetime.utcnow().isoformat()},
        "unit_options": [{"name": u.name, "active": u.active} for u in unit_options],
        "dish_types": [{"name": d.name, "description": d.description} for d in dish_types],
        "ingredients": [{"name": i.name, "unit": i.unit} for i in ingredients],
        "menus": menu_payload,
        "meal_sets": [
            {
                "name": s.name,
                "description": s.description,
                "requirements": [
                    {
                        "dish_type": dish_type_lookup.get(r.dish_type_id, r.dish_type_id),
                        "required_count": r.required_count,
                    }
                    for r in meal_set_requirements.get(s.id, [])
                ],
            }
            for s in meal_sets
        ],
        "task_categories": [c.name for c in categories],
        "task_templates": [
            {
                "title": t.title,
                "default_category": t.default_category,
                "default_points": t.default_points,
                "relative_due_days": t.relative_due_days,
                "memo": t.memo,
                "instructions": t.instructions,
            }
            for t in task_templates
        ],
        "recurring_rules": [
            {
                "template_title": session.get(TaskTemplate, r.task_template_id).title
                if r.task_template_id
                else None,
                "frequency": r.frequency.value,
                "next_run_date": r.next_run_date.isoformat(),
            }
            for r in recurring_rules
            if session.get(TaskTemplate, r.task_template_id)
        ],
        "reward_templates": [
            {"title": rt.title, "cost_points": rt.cost_points, "memo": rt.memo}
            for rt in reward_templates
        ],
    }


def import_household_data(session: Session, household_id: int, payload: dict):
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dict")
    unit_option_map: dict[str, UnitOption] = {}
    for entry in payload.get("unit_options", []):
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        existing = session.exec(
            select(UnitOption).where(UnitOption.household_id == household_id, UnitOption.name == name)
        ).first()
        if not existing:
            existing = UnitOption(household_id=household_id, name=name, active=bool(entry.get("active", True)))
        else:
            existing.active = bool(entry.get("active", True))
        session.add(existing)
        session.commit()
        session.refresh(existing)
        unit_option_map[name] = existing

    dish_type_map: dict[str, DishType] = {}
    for entry in payload.get("dish_types", []):
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        existing = session.exec(
            select(DishType).where(DishType.household_id == household_id, DishType.name == name)
        ).first()
        if not existing:
            existing = DishType(
                household_id=household_id, name=name, description=entry.get("description")
            )
        else:
            existing.description = entry.get("description")
        session.add(existing)
        session.commit()
        session.refresh(existing)
        dish_type_map[name] = existing

    ingredient_map: dict[tuple[str, Optional[str]], Ingredient] = {}
    for entry in payload.get("ingredients", []):
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        unit_val = entry.get("unit") or None
        ingredient = get_or_create_ingredient(session, household_id, name, unit_val)
        ingredient_map[(name, unit_val)] = ingredient

    for menu_entry in payload.get("menus", []):
        menu_name = str(menu_entry.get("name", "")).strip()
        if not menu_name:
            continue
        menu = session.exec(
            select(Menu).where(Menu.household_id == household_id, Menu.name == menu_name)
        ).first()
        dish_type_id = None
        dish_type_name = menu_entry.get("dish_type")
        if dish_type_name and dish_type_name in dish_type_map:
            dish_type_id = dish_type_map[dish_type_name].id
        if not menu:
            menu = Menu(
                household_id=household_id,
                name=menu_name,
                description=menu_entry.get("description"),
                dish_type_id=dish_type_id,
            )
            session.add(menu)
            session.commit()
            session.refresh(menu)
        else:
            menu.description = menu_entry.get("description")
            menu.dish_type_id = dish_type_id
            session.add(menu)
            session.commit()
        ingredient_names: list[str] = []
        ingredient_quantities: list[str] = []
        ingredient_units: list[str] = []
        for ing in menu_entry.get("ingredients", []):
            ing_name = str(ing.get("name", "")).strip()
            if not ing_name:
                continue
            ingredient_names.append(ing_name)
            ingredient_quantities.append(str(ing.get("quantity", 0)))
            ingredient_units.append(str(ing.get("unit", "")))
        save_menu_ingredients(
            session,
            menu,
            ingredient_names,
            ingredient_quantities,
            ingredient_units,
            household_id,
        )

    requirement_lookup: dict[int, list[dict]] = {}
    for set_entry in payload.get("meal_sets", []):
        name = str(set_entry.get("name", "")).strip()
        if not name:
            continue
        template = session.exec(
            select(MealSetTemplate).where(
                MealSetTemplate.household_id == household_id, MealSetTemplate.name == name
            )
        ).first()
        if not template:
            template = MealSetTemplate(
                household_id=household_id,
                name=name,
                description=set_entry.get("description"),
            )
            session.add(template)
            session.commit()
            session.refresh(template)
        else:
            template.description = set_entry.get("description")
            session.add(template)
            session.commit()
        requirement_lookup[template.id] = set_entry.get("requirements", [])

    for template_id, reqs in requirement_lookup.items():
        counts: dict[int, int] = {}
        for req in reqs:
            dish_key = req.get("dish_type")
            dish_type_id = None
            if isinstance(dish_key, str) and dish_key in dish_type_map:
                dish_type_id = dish_type_map[dish_key].id
            elif isinstance(dish_key, int):
                existing = session.get(DishType, dish_key)
                if existing and existing.household_id == household_id:
                    dish_type_id = existing.id
            if dish_type_id is None:
                continue
            try:
                count_val = int(req.get("required_count", 0))
            except (TypeError, ValueError):
                continue
            counts[dish_type_id] = count_val
        set_meal_set_requirements(session, template_id, counts)

    for name in payload.get("task_categories", []):
        cleaned = str(name).strip()
        if not cleaned:
            continue
        existing = session.exec(
            select(TaskCategory).where(TaskCategory.household_id == household_id, TaskCategory.name == cleaned)
        ).first()
        if not existing:
            session.add(TaskCategory(household_id=household_id, name=cleaned))
    session.commit()

    template_map: dict[str, TaskTemplate] = {}
    for entry in payload.get("task_templates", []):
        title = str(entry.get("title", "")).strip()
        if not title:
            continue
        template = session.exec(
            select(TaskTemplate).where(TaskTemplate.household_id == household_id, TaskTemplate.title == title)
        ).first()
        if not template:
            template = TaskTemplate(
                household_id=household_id,
                title=title,
                default_category=entry.get("default_category"),
                default_points=entry.get("default_points"),
                relative_due_days=entry.get("relative_due_days"),
                memo=entry.get("memo"),
                instructions=entry.get("instructions"),
            )
            session.add(template)
        else:
            template.default_category = entry.get("default_category")
            template.default_points = entry.get("default_points")
            template.relative_due_days = entry.get("relative_due_days")
            template.memo = entry.get("memo")
            template.instructions = entry.get("instructions")
            session.add(template)
        session.commit()
        session.refresh(template)
        template_map[title] = template

    for rule in payload.get("recurring_rules", []):
        title = rule.get("template_title")
        if not title or title not in template_map:
            continue
        try:
            next_date = date.fromisoformat(rule.get("next_run_date")) if rule.get("next_run_date") else date.today()
        except (TypeError, ValueError):
            next_date = date.today()
        freq_raw = rule.get("frequency", "weekly")
        try:
            freq_val = RecurringFrequency(freq_raw)
        except ValueError:
            freq_val = RecurringFrequency.weekly
        existing = session.exec(
            select(RecurringTaskRule).where(
                RecurringTaskRule.household_id == household_id,
                RecurringTaskRule.task_template_id == template_map[title].id,
                RecurringTaskRule.frequency == freq_val,
            )
        ).first()
        if not existing:
            existing = RecurringTaskRule(
                household_id=household_id,
                task_template_id=template_map[title].id,
                frequency=freq_val,
                next_run_date=next_date,
            )
        else:
            existing.frequency = freq_val
            existing.next_run_date = next_date
        session.add(existing)
    session.commit()

    for rt in payload.get("reward_templates", []):
        title = str(rt.get("title", "")).strip()
        if not title:
            continue
        existing = session.exec(
            select(RewardTemplate).where(RewardTemplate.household_id == household_id, RewardTemplate.title == title)
        ).first()
        if not existing:
            existing = RewardTemplate(
                household_id=household_id,
                title=title,
                cost_points=rt.get("cost_points", 0),
                memo=rt.get("memo"),
            )
        else:
            existing.cost_points = rt.get("cost_points", existing.cost_points)
            existing.memo = rt.get("memo")
        session.add(existing)
    session.commit()


def save_menu_ingredients(
    session: Session,
    menu: Menu,
    names: list[str],
    quantities: list[str],
    units: list[str],
    household_id: int,
):
    existing = session.exec(select(MenuIngredient).where(MenuIngredient.menu_id == menu.id)).all()
    for entry in existing:
        session.delete(entry)
    session.commit()
    unit_lookup = {u.name: u for u in get_unit_options(session, household_id)}
    for name, qty_raw, unit in zip(names, quantities, units):
        cleaned = name.strip()
        if not cleaned:
            continue
        try:
            qty = float(qty_raw)
        except (TypeError, ValueError):
            qty = 0
        unit_clean = unit.strip() if unit else ""
        unit_option = unit_lookup.get(unit_clean) if unit_clean else None
        ingredient = get_or_create_ingredient(
            session,
            household_id,
            cleaned,
            unit_option.name if unit_option else (unit_clean or None),
        )
        session.add(
            MenuIngredient(
                menu_id=menu.id,
                ingredient_id=ingredient.id,
                quantity=qty,
                unit_option_id=unit_option.id if unit_option else None,
            )
        )
    session.commit()


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


def seed_household_templates(session: Session, household_id: int):
    existing = session.exec(
        select(func.count(TaskTemplate.id)).where(TaskTemplate.household_id == household_id)
    ).one()
    if existing and existing[0]:
        return
    presets = [
        {
            "title": "毎日のリビング片付け / Living room tidy",
            "default_category": "cleaning",
            "default_points": 3,
            "relative_due_days": 0,
            "memo": "おもちゃ・雑誌を片付け、テーブルを拭く",
            "instructions": "* クッションを整える\n* テーブルを拭く\n* 床に落ちているものを回収",
        },
        {
            "title": "夕食後の皿洗い / Dishes after dinner",
            "default_category": "cooking",
            "default_points": 4,
            "relative_due_days": 0,
            "memo": "食洗機または手洗いで片付け",
            "instructions": "* 食器をまとめて予洗い\n* 食洗機に入れる or 手洗いする\n* シンク周りを拭く",
        },
        {
            "title": "ゴミ出し準備 / Trash day prep",
            "default_category": "cleaning",
            "default_points": 2,
            "relative_due_days": 0,
            "memo": "燃えるゴミをまとめて玄関へ",
            "instructions": "* 各部屋のゴミ箱を回収\n* 袋の口を固く結ぶ\n* 玄関に置いておく",
        },
        {
            "title": "洗濯＆干し / Laundry wash & hang",
            "default_category": "laundry",
            "default_points": 5,
            "relative_due_days": 0,
            "memo": "洗濯から干しまで担当",
            "instructions": "* 洗濯機を回す\n* 仕分けして干す\n* 物干しを整える",
        },
        {
            "title": "お風呂掃除 / Bathroom scrub",
            "default_category": "cleaning",
            "default_points": 4,
            "relative_due_days": 1,
            "memo": "浴槽と床の掃除",
            "instructions": "* 換気を回す\n* 浴槽ブラシでこする\n* 床と排水口を洗う",
        },
        {
            "title": "買い出しリストチェック / Grocery restock",
            "default_category": "shopping",
            "default_points": 3,
            "relative_due_days": 2,
            "memo": "冷蔵庫・パントリーを確認",
            "instructions": "* 残量を確認\n* なくなりそうなものをメモ\n* リストを家族と共有",
        },
    ]
    for preset in presets:
        session.add(TaskTemplate(household_id=household_id, **preset))
    session.commit()


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
            priority=3,
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


def run_meal_plan_tasks(session: Session, household_id: int, created_by_user_id: int):
    today = date.today()
    days = session.exec(
        select(MealPlanDay)
        .join(MealPlan, MealPlan.id == MealPlanDay.meal_plan_id)
        .where(MealPlan.household_id == household_id, MealPlanDay.day_date <= today)
    ).all()
    created_tasks: list[Task] = []
    menus_by_id = {m.id: m for m in get_menus_for_household(session, household_id) if m.id}
    set_templates = {s.id: s for s in get_meal_set_templates(session, household_id) if s.id}
    for day in days:
        for slot in (MealSlot.lunch, MealSlot.dinner):
            set_id = day.lunch_set_template_id if slot == MealSlot.lunch else day.dinner_set_template_id
            selections = session.exec(
                select(MealPlanSelection)
                .where(MealPlanSelection.meal_plan_day_id == day.id, MealPlanSelection.meal_slot == slot)
                .order_by(MealPlanSelection.position)
            ).all()
            if not set_id and not selections:
                continue
            existing = session.exec(
                select(Task).where(
                    Task.household_id == household_id,
                    Task.meal_plan_day_id == day.id,
                    Task.meal_slot == slot,
                )
            ).first()
            if existing:
                continue
            menu_names = []
            for sel in selections:
                menu = menus_by_id.get(sel.menu_id)
                if menu:
                    menu_names.append(menu.name)
            set_label = set_templates.get(set_id).name if set_id and set_id in set_templates else ""
            slot_label = "昼食" if slot == MealSlot.lunch else "夕食"
            title = f"{slot_label}準備: {set_label or '献立'}"
            if menu_names:
                title = f"{title} ({', '.join(menu_names)})"
            description = "\n".join(menu_names) if menu_names else ""
            order_num = next_order_number(session, household_id)
            task = Task(
                household_id=household_id,
                order_number=order_num,
                title=title,
                description=description or None,
                category="meal",
                due_date=day.day_date,
                proposed_points=2,
                priority=2,
                status=TaskStatus.open,
                created_by_user_id=created_by_user_id,
                meal_plan_day_id=day.id,
                meal_slot=slot,
            )
            session.add(task)
            created_tasks.append(task)
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
    run_meal_plan_tasks(session, user.household_id, user.id)
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
        request,
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


@app.get("/help", response_class=HTMLResponse)
def help_page(
    request: Request,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request,
        "help.html",
        build_context(request, session, user),
    )


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request, session: Session = Depends(get_session)):
    households = session.exec(select(Household)).all()
    return templates.TemplateResponse(
        request,
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
    new_join_code: Optional[str] = Form(None),
    existing_join_code: Optional[str] = Form(None),
    household_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
):
    new_join_code = new_join_code.strip() if new_join_code else None
    existing_join_code = existing_join_code.strip() if existing_join_code else None
    if create_household:
        if not household_name:
            flash(request, "Household name required", "error")
            return RedirectResponse("/register", status_code=303)
        code = (new_join_code or secrets.token_hex(3)).lower()
        household = Household(name=household_name, join_code=code)
        session.add(household)
        session.commit()
        session.refresh(household)
        seed_household_templates(session, household.id)
        ensure_household_defaults(session, household.id)
    else:
        if not household_id:
            flash(request, "Select a household", "error")
            return RedirectResponse("/register", status_code=303)
        household = session.get(Household, household_id)
        if not household:
            flash(request, "Household not found", "error")
            return RedirectResponse("/register", status_code=303)
        stored_code = household.join_code.lower().strip() if household.join_code else None
        provided_code = existing_join_code.lower().strip() if existing_join_code else None
        if stored_code and provided_code != stored_code:
            flash(request, "Invalid join code", "error")
            return RedirectResponse("/register", status_code=303)
        ensure_household_defaults(session, household.id)
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
    request.session["language"] = household.language if household.language in UI_STRINGS else "ja"
    request.session["theme"] = household.theme if household.theme in THEME_CHOICES else THEME_CHOICES[0]
    request.session["font"] = household.font if household.font in FONT_CHOICES else FONT_CHOICES[0]
    login_user(request, user)
    flash(request, "Registered and logged in")
    return RedirectResponse("/", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, session: Session = Depends(get_session)):
    households = session.exec(select(Household)).all()
    return templates.TemplateResponse(
        request,
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
    request.session["language"] = household.language if household.language in UI_STRINGS else "ja"
    request.session["theme"] = household.theme if household.theme in THEME_CHOICES else THEME_CHOICES[0]
    request.session["font"] = household.font if household.font in FONT_CHOICES else FONT_CHOICES[0]
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
    ensure_household_defaults(session, user.household_id)
    templates_list = session.exec(
        select(TaskTemplate).where(TaskTemplate.household_id == user.household_id)
    ).all()
    recurring_rules = session.exec(
        select(RecurringTaskRule).where(RecurringTaskRule.household_id == user.household_id)
    ).all()
    household_users = get_household_users(session, user.household_id)
    assignee_map = {u.id: u for u in household_users}
    household = session.get(Household, user.household_id)
    unit_options = get_unit_options(session, user.household_id)
    dish_types = get_dish_types(session, user.household_id)
    meal_sets = get_meal_set_templates(session, user.household_id)
    meal_set_requirements = get_meal_set_requirements(session, [m.id for m in meal_sets if m.id])
    categories = get_task_categories(session, user.household_id)
    return templates.TemplateResponse(
        request,
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
                "unit_options": unit_options,
                "dish_types": dish_types,
                "meal_sets": meal_sets,
                "meal_set_requirements": meal_set_requirements,
                "categories": categories,
            },
        ),
    )


@app.post("/settings/language")
async def update_language(
    request: Request,
    language: str = Form(...),
    theme: str = Form("sakura"),
    font: str = Form("modern"),
    household_name: Optional[str] = Form(None),
    join_code: Optional[str] = Form(None),
    regenerate_join_code: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    allowed_languages = set(UI_STRINGS.keys())
    language = language if language in allowed_languages else "ja"
    household = session.get(Household, user.household_id)
    if household:
        cleaned_name = household_name.strip() if household_name else None
        cleaned_code = join_code.strip().lower() if join_code else None
        household.name = cleaned_name or household.name
        if regenerate_join_code:
            household.join_code = secrets.token_hex(3)
        elif join_code is not None:
            household.join_code = cleaned_code or household.join_code
        household.language = language
        household.theme = theme if theme in THEME_CHOICES else household.theme
        household.font = font if font in FONT_CHOICES else household.font
        session.add(household)
        session.commit()
        session.refresh(household)
        language = household.language
        theme = household.theme
        font = household.font
    request.session["language"] = language
    request.session["theme"] = theme if theme in THEME_CHOICES else THEME_CHOICES[0]
    request.session["font"] = font if font in FONT_CHOICES else FONT_CHOICES[0]
    strings = get_strings(language)
    flash(request, strings.get("settings.updated", "Settings updated"))
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


@app.post("/settings/unit-options")
async def add_unit_option(
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_meal_seed_data(session, user.household_id)
    cleaned = name.strip()
    if not cleaned:
        flash(request, "Unit name required", "error")
        return RedirectResponse("/settings", status_code=303)
    existing = session.exec(
        select(UnitOption).where(UnitOption.household_id == user.household_id, UnitOption.name == cleaned)
    ).first()
    if existing:
        existing.active = True
        session.add(existing)
    else:
        session.add(UnitOption(household_id=user.household_id, name=cleaned, active=True))
    session.commit()
    flash(request, "Unit option saved")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/categories")
async def add_category(
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_household_defaults(session, user.household_id)
    cleaned = name.strip()
    if not cleaned:
        flash(request, "Category name required", "error")
        return RedirectResponse("/settings", status_code=303)
    existing = session.exec(
        select(TaskCategory).where(
            TaskCategory.household_id == user.household_id, TaskCategory.name == cleaned
        )
    ).first()
    if existing:
        flash(request, "Category already exists")
    else:
        session.add(TaskCategory(household_id=user.household_id, name=cleaned))
        session.commit()
        flash(request, "Category added")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/categories/{category_id}/edit")
async def edit_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    category = session.exec(
        select(TaskCategory).where(
            TaskCategory.id == category_id, TaskCategory.household_id == user.household_id
        )
    ).first()
    if not category:
        flash(request, "Category not found", "error")
        return RedirectResponse("/settings", status_code=303)
    cleaned = name.strip()
    if not cleaned:
        flash(request, "Category name required", "error")
        return RedirectResponse("/settings", status_code=303)
    category.name = cleaned
    session.add(category)
    session.commit()
    flash(request, "Category updated")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/categories/{category_id}/delete")
async def delete_category(
    request: Request,
    category_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    category = session.exec(
        select(TaskCategory).where(
            TaskCategory.id == category_id, TaskCategory.household_id == user.household_id
        )
    ).first()
    if not category:
        flash(request, "Category not found", "error")
        return RedirectResponse("/settings", status_code=303)
    session.delete(category)
    session.commit()
    flash(request, "Category deleted")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/dish-types")
async def add_dish_type(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_household_defaults(session, user.household_id)
    cleaned = name.strip()
    if not cleaned:
        flash(request, "Dish type required", "error")
        return RedirectResponse("/settings", status_code=303)
    existing = session.exec(
        select(DishType).where(DishType.household_id == user.household_id, DishType.name == cleaned)
    ).first()
    if existing:
        flash(request, "Dish type already exists")
    else:
        session.add(DishType(household_id=user.household_id, name=cleaned, description=description))
        session.commit()
        flash(request, "Dish type added")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/dish-types/{dish_type_id}/edit")
async def edit_dish_type(
    request: Request,
    dish_type_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    dish_type = session.exec(
        select(DishType).where(DishType.id == dish_type_id, DishType.household_id == user.household_id)
    ).first()
    if not dish_type:
        flash(request, "Dish type not found", "error")
        return RedirectResponse("/settings", status_code=303)
    cleaned = name.strip()
    if not cleaned:
        flash(request, "Dish type required", "error")
        return RedirectResponse("/settings", status_code=303)
    dish_type.name = cleaned
    dish_type.description = description
    session.add(dish_type)
    session.commit()
    flash(request, "Dish type updated")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/dish-types/{dish_type_id}/delete")
async def delete_dish_type(
    request: Request,
    dish_type_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    dish_type = session.exec(
        select(DishType).where(DishType.id == dish_type_id, DishType.household_id == user.household_id)
    ).first()
    if not dish_type:
        flash(request, "Dish type not found", "error")
        return RedirectResponse("/settings", status_code=303)
    session.delete(dish_type)
    session.commit()
    flash(request, "Dish type deleted")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/meal-sets")
async def add_meal_set(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_household_defaults(session, user.household_id)
    cleaned = name.strip()
    if not cleaned:
        flash(request, "Set name required", "error")
        return RedirectResponse("/settings", status_code=303)
    template = MealSetTemplate(household_id=user.household_id, name=cleaned, description=description)
    session.add(template)
    session.commit()
    session.refresh(template)
    form = await request.form()
    dish_types = get_dish_types(session, user.household_id)
    counts = {}
    for dt in dish_types:
        key = f"requirement_{dt.id}"
        if key in form and str(form[key]).strip():
            try:
                counts[dt.id] = int(form[key])
            except ValueError:
                continue
    set_meal_set_requirements(session, template.id, counts)
    flash(request, "Meal set added")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/meal-sets/{set_id}/edit")
async def edit_meal_set(
    request: Request,
    set_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    template = session.exec(
        select(MealSetTemplate).where(
            MealSetTemplate.id == set_id, MealSetTemplate.household_id == user.household_id
        )
    ).first()
    if not template:
        flash(request, "Set not found", "error")
        return RedirectResponse("/settings", status_code=303)
    cleaned = name.strip()
    if not cleaned:
        flash(request, "Set name required", "error")
        return RedirectResponse("/settings", status_code=303)
    template.name = cleaned
    template.description = description
    session.add(template)
    session.commit()
    form = await request.form()
    dish_types = get_dish_types(session, user.household_id)
    counts = {}
    for dt in dish_types:
        key = f"requirement_{dt.id}"
        if key in form and str(form[key]).strip():
            try:
                counts[dt.id] = int(form[key])
            except ValueError:
                continue
    set_meal_set_requirements(session, template.id, counts)
    flash(request, "Meal set updated")
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/meal-sets/{set_id}/delete")
async def delete_meal_set(
    request: Request,
    set_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    template = session.exec(
        select(MealSetTemplate).where(
            MealSetTemplate.id == set_id, MealSetTemplate.household_id == user.household_id
        )
    ).first()
    if not template:
        flash(request, "Set not found", "error")
        return RedirectResponse("/settings", status_code=303)
    session.delete(template)
    session.commit()
    flash(request, "Meal set deleted")
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


@app.get("/ingredients", response_class=HTMLResponse)
def list_ingredients(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_meal_seed_data(session, user.household_id)
    ingredients = get_ingredients(session, user.household_id)
    unit_options = get_unit_options(session, user.household_id)
    usage = ingredient_usage_counts(session, user.household_id)
    return templates.TemplateResponse(
        request,
        "ingredients.html",
        build_context(
            request,
            session,
            user,
            {
                "ingredients": ingredients,
                "unit_options": unit_options,
                "usage": usage,
            },
        ),
    )


@app.post("/ingredients")
async def create_ingredient(
    request: Request,
    name: str = Form(...),
    unit: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_meal_seed_data(session, user.household_id)
    cleaned = name.strip()
    if not cleaned:
        flash(request, "Name required", "error")
        return RedirectResponse("/ingredients", status_code=303)
    unit_val = unit.strip() if unit else None
    get_or_create_ingredient(session, user.household_id, cleaned, unit_val)
    flash(request, "Ingredient saved")
    return RedirectResponse("/ingredients", status_code=303)


@app.post("/ingredients/{ingredient_id}/delete")
async def delete_ingredient(
    request: Request,
    ingredient_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient or ingredient.household_id != user.household_id:
        flash(request, "Ingredient not found", "error")
        return RedirectResponse("/ingredients", status_code=303)
    usage = ingredient_usage_counts(session, user.household_id)
    if usage.get(ingredient.id, 0) > 0:
        flash(request, get_strings(get_language(request, session, user))["ingredients.deleteBlocked"], "error")
        return RedirectResponse("/ingredients", status_code=303)
    session.delete(ingredient)
    session.commit()
    flash(request, "Ingredient deleted")
    return RedirectResponse("/ingredients", status_code=303)


@app.get("/data/export")
def export_data(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_household_defaults(session, user.household_id)
    payload = export_household_data(session, user.household_id)
    filename = f"household-{user.household_id}-export.json"
    return JSONResponse(
        payload,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@app.post("/data/import")
async def import_data(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_household_defaults(session, user.household_id)
    strings = get_strings(get_language(request, session, user))
    try:
        content = await file.read()
        payload = json.loads(content.decode("utf-8"))
        import_household_data(session, user.household_id, payload)
    except Exception:
        flash(request, strings["data.importError"], "error")
        return RedirectResponse("/settings", status_code=303)
    flash(request, strings["data.importSuccess"])
    return RedirectResponse("/settings", status_code=303)


@app.get("/menus", response_class=HTMLResponse)
def list_menus(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_meal_seed_data(session, user.household_id)
    menus = get_menus_for_household(session, user.household_id)
    ingredients_map = get_menu_ingredients_map(session, [m.id for m in menus if m.id])
    dish_types = get_dish_types(session, user.household_id)
    unit_options = get_unit_options(session, user.household_id)
    ingredient_options = get_ingredients(session, user.household_id)
    return templates.TemplateResponse(
        request,
        "menus/list.html",
        build_context(
            request,
            session,
            user,
            {
                "menus": menus,
                "ingredients_map": ingredients_map,
                "dish_types": dish_types,
                "unit_options": unit_options,
                "ingredient_options": ingredient_options,
            },
        ),
    )


@app.post("/menus")
async def create_menu(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    dish_type_id: Optional[int] = Form(None),
    ingredient_names: list[str] = Form([]),
    ingredient_quantities: list[str] = Form([]),
    ingredient_units: list[str] = Form([]),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_meal_seed_data(session, user.household_id)
    cleaned_name = name.strip()
    if not cleaned_name:
        flash(request, "Menu name required", "error")
        return RedirectResponse("/menus", status_code=303)
    valid_dish_types = {d.id for d in get_dish_types(session, user.household_id) if d.id}
    dish_type_val = dish_type_id if dish_type_id in valid_dish_types else None
    menu = Menu(
        household_id=user.household_id,
        name=cleaned_name,
        description=description or None,
        dish_type_id=dish_type_val,
    )
    session.add(menu)
    session.commit()
    session.refresh(menu)
    save_menu_ingredients(
        session,
        menu,
        ingredient_names,
        ingredient_quantities,
        ingredient_units,
        user.household_id,
    )
    flash(request, "Menu created")
    return RedirectResponse("/menus", status_code=303)


@app.get("/menus/{menu_id}/edit", response_class=HTMLResponse)
def edit_menu_page(
    request: Request,
    menu_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_meal_seed_data(session, user.household_id)
    menu = session.get(Menu, menu_id)
    if not menu or menu.household_id != user.household_id:
        flash(request, "Menu not found", "error")
        return RedirectResponse("/menus", status_code=303)
    ingredients = get_menu_ingredients_map(session, [menu.id]).get(menu.id, [])
    dish_types = get_dish_types(session, user.household_id)
    unit_options = get_unit_options(session, user.household_id)
    ingredient_options = get_ingredients(session, user.household_id)
    return templates.TemplateResponse(
        request,
        "menus/edit.html",
        build_context(
            request,
            session,
            user,
            {
                "menu": menu,
                "ingredients": ingredients,
                "dish_types": dish_types,
                "unit_options": unit_options,
                "ingredient_options": ingredient_options,
            },
        ),
    )


@app.post("/menus/{menu_id}/edit")
async def update_menu(
    request: Request,
    menu_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    dish_type_id: Optional[int] = Form(None),
    ingredient_names: list[str] = Form([]),
    ingredient_quantities: list[str] = Form([]),
    ingredient_units: list[str] = Form([]),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    menu = session.get(Menu, menu_id)
    if not menu or menu.household_id != user.household_id:
        flash(request, "Menu not found", "error")
        return RedirectResponse("/menus", status_code=303)
    menu.name = name.strip() or menu.name
    menu.description = description or None
    valid_dish_types = {d.id for d in get_dish_types(session, user.household_id) if d.id}
    if dish_type_id in valid_dish_types:
        menu.dish_type_id = dish_type_id
    session.add(menu)
    session.commit()
    save_menu_ingredients(
        session,
        menu,
        ingredient_names,
        ingredient_quantities,
        ingredient_units,
        user.household_id,
    )
    flash(request, "Menu updated")
    return RedirectResponse("/menus", status_code=303)


@app.post("/menus/{menu_id}/delete")
async def delete_menu(
    request: Request,
    menu_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    menu = session.get(Menu, menu_id)
    if not menu or menu.household_id != user.household_id:
        flash(request, "Menu not found", "error")
        return RedirectResponse("/menus", status_code=303)
    for entry in session.exec(
        select(MenuIngredient).where(MenuIngredient.menu_id == menu.id)
    ).all():
        session.delete(entry)
    session.delete(menu)
    session.commit()
    flash(request, "Menu deleted")
    return RedirectResponse("/menus", status_code=303)


@app.get("/meal-plans", response_class=HTMLResponse)
def meal_plans_page(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_meal_seed_data(session, user.household_id)
    plans = session.exec(
        select(MealPlan).where(MealPlan.household_id == user.household_id).order_by(MealPlan.start_date)
    ).all()
    return templates.TemplateResponse(
        request,
        "meal_plans/list.html",
        build_context(
            request,
            session,
            user,
            {"plans": plans},
        ),
    )


@app.post("/meal-plans")
async def create_meal_plan(
    request: Request,
    name: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    if end_date < start_date:
        flash(request, "End date must be after start date", "error")
        return RedirectResponse("/meal-plans", status_code=303)
    plan = MealPlan(
        household_id=user.household_id,
        name=name.strip(),
        start_date=start_date,
        end_date=end_date,
        created_by_user_id=user.id,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    ensure_meal_plan_days(session, plan)
    flash(request, "Meal plan created")
    return RedirectResponse(f"/meal-plans/{plan.id}", status_code=303)


@app.get("/meal-plans/{plan_id}", response_class=HTMLResponse)
def meal_plan_detail(
    request: Request,
    plan_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    plan = session.get(MealPlan, plan_id)
    if not plan or plan.household_id != user.household_id:
        flash(request, "Meal plan not found", "error")
        return RedirectResponse("/meal-plans", status_code=303)
    ensure_meal_seed_data(session, user.household_id)
    ensure_meal_plan_days(session, plan)
    days = session.exec(
        select(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id).order_by(MealPlanDay.day_date)
    ).all()
    menus = get_menus_for_household(session, user.household_id)
    dish_types = get_dish_types(session, user.household_id)
    unit_options = get_unit_options(session, user.household_id)
    set_templates = get_meal_set_templates(session, user.household_id)
    requirement_map = get_meal_set_requirements(session, [s.id for s in set_templates if s.id])
    selection_rows = session.exec(
        select(MealPlanSelection)
        .join(MealPlanDay, MealPlanDay.id == MealPlanSelection.meal_plan_day_id)
        .where(MealPlanDay.meal_plan_id == plan.id)
    ).all()
    selections: dict[tuple[int, MealSlot, int], list[int]] = {}
    for sel in selection_rows:
        key = (sel.meal_plan_day_id, sel.meal_slot.value, sel.dish_type_id)
        selections.setdefault(key, []).append(sel.menu_id)
    return templates.TemplateResponse(
        request,
        "meal_plans/detail.html",
        build_context(
            request,
            session,
            user,
            {
                "plan": plan,
                "days": days,
                "menus": menus,
                "dish_types": dish_types,
                "unit_options": unit_options,
                "set_templates": set_templates,
                "requirement_map": requirement_map,
                "selections": selections,
            },
        ),
    )


@app.post("/meal-plans/{plan_id}")
async def update_meal_plan(
    request: Request,
    plan_id: int,
    day_dates: list[str] = Form(...),
    lunch_menu_ids: list[str] = Form([]),
    dinner_menu_ids: list[str] = Form([]),
    lunch_set_ids: list[str] = Form([]),
    dinner_set_ids: list[str] = Form([]),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    plan = session.get(MealPlan, plan_id)
    if not plan or plan.household_id != user.household_id:
        flash(request, "Meal plan not found", "error")
        return RedirectResponse("/meal-plans", status_code=303)
    ensure_meal_plan_days(session, plan)
    form_data = await request.form()
    days = session.exec(
        select(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id)
    ).all()
    day_lookup = {d.day_date: d for d in days}
    menus = get_menus_for_household(session, user.household_id)
    valid_menu_ids = {m.id for m in menus}
    menus_by_id = {m.id: m for m in menus if m.id}
    set_templates = {s.id: s for s in get_meal_set_templates(session, user.household_id) if s.id}
    requirement_map = get_meal_set_requirements(session, list(set_templates.keys()))
    for idx, (day_str, lunch_id, dinner_id) in enumerate(
        zip(day_dates, lunch_menu_ids, dinner_menu_ids)
    ):
        try:
            parsed_day = date.fromisoformat(str(day_str))
        except ValueError:
            continue
        d_obj = day_lookup.get(parsed_day)
        if not d_obj:
            continue
        # clear existing selections for the day so we can rewrite
        for old_sel in session.exec(
            select(MealPlanSelection).where(MealPlanSelection.meal_plan_day_id == d_obj.id)
        ).all():
            session.delete(old_sel)
        lunch_val = int(lunch_id) if lunch_id else None
        dinner_val = int(dinner_id) if dinner_id else None
        d_obj.lunch_menu_id = lunch_val if not lunch_val or lunch_val in valid_menu_ids else None
        d_obj.dinner_menu_id = dinner_val if not dinner_val or dinner_val in valid_menu_ids else None
        lunch_set_val = int(lunch_set_ids[idx]) if idx < len(lunch_set_ids) and lunch_set_ids[idx] else None
        dinner_set_val = int(dinner_set_ids[idx]) if idx < len(dinner_set_ids) and dinner_set_ids[idx] else None
        d_obj.lunch_set_template_id = lunch_set_val if lunch_set_val in set_templates else None
        d_obj.dinner_set_template_id = dinner_set_val if dinner_set_val in set_templates else None
        session.add(d_obj)
        # save structured selections per slot
        for slot, set_val in (
            (MealSlot.lunch, lunch_set_val),
            (MealSlot.dinner, dinner_set_val),
        ):
            if not set_val or set_val not in requirement_map:
                continue
            for req in requirement_map[set_val]:
                key = f"{slot.value}_selection-{idx}-{req.dish_type_id}"
                values = form_data.getlist(key)
                for position, raw_menu_id in enumerate(values[: req.required_count], start=1):
                    try:
                        menu_id_val = int(raw_menu_id)
                    except (TypeError, ValueError):
                        continue
                    menu_obj = menus_by_id.get(menu_id_val)
                    if not menu_obj or menu_obj.dish_type_id != req.dish_type_id:
                        continue
                    selection = MealPlanSelection(
                        meal_plan_day_id=d_obj.id,
                        meal_slot=slot,
                        dish_type_id=req.dish_type_id,
                        menu_id=menu_id_val,
                        position=position,
                    )
                    session.add(selection)
    session.commit()
    flash(request, "Meal plan updated")
    return RedirectResponse(f"/meal-plans/{plan.id}", status_code=303)


@app.get("/meal-plans/{plan_id}/ingredients", response_class=HTMLResponse)
def meal_plan_ingredients(
    request: Request,
    plan_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    plan = session.get(MealPlan, plan_id)
    if not plan or plan.household_id != user.household_id:
        flash(request, "Meal plan not found", "error")
        return RedirectResponse("/meal-plans", status_code=303)
    ensure_meal_plan_days(session, plan)
    totals = aggregate_meal_plan_ingredients(session, plan)
    return templates.TemplateResponse(
        request,
        "meal_plans/ingredients.html",
        build_context(
            request,
            session,
            user,
            {"plan": plan, "ingredients": totals},
        ),
    )


@app.get("/tasks", response_class=HTMLResponse)
def list_tasks(
    request: Request,
    status: Optional[str] = None,
    scope: str = "assigned",
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    run_recurring_rules(session, user.household_id, user.id)
    run_meal_plan_tasks(session, user.household_id, user.id)
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
        request,
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
    ensure_household_defaults(session, user.household_id)
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
        request,
        "task_form.html",
        build_context(
            request,
            session,
            user,
            {
                "template": template_data,
                "default_due_date": default_due_date,
                "assignees": get_household_users(session, user.household_id),
                "categories": get_task_categories(session, user.household_id),
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
    priority: int = Form(3),
    notes: Optional[str] = Form(None),
    assignee_user_id: Optional[int] = Form(None),
    task_template_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_household_defaults(session, user.household_id)
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
        priority=priority,
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
    ensure_household_defaults(session, user.household_id)
    task = get_task(session, user.household_id, task_id)
    return templates.TemplateResponse(
        request,
        "task_form.html",
        build_context(
            request,
            session,
            user,
            {
                "task": task,
                "default_due_date": task.due_date,
                "assignees": get_household_users(session, user.household_id),
                "categories": get_task_categories(session, user.household_id),
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
    priority: int = Form(3),
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
    task.priority = priority
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
        request,
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
        request,
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
    if actual_points is not None:
        task.actual_points = actual_points
    elif action in ["claim", "start"] and task.actual_points is None:
        task.actual_points = task.proposed_points
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
    ensure_household_defaults(session, user.household_id)
    selected_category = request.query_params.get("category") if request else None
    templates_query = select(TaskTemplate).where(TaskTemplate.household_id == user.household_id)
    if selected_category:
        templates_query = templates_query.where(TaskTemplate.default_category == selected_category)
    templates_list = session.exec(templates_query).all()
    return templates.TemplateResponse(
        request,
        "task_templates.html",
        build_context(
            request,
            session,
            user,
            {
                "templates": templates_list,
                "categories": get_task_categories(session, user.household_id),
                "selected_category": selected_category,
            },
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
    instruction_image_file: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_household_defaults(session, user.household_id)
    uploaded_url = await store_instruction_upload(instruction_image_file)
    final_instruction_url = instruction_image_url or uploaded_url
    final_instructions = instructions or ""
    if uploaded_url and uploaded_url not in final_instructions:
        final_instructions = (final_instructions + "\n" if final_instructions else "") + f"image::{uploaded_url}[]"
    template = TaskTemplate(
        household_id=user.household_id,
        title=title,
        default_category=default_category,
        default_points=default_points,
        relative_due_days=relative_due_days,
        memo=memo,
        instructions=final_instructions or None,
        instruction_image_url=final_instruction_url,
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
    instruction_image_file: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
):
    ensure_household_defaults(session, user.household_id)
    template = session.exec(
        select(TaskTemplate).where(
            TaskTemplate.id == template_id, TaskTemplate.household_id == user.household_id
        )
    ).first()
    if not template:
        flash(request, "Template not found", "error")
        return RedirectResponse("/templates/tasks", status_code=303)
    uploaded_url = await store_instruction_upload(instruction_image_file)
    template.title = title
    template.default_category = default_category
    template.default_points = default_points
    template.relative_due_days = relative_due_days
    template.memo = memo
    candidate_instructions = instructions or ""
    final_image_url = instruction_image_url or uploaded_url or template.instruction_image_url
    if uploaded_url and uploaded_url not in candidate_instructions:
        candidate_instructions = (candidate_instructions + "\n" if candidate_instructions else "") + f"image::{uploaded_url}[]"
    template.instructions = candidate_instructions or None
    template.instruction_image_url = final_image_url
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
        request,
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
        request,
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
