from datetime import datetime, date, time
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TaskStatus(str, Enum):
    open = "open"  # 発注中
    assigned = "assigned"  # 受注済み
    in_progress = "in_progress"  # 作業中
    completed = "completed"  # 完了報告
    approved = "approved"  # 完了承認
    cancelled = "cancelled"


class RewardStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PointTransactionType(str, Enum):
    earn = "earn"
    spend = "spend"
    adjust = "adjust"


class Household(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    join_code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    language: str = Field(default="en")
    theme: str = Field(default="sakura")

    users: list["User"] = Relationship(back_populates="household")


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="household.id")
    email: str
    display_name: str
    hashed_password: str
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    household: Household = Relationship(back_populates="users")


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="household.id")
    order_number: int
    title: str
    description: Optional[str] = None
    category: str
    due_date: date
    due_time: Optional[time] = None
    proposed_points: int
    actual_points: Optional[int] = None
    priority: Priority = Field(default=Priority.medium)
    status: TaskStatus = Field(default=TaskStatus.open)
    created_by_user_id: int = Field(foreign_key="user.id")
    assignee_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    task_template_id: Optional[int] = Field(default=None, foreign_key="tasktemplate.id")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="household.id")
    title: str
    default_category: Optional[str] = None
    default_points: Optional[int] = None
    relative_due_days: Optional[int] = None
    memo: Optional[str] = None
    instructions: Optional[str] = None
    instruction_image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecurringFrequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class RecurringTaskRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="household.id")
    task_template_id: int = Field(foreign_key="tasktemplate.id")
    assignee_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    frequency: RecurringFrequency = Field(default=RecurringFrequency.weekly)
    next_run_date: date = Field(default_factory=date.today)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RewardTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="household.id")
    title: str
    cost_points: int
    memo: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RewardUse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="household.id")
    user_id: int = Field(foreign_key="user.id")
    reward_template_id: Optional[int] = Field(default=None, foreign_key="rewardtemplate.id")
    title: str
    cost_points: int
    status: RewardStatus = Field(default=RewardStatus.pending)
    approved_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    note: Optional[str] = None


class PointTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="household.id")
    user_id: int = Field(foreign_key="user.id")
    amount: int
    transaction_type: PointTransactionType
    description: Optional[str] = None
    related_task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    related_reward_use_id: Optional[int] = Field(default=None, foreign_key="rewarduse.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "Household",
    "User",
    "Task", 
    "TaskTemplate", 
    "RewardTemplate", 
    "RewardUse", 
    "PointTransaction", 
    "Priority", 
    "TaskStatus", 
    "RewardStatus", 
    "PointTransactionType", 
    "RecurringTaskRule", 
    "RecurringFrequency", 
]
