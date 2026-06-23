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


class HabitCreate(BaseModel):
    title: str = Field(min_length=1, max_length=280)
    mode: Literal["build", "remove"] = "build"
    description: str | None = None
    cue: str | None = None
    frequency: Literal["daily", "weekly"] = "daily"
    coaching_tone: Literal["supportive", "neutral", "strict"] = "supportive"
    source: str = "manual"


class HabitUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=280)
    description: str | None = None
    cue: str | None = None
    frequency: Literal["daily", "weekly"] | None = None
    coaching_tone: Literal["supportive", "neutral", "strict"] | None = None
    status: Literal["active", "paused", "archived"] | None = None


class HabitRead(BaseModel):
    id: str
    title: str
    mode: str
    description: str | None
    cue: str | None
    frequency: str
    coaching_tone: str
    status: str
    current_streak: int
    longest_streak: int
    relapse_count: int
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HabitCheckInCreate(BaseModel):
    outcome: Literal["complete", "skip", "relapse"]
    notes: str | None = None
    checked_at: datetime | None = None


class HabitCheckInRead(BaseModel):
    id: str
    habit_id: str
    outcome: str
    notes: str | None
    checked_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=280)
    description: str | None = None
    target_date: datetime | None = None
    source: str = "manual"


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=280)
    description: str | None = None
    target_date: datetime | None = None
    status: Literal["active", "completed", "cancelled", "paused"] | None = None
    current_phase: str | None = None


class GoalRead(BaseModel):
    id: str
    title: str
    description: str | None
    target_date: datetime | None
    status: str
    current_phase: str | None
    baseline_data: str | None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalInterviewCreate(BaseModel):
    current_level: str | None = None
    available_time: str | None = None
    constraints: str | None = None
    motivation_style: str | None = None
    extra_notes: str | None = None


class GoalCheckInCreate(BaseModel):
    notes: str | None = None
    adherence_rating: int | None = Field(default=None, ge=1, le=5)


class GoalCheckInRead(BaseModel):
    id: str
    goal_id: str
    notes: str | None
    adherence_rating: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
