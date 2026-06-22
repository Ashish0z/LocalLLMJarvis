from datetime import datetime, timezone

IMPORTANT_WORDS = {"urgent", "important", "critical", "must", "deadline", "asap"}
LOW_WORDS = {"someday", "maybe", "optional", "whenever"}


def score_task(title: str, due_at: datetime | None) -> tuple[float, str]:
    score = 10.0
    reasons: list[str] = []
    lowered = title.lower()

    if any(word in lowered for word in IMPORTANT_WORDS):
        score += 35
        reasons.append("contains importance language")

    if any(word in lowered for word in LOW_WORDS):
        score -= 10
        reasons.append("contains low-urgency language")

    if due_at:
        now = datetime.now(timezone.utc)
        due = due_at if due_at.tzinfo else due_at.replace(tzinfo=timezone.utc)
        hours_until_due = (due - now).total_seconds() / 3600
        if hours_until_due <= 0:
            score += 45
            reasons.append("is overdue")
        elif hours_until_due <= 24:
            score += 30
            reasons.append("is due within 24 hours")
        elif hours_until_due <= 72:
            score += 20
            reasons.append("is due within 3 days")
        else:
            score += 5
            reasons.append("has a future due date")

    if not reasons:
        reasons.append("default priority until more context is available")

    return max(0.0, min(score, 100.0)), "; ".join(reasons)

