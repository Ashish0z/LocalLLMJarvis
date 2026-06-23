import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import models
from app.services.ollama import OllamaClient
from app.services.prioritization import score_task
from app.services.time_parser import parse_when


class AssistantService:
    def __init__(self) -> None:
        self.ollama = OllamaClient()

    async def handle_message(self, db: Session, text: str, source: str) -> dict:
        cleaned = text.strip()
        actions: list[dict] = []

        db.add(models.ConversationMessage(role="user", content=cleaned))

        task = self._maybe_create_task(db, cleaned, source)
        if task:
            actions.append({"type": "task_created", "id": task.id, "title": task.title})

        reminder = self._maybe_create_reminder(db, cleaned, source)
        if reminder:
            actions.append({"type": "reminder_created", "id": reminder.id, "title": reminder.title})

        log = self._maybe_create_health_log(db, cleaned, source)
        if log:
            actions.append({"type": f"{log.kind}_logged", "id": log.id, "detail": log.value})

        habit = self._maybe_create_habit(db, cleaned, source)
        if habit:
            actions.append({"type": "habit_created", "id": habit.id, "title": habit.title})

        goal = self._maybe_create_goal(db, cleaned, source)
        if goal:
            actions.append({"type": "goal_created", "id": goal.id, "title": goal.title})

        if actions:
            response = self._confirmation(actions)
        else:
            fallback = await self.ollama.chat(cleaned)
            response = fallback or (
                "I heard you. I could not safely turn that into a task, reminder, or log yet, "
                "so I saved it in the conversation history."
            )

        db.add(models.ConversationMessage(role="assistant", content=response))
        db.commit()
        return {"response": response, "actions": actions}

    def _maybe_create_task(self, db: Session, text: str, source: str) -> models.Task | None:
        lowered = text.lower()
        if not any(marker in lowered for marker in ["add task", "add a task", "todo", "to-do", "to do"]):
            return None

        title = re.sub(
            r"^\s*(please\s+)?(add\s+(a\s+)?)?(task|todo|to-do|to do)(\s+to\s+)?",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip(" .")
        title = re.sub(r"^(to|for)\s+", "", title, flags=re.IGNORECASE).strip()
        if not title:
            title = text.strip()

        due_at = parse_when(text)
        priority_score, priority_reason = score_task(title, due_at)
        task = models.Task(
            title=title,
            due_at=due_at,
            priority_score=priority_score,
            priority_reason=priority_reason,
            source=source,
        )
        db.add(task)
        db.flush()
        return task

    def _maybe_create_reminder(self, db: Session, text: str, source: str) -> models.Reminder | None:
        lowered = text.lower()
        if "remind me" not in lowered and "reminder" not in lowered:
            return None

        title = re.sub(r"^\s*(please\s+)?(set\s+a\s+)?reminder\s*(to|for)?\s*", "", text, flags=re.IGNORECASE)
        title = re.sub(r"^\s*(please\s+)?remind me\s*(to|that|about)?\s*", "", title, flags=re.IGNORECASE)
        title = title.strip(" .")
        if not title:
            title = text.strip()

        reminder = models.Reminder(
            title=title,
            remind_at=parse_when(text),
            intensity="persistent" if any(word in lowered for word in ["urgent", "important", "critical"]) else "standard",
            source=source,
        )
        db.add(reminder)
        db.flush()
        return reminder

    def _maybe_create_health_log(self, db: Session, text: str, source: str) -> models.HealthLog | None:
        lowered = text.lower()

        if "water" in lowered and any(word in lowered for word in ["drank", "drink", "log", "had"]):
            amount = self._extract_amount(text)
            log = models.HealthLog(
                kind="water",
                value=text.strip(),
                amount=amount,
                unit="ml" if amount else None,
                logged_at=datetime.now(timezone.utc),
                source=source,
            )
            db.add(log)
            db.flush()
            return log

        nutrition_markers = ["ate", "breakfast", "lunch", "dinner", "snack", "meal"]
        if any(marker in lowered for marker in nutrition_markers):
            log = models.HealthLog(
                kind="nutrition",
                value=text.strip(),
                logged_at=datetime.now(timezone.utc),
                source=source,
            )
            db.add(log)
            db.flush()
            return log

        return None

    def _extract_amount(self, text: str) -> int | None:
        match = re.search(r"\b(\d{2,4})\s*(ml|milliliters?|litres?|liters?|l)\b", text, flags=re.IGNORECASE)
        if not match:
            return None
        amount = int(match.group(1))
        unit = match.group(2).lower()
        if unit in {"l", "liter", "liters", "litre", "litres"}:
            amount *= 1000
        return amount

    def _maybe_create_habit(self, db: Session, text: str, source: str) -> models.Habit | None:
        lowered = text.lower()
        habit_markers = ["habit to", "build a habit", "build the habit", "break the habit", "stop the habit", "track habit", "new habit"]
        if not any(marker in lowered for marker in habit_markers):
            return None

        mode = "remove" if any(w in lowered for w in ["break", "stop", "quit", "remove"]) else "build"

        title = re.sub(
            r"^\s*(i want to\s+)?(build|break|stop|quit|remove|track)(\s+(a|the))?\s+habit(\s+(to|of|for))?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip(" .")
        if not title:
            title = text.strip()

        habit = models.Habit(
            title=title,
            mode=mode,
            source=source,
        )
        db.add(habit)
        db.flush()
        return habit

    def _maybe_create_goal(self, db: Session, text: str, source: str) -> models.Goal | None:
        lowered = text.lower()
        goal_markers = ["my goal is", "set a goal", "new goal", "want to achieve", "goal to", "goal:"]
        if not any(marker in lowered for marker in goal_markers):
            return None

        title = re.sub(
            r"^\s*(my\s+)?goal(\s+is)?(\s+to)?\s*[:\-]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        title = re.sub(r"^\s*(set\s+a\s+|new\s+)?goal\s*(to|for|:)?\s*", "", title, flags=re.IGNORECASE)
        title = re.sub(r"^\s*(i\s+)?(want\s+to\s+achieve|want\s+to)\s*", "", title, flags=re.IGNORECASE)
        title = title.strip(" .")
        if not title:
            title = text.strip()

        goal = models.Goal(
            title=title,
            target_date=parse_when(text),
            source=source,
        )
        db.add(goal)
        db.flush()
        return goal

    def _confirmation(self, actions: list[dict]) -> str:
        parts: list[str] = []
        for action in actions:
            if action["type"] == "task_created":
                parts.append(f"added task: {action['title']}")
            elif action["type"] == "reminder_created":
                parts.append(f"set reminder: {action['title']}")
            elif action["type"] == "water_logged":
                parts.append("logged water")
            elif action["type"] == "nutrition_logged":
                parts.append("logged meal")
            elif action["type"] == "habit_created":
                parts.append(f"created habit: {action['title']}")
            elif action["type"] == "goal_created":
                parts.append(f"created goal: {action['title']}")
        return "Done - " + "; ".join(parts) + "."

