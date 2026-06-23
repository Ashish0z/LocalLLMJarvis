from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=280)
    notes: str | None = None
    due_at: datetime | None = None
    source: str = "manual"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=280)
    notes: str | None = None
    due_at: datetime | None = None
    status: Literal["pending", "done", "archived"] | None = None


class TaskRead(BaseModel):
    id: str
    title: str
    notes: str | None
    status: str
    due_at: datetime | None
    priority_score: float
    priority_reason: str | None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=280)
    remind_at: datetime | None = None
    intensity: Literal["gentle", "standard", "persistent"] = "standard"
    source: str = "manual"


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=280)
    remind_at: datetime | None = None
    status: Literal["active", "done", "snoozed", "cancelled"] | None = None
    intensity: Literal["gentle", "standard", "persistent"] | None = None


class ReminderRead(BaseModel):
    id: str
    title: str
    remind_at: datetime | None
    status: str
    intensity: str
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthLogCreate(BaseModel):
    kind: Literal["water", "nutrition", "sleep", "mood", "exercise"]
    value: str = Field(min_length=1)
    amount: int | None = None
    unit: str | None = None
    logged_at: datetime | None = None
    source: str = "manual"


class WaterLogCreate(BaseModel):
    value: str = "water"
    amount: int | None = Field(default=250, ge=1)
    unit: str = "ml"
    logged_at: datetime | None = None
    source: str = "manual"


class NutritionLogCreate(BaseModel):
    value: str = Field(min_length=1)
    logged_at: datetime | None = None
    source: str = "manual"


class HealthLogRead(BaseModel):
    id: str
    kind: str
    value: str
    amount: int | None
    unit: str | None
    logged_at: datetime
    source: str

    model_config = ConfigDict(from_attributes=True)


class MemoryCreate(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1)
    source: str = "manual"


class MemoryUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=64)
    content: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class MemoryRead(BaseModel):
    id: str
    category: str
    content: str
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssistantMessageCreate(BaseModel):
    text: str = Field(min_length=1)
    source: Literal["chat", "web", "android"] = "chat"


class AssistantActionRead(BaseModel):
    type: str
    id: str | None = None
    title: str | None = None
    detail: str | None = None


class AssistantMessageRead(BaseModel):
    response: str
    actions: list[AssistantActionRead]


class TodayRead(BaseModel):
    generated_at: datetime
    top_priorities: list[TaskRead]
    upcoming_reminders: list[ReminderRead]
    recent_logs: list[HealthLogRead]
    suggestion: str


class DocumentRead(BaseModel):
    id: str
    filename: str
    content_type: str | None
    summary: str | None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailRead(DocumentRead):
    text: str


class DocumentAskCreate(BaseModel):
    question: str = Field(min_length=1)


class DocumentAskRead(BaseModel):
    answer: str
    document_id: str
    context_chunks: list[str]


# ---------- Projects ----------

class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=280)
    description: str | None = None
    sequence_order: int = Field(default=0, ge=0)
    due_at: datetime | None = None


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=280)
    description: str | None = None
    sequence_order: int | None = Field(default=None, ge=0)
    status: Literal["planned", "active", "blocked", "done"] | None = None
    due_at: datetime | None = None


class MilestoneRead(BaseModel):
    id: str
    project_id: str
    title: str
    description: str | None
    sequence_order: int
    status: str
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=280)
    objective: str = Field(min_length=1)
    constraints: str | None = None
    deadline: datetime | None = None
    milestones: list[MilestoneCreate] = []


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=280)
    objective: str | None = Field(default=None, min_length=1)
    constraints: str | None = None
    deadline: datetime | None = None
    status: Literal["planned", "active", "blocked", "done"] | None = None


class ProjectRead(BaseModel):
    id: str
    title: str
    objective: str
    constraints: str | None
    deadline: datetime | None
    status: str
    replan_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailRead(ProjectRead):
    milestones: list[MilestoneRead]


class ProjectReplanCreate(BaseModel):
    reason: str = Field(min_length=1)
    updated_milestones: list[MilestoneCreate] | None = None
