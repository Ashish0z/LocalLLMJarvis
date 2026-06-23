"""Tests for NLP enhancement and extraction reliability (issue #6)."""

import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.main import app
from app import models
from app.database import SessionLocal
from app.services.time_parser import is_recurring, parse_when

HEADERS = {"X-API-Key": "test-key"}


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def fresh_db():
    """Delete all tasks, reminders, and health-logs before a test that requires clean state."""
    db = SessionLocal()
    try:
        db.execute(delete(models.Task))
        db.execute(delete(models.Reminder))
        db.execute(delete(models.HealthLog))
        db.commit()
    finally:
        db.close()
    yield


# ── time_parser: weekday parsing ─────────────────────────────────────────────

class TestWeekdayParsing:
    def test_plain_weekday_returns_future_date(self) -> None:
        result = parse_when("Remind me on Friday")
        assert result is not None
        assert result > datetime.now(timezone.utc)
        assert result.weekday() == 4  # Friday

    def test_next_weekday_returns_future_date(self) -> None:
        result = parse_when("Schedule meeting for next Monday")
        assert result is not None
        assert result > datetime.now(timezone.utc)
        assert result.weekday() == 0  # Monday

    def test_weekday_with_time_uses_specified_hour(self) -> None:
        result = parse_when("Call dentist on Tuesday at 3pm")
        assert result is not None
        assert result.weekday() == 1  # Tuesday
        assert result.hour == 15

    def test_weekday_with_morning_uses_9am(self) -> None:
        result = parse_when("team sync on Wednesday morning")
        assert result is not None
        assert result.weekday() == 2  # Wednesday
        assert result.hour == 9

    def test_weekday_result_is_in_future(self) -> None:
        """Any weekday result must be strictly in the future."""
        for phrase in [
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ]:
            result = parse_when(f"reminder on {phrase}")
            assert result is not None, f"parse_when returned None for '{phrase}'"
            assert result > datetime.now(timezone.utc), f"Result for '{phrase}' is not in future"


# ── time_parser: recurring phrases ───────────────────────────────────────────

class TestRecurringPhrases:
    def test_every_day_is_recurring(self) -> None:
        assert is_recurring("wake up every day at 7am") is True

    def test_daily_is_recurring(self) -> None:
        assert is_recurring("take medication daily") is True

    def test_every_morning_is_recurring(self) -> None:
        assert is_recurring("check email every morning") is True

    def test_weekly_is_recurring(self) -> None:
        assert is_recurring("team standup weekly") is True

    def test_every_monday_is_recurring(self) -> None:
        assert is_recurring("submit report every Monday") is True

    def test_single_occurrence_is_not_recurring(self) -> None:
        assert is_recurring("call mom tomorrow") is False

    def test_plain_reminder_is_not_recurring(self) -> None:
        assert is_recurring("remind me to buy milk") is False


# ── time_parser: clock regex false-positive fix ───────────────────────────────

class TestClockRegexFalsePositives:
    def test_bare_number_does_not_parse(self) -> None:
        """'3 items' should not produce a time hint."""
        result = parse_when("I have 3 items on my shopping list")
        assert result is None

    def test_quantity_in_sentence_does_not_parse(self) -> None:
        result = parse_when("finished 5 tasks today")
        # "today" gives a time hint, but the bare "5" must not be treated as a clock
        assert result is not None
        assert result.hour == 9  # falls through to default morning time

    def test_explicit_ampm_parses(self) -> None:
        result = parse_when("meeting at 3pm")
        assert result is not None
        assert result.hour == 15

    def test_colon_notation_parses(self) -> None:
        result = parse_when("alarm at 07:30")
        assert result is not None
        assert result.hour == 7
        assert result.minute == 30


# ── assistant: idempotency ────────────────────────────────────────────────────

class TestIdempotency:
    def test_duplicate_reminder_not_created_twice(self, fresh_db: None) -> None:
        with TestClient(app) as client:
            first = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "Remind me to call the bank tomorrow morning", "source": "chat"},
            )
            second = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "Remind me to call the bank tomorrow morning", "source": "chat"},
            )

        assert first.status_code == 200
        assert second.status_code == 200
        # Both responses should reference a reminder action
        first_actions = [a["type"] for a in first.json()["actions"]]
        second_actions = [a["type"] for a in second.json()["actions"]]
        assert "reminder_created" in first_actions
        assert "reminder_created" in second_actions
        # Both responses must reference the same reminder ID (no duplicate)
        first_id = next(a["id"] for a in first.json()["actions"] if a["type"] == "reminder_created")
        second_id = next(a["id"] for a in second.json()["actions"] if a["type"] == "reminder_created")
        assert first_id == second_id, "Duplicate reminder was created instead of returning existing one"

    def test_duplicate_task_not_created_twice(self, fresh_db: None) -> None:
        with TestClient(app) as client:
            first = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "Add task to review quarterly report", "source": "chat"},
            )
            second = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "Add task to review quarterly report", "source": "chat"},
            )

        assert first.status_code == 200
        assert second.status_code == 200
        first_id = next(a["id"] for a in first.json()["actions"] if a["type"] == "task_created")
        second_id = next(a["id"] for a in second.json()["actions"] if a["type"] == "task_created")
        assert first_id == second_id, "Duplicate task was created instead of returning existing one"


# ── assistant: false positive reduction ──────────────────────────────────────

class TestFalsePositiveReduction:
    def test_reminder_about_lunch_does_not_log_meal(self) -> None:
        """'remind me about lunch' should not create a nutrition health log."""
        with TestClient(app) as client:
            response = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "Remind me about my lunch meeting", "source": "chat"},
            )

        assert response.status_code == 200
        action_types = [a["type"] for a in response.json()["actions"]]
        assert "nutrition_logged" not in action_types

    def test_reminder_with_dinner_does_not_log_meal(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "Remind me to book a table for dinner tomorrow", "source": "chat"},
            )

        assert response.status_code == 200
        action_types = [a["type"] for a in response.json()["actions"]]
        assert "nutrition_logged" not in action_types

    def test_actual_meal_log_still_works(self) -> None:
        """'I had lunch' (no reminder signal) should still create a nutrition log."""
        with TestClient(app) as client:
            response = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "I had lunch – a big bowl of ramen", "source": "chat"},
            )

        assert response.status_code == 200
        action_types = [a["type"] for a in response.json()["actions"]]
        assert "nutrition_logged" in action_types


# ── assistant: clarification flow ────────────────────────────────────────────

class TestClarificationFlow:
    def test_bare_remind_me_asks_clarification(self) -> None:
        """'remind me' with no subject should ask what to remind about."""
        with TestClient(app) as client:
            response = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "remind me", "source": "chat"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["actions"] == []
        assert "what" in data["response"].lower() or "remind" in data["response"].lower()

    def test_both_task_and_reminder_signals_ask_clarification(self) -> None:
        """Input with both task and reminder signals should trigger clarification."""
        with TestClient(app) as client:
            response = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "Add task and remind me to submit the form", "source": "chat"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["actions"] == []
        assert "task" in data["response"].lower() or "reminder" in data["response"].lower()


# ── assistant: recurring reminder is flagged ─────────────────────────────────

class TestRecurringReminder:
    def test_recurring_reminder_sets_recurrence_field(self, fresh_db: None) -> None:
        with TestClient(app) as client:
            _ = client.post(
                "/assistant/message",
                headers=HEADERS,
                json={"text": "Remind me to take my vitamins every morning", "source": "chat"},
            )
            reminders = client.get("/reminders", headers=HEADERS)

        assert reminders.status_code == 200
        matches = [r for r in reminders.json() if "vitamins" in r["title"].lower()]
        assert matches, "Recurring reminder was not created"
        assert matches[0]["recurrence"] == "recurring"
