import re
from datetime import datetime, time, timedelta, timezone


def parse_when(text: str) -> datetime | None:
    lowered = text.lower()
    now = datetime.now(timezone.utc)
    target_date = now.date()

    if "tomorrow" in lowered:
        target_date = (now + timedelta(days=1)).date()
    elif "next week" in lowered:
        target_date = (now + timedelta(days=7)).date()

    target_time = time(hour=9)
    if "morning" in lowered:
        target_time = time(hour=9)
    elif "after lunch" in lowered or "afternoon" in lowered:
        target_time = time(hour=14)
    elif "evening" in lowered:
        target_time = time(hour=18)
    elif "tonight" in lowered or "night" in lowered:
        target_time = time(hour=20)

    clock_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lowered)
    if clock_match:
        hour = int(clock_match.group(1))
        minute = int(clock_match.group(2) or 0)
        meridiem = clock_match.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            target_time = time(hour=hour, minute=minute)

    has_time_hint = any(
        phrase in lowered
        for phrase in [
            "today",
            "tomorrow",
            "next week",
            "morning",
            "afternoon",
            "evening",
            "tonight",
            "night",
            "after lunch",
        ]
    ) or bool(clock_match)

    if not has_time_hint:
        return None

    parsed = datetime.combine(target_date, target_time, tzinfo=timezone.utc)
    if parsed < now and "tomorrow" not in lowered and "next week" not in lowered:
        parsed = parsed + timedelta(days=1)
    return parsed

