import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.services.ollama import OllamaClient
from app.services.prioritization import score_task
from app.services.time_parser import is_recurring, parse_when

# ── intent signal sets ────────────────────────────────────────────────────────
_TASK_SIGNALS = frozenset(["add task", "add a task", "todo", "to-do", "to do"])
_REMINDER_SIGNALS = frozenset(["remind me", "reminder"])
_NUTRITION_VERBS = frozenset(["ate", "had", "having", "eating", "finished", "consumed"])
_NUTRITION_MARKERS = frozenset(["ate", "breakfast", "snack", "meal"])
_NUTRITION_MEAL_WORDS = frozenset(["lunch", "dinner"])

# Words that indicate the text is carrying important/urgent content
_URGENCY_WORDS = frozenset(["urgent", "important", "critical"])


class AssistantService:
    def __init__(self) -> None:
        self.ollama = OllamaClient()

    async def handle_message(self, db: Session, text: str, source: str) -> dict:
        cleaned = text.strip()
        actions: list[dict] = []

        db.add(models.ConversationMessage(role="user", content=cleaned))

        clarification = self._detect_ambiguous_intent(cleaned)
        if clarification:
            response = clarification
            db.add(models.ConversationMessage(role="assistant", content=response))
            db.commit()
            return {"response": response, "actions": actions}

        task = self._maybe_create_task(db, cleaned, source)
        if task:
            actions.append({"type": "task_created", "id": task.id, "title": task.title})

        reminder = self._maybe_create_reminder(db, cleaned, source)
        if reminder:
            actions.append({"type": "reminder_created", "id": reminder.id, "title": reminder.title})

        log = self._maybe_create_health_log(db, cleaned, source)
        if log:
            actions.append({"type": f"{log.kind}_logged", "id": log.id, "detail": log.value})

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

    # ── intent helpers ────────────────────────────────────────────────────────

    def _detect_ambiguous_intent(self, text: str) -> str | None:
        """Return a clarification question when the intent is ambiguous, else None."""
        lowered = text.lower()

        has_task = any(sig in lowered for sig in _TASK_SIGNALS)
        has_reminder = any(sig in lowered for sig in _REMINDER_SIGNALS)

        # Both task and reminder signals → ask which one is intended
        if has_task and has_reminder:
            return (
                "Did you want to add a task or set a reminder? "
                "Please rephrase as one of: 'Add task …' or 'Remind me to …'."
            )

        # Reminder signal present but no subject after stripping boilerplate
        if has_reminder:
            subject = re.sub(r"(please\s+)?(set\s+a\s+)?reminder\s*(to|for)?\s*", "", lowered, flags=re.IGNORECASE)
            subject = re.sub(r"(please\s+)?remind me\s*(to|that|about)?\s*", "", subject, flags=re.IGNORECASE)
            subject = subject.strip(" .")
            if not subject:
                return "What would you like to be reminded about?"

        return None

    def _maybe_create_task(self, db: Session, text: str, source: str) -> models.Task | None:
        lowered = text.lower()
        if not any(marker in lowered for marker in _TASK_SIGNALS):
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

        if self._is_duplicate_task(db, title):
            existing = db.scalars(
                select(models.Task).where(
                    models.Task.status == "pending",
                    models.Task.title == title,
                )
            ).first()
            return existing  # return the existing record without re-creating

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
        if not any(sig in lowered for sig in _REMINDER_SIGNALS):
            return None

        title = re.sub(r"^\s*(please\s+)?(set\s+a\s+)?reminder\s*(to|for)?\s*", "", text, flags=re.IGNORECASE)
        title = re.sub(r"^\s*(please\s+)?remind me\s*(to|that|about)?\s*", "", title, flags=re.IGNORECASE)
        title = title.strip(" .")
        if not title:
            title = text.strip()

        remind_at = parse_when(text)

        if self._is_duplicate_reminder(db, title, remind_at):
            existing = db.scalars(
                select(models.Reminder).where(
                    models.Reminder.status == "active",
                    models.Reminder.title == title,
                )
            ).first()
            return existing  # return the existing record without re-creating

        reminder = models.Reminder(
            title=title,
            remind_at=remind_at,
            recurrence="recurring" if is_recurring(text) else None,
            intensity="persistent" if any(word in lowered for word in _URGENCY_WORDS) else "standard",
            source=source,
        )
        db.add(reminder)
        db.flush()
        return reminder

    def _maybe_create_health_log(self, db: Session, text: str, source: str) -> models.HealthLog | None:
        lowered = text.lower()

        # Skip health-log extraction when the message is primarily a reminder or task command
        # to prevent false positives (e.g., "remind me about lunch" should not log a meal).
        if any(sig in lowered for sig in _REMINDER_SIGNALS):
            return None
        if any(sig in lowered for sig in _TASK_SIGNALS):
            return None

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

        # General nutrition: require a consumption verb alongside meal-specific words
        # to avoid triggering on time-of-day phrases like "after lunch" in a reminder.
        has_nutrition_marker = any(marker in lowered for marker in _NUTRITION_MARKERS)
        has_meal_with_verb = (
            any(word in lowered for word in _NUTRITION_MEAL_WORDS)
            and any(verb in lowered for verb in _NUTRITION_VERBS)
        )
        if has_nutrition_marker or has_meal_with_verb:
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
        return "Done - " + "; ".join(parts) + "."

    # ── idempotency helpers ───────────────────────────────────────────────────

    def _is_duplicate_task(self, db: Session, title: str) -> bool:
        """Return True if a pending task with the same normalised title already exists."""
        normalised = title.lower().strip()
        existing = db.scalars(
            select(models.Task).where(models.Task.status == "pending")
        ).all()
        return any(t.title.lower().strip() == normalised for t in existing)

    def _is_duplicate_reminder(self, db: Session, title: str, remind_at: datetime | None) -> bool:
        """Return True if an active reminder with the same normalised title already exists."""
        normalised = title.lower().strip()
        existing = db.scalars(
            select(models.Reminder).where(models.Reminder.status == "active")
        ).all()
        return any(r.title.lower().strip() == normalised for r in existing)

