package com.localllmjarvis.app

import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

private val displayFormatter: DateTimeFormatter = DateTimeFormatter.ofPattern("EEE, MMM d • h:mm a z")

fun parseApiInstantOrNull(value: String): Instant? {
    return runCatching { OffsetDateTime.parse(value).toInstant() }
        .recoverCatching {
            LocalDateTime.parse(value).atZone(ZoneId.systemDefault()).toInstant()
        }
        .getOrNull()
}

fun formatApiDateTime(value: String?): String? {
    if (value.isNullOrBlank()) return null
    val instant = parseApiInstantOrNull(value) ?: return null
    return displayFormatter.format(instant.atZone(ZoneId.systemDefault()))
}

fun normalizeDateInputOrNull(value: String): String? {
    val cleaned = value.trim()
    if (cleaned.isBlank()) return null
    return runCatching { OffsetDateTime.parse(cleaned).toString() }
        .recoverCatching {
            LocalDateTime.parse(cleaned)
                .atZone(ZoneId.systemDefault())
                .toOffsetDateTime()
                .toString()
        }
        .getOrNull()
}

fun snoozeUntil(remindAt: String?, minutes: Long = 15): String {
    val baseInstant = remindAt?.let(::parseApiInstantOrNull) ?: Instant.now()
    return baseInstant.plusSeconds(minutes * 60).atOffset(ZoneOffset.UTC).toString()
}
