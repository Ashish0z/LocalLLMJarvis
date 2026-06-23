import re
from datetime import datetime, time, timedelta, timezone

# Map lowercase weekday names to Python weekday numbers (Monday=0)
WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Recurring time phrases that indicate a repeating schedule
_RECURRING_PHRASES: frozenset[str] = frozenset({
    "every day",
    "everyday",
    "daily",
    "every morning",
    "every evening",
    "every night",
    "every week",
    "weekly",
    "each day",
    "each morning",
    "each week",
})

_EVERY_WEEKDAY_RE = re.compile(
    r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
)

# Clock regex: require am/pm marker OR colon notation (HH:MM) to avoid false
# matches on bare ordinal/quantity numbers like "3 items" or "in 2 days".
_CLOCK_RE = re.compile(
    r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b|\b(\d{1,2})\s*(am|pm)\b",
    re.IGNORECASE,
)


def is_recurring(text: str) -> bool:
    """Return True when *text* contains a phrase that denotes a recurring schedule."""
    lowered = text.lower()
    if any(phrase in lowered for phrase in _RECURRING_PHRASES):
        return True
    return bool(_EVERY_WEEKDAY_RE.search(lowered))


def parse_when(text: str) -> datetime | None:
    """Parse a natural-language time expression and return a UTC datetime.

    Relative date keywords:
        tomorrow, next week, weekday names (Monday–Sunday, next Monday, …)

    Day-part keywords map to fixed hours (UTC):
        morning → 09:00, after lunch / afternoon → 14:00, evening → 18:00,
        tonight / night → 20:00

    Clock expressions require an am/pm suffix or colon notation (HH:MM) to
    prevent false matches on bare numbers.

    Same-day weekday rule: when the named weekday matches today's weekday, the
    returned date is always the *next* occurrence (7 days ahead).  This is
    intentional — if the time has already passed today the parser cannot know,
    so it defaults to the future.

    Returns None when no time hint is found in the text.
    """
    lowered = text.lower()
    now = datetime.now(timezone.utc)
    target_date = now.date()
    resolved_relative = False  # True when we've pinned a relative date

    if "tomorrow" in lowered:
        target_date = (now + timedelta(days=1)).date()
        resolved_relative = True
    elif "next week" in lowered:
        target_date = (now + timedelta(days=7)).date()
        resolved_relative = True
    else:
        # Weekday names: "on Monday", "next Thursday", plain "Friday", …
        weekday_match = re.search(
            r"\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            lowered,
        )
        if weekday_match:
            force_next_week = bool(weekday_match.group(1))  # explicit "next …"
            target_weekday = WEEKDAY_NAMES[weekday_match.group(2)]
            current_weekday = now.weekday()
            days_ahead = (target_weekday - current_weekday) % 7
            if days_ahead == 0:
                # Same weekday as today → always push to the next occurrence
                days_ahead = 7
            if force_next_week and days_ahead < 7:
                # "next Monday" when Monday is 3 days away → week after that
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
            resolved_relative = True

    target_time = time(hour=9)
    if "morning" in lowered:
        target_time = time(hour=9)
    elif "after lunch" in lowered or "afternoon" in lowered:
        target_time = time(hour=14)
    elif "evening" in lowered:
        target_time = time(hour=18)
    elif "tonight" in lowered or "night" in lowered:
        target_time = time(hour=20)

    clock_match = _CLOCK_RE.search(lowered)
    if clock_match:
        if clock_match.group(1) is not None:
            # HH:MM [am/pm]
            hour = int(clock_match.group(1))
            minute = int(clock_match.group(2))
            meridiem = clock_match.group(3)
        else:
            # H am/pm
            hour = int(clock_match.group(4))
            minute = 0
            meridiem = clock_match.group(5)
        meridiem_lc = meridiem.lower() if meridiem else None
        if meridiem_lc == "pm" and hour < 12:
            hour += 12
        if meridiem_lc == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            target_time = time(hour=hour, minute=minute)

    weekday_hint = any(name in lowered for name in WEEKDAY_NAMES)
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
    ) or weekday_hint or bool(clock_match)

    if not has_time_hint:
        return None

    parsed = datetime.combine(target_date, target_time, tzinfo=timezone.utc)
    if parsed < now and not resolved_relative:
        parsed = parsed + timedelta(days=1)
    return parsed

