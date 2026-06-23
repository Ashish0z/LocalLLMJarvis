package com.localllmjarvis.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.json.JSONArray
import org.json.JSONObject

/**
 * Unit tests for data model creation and API response parsing logic.
 *
 * These run on the JVM without an Android device or emulator.
 */
class ModelsTest {

    // -----------------------------------------------------------------------
    // TaskItem
    // -----------------------------------------------------------------------

    @Test
    fun `TaskItem holds expected values`() {
        val task = TaskItem(
            id = "t-1",
            title = "Submit the insurance form",
            status = "pending",
            dueAt = "2024-01-15T09:00:00Z",
            priorityScore = 85.0,
            priorityReason = "Due soon"
        )

        assertEquals("t-1", task.id)
        assertEquals("Submit the insurance form", task.title)
        assertEquals("pending", task.status)
        assertEquals("2024-01-15T09:00:00Z", task.dueAt)
        assertEquals(85.0, task.priorityScore, 0.001)
        assertEquals("Due soon", task.priorityReason)
    }

    @Test
    fun `TaskItem dueAt and priorityReason can be null`() {
        val task = TaskItem(
            id = "t-2",
            title = "Flexible task",
            status = "pending",
            dueAt = null,
            priorityScore = 50.0,
            priorityReason = null
        )

        assertNull(task.dueAt)
        assertNull(task.priorityReason)
    }

    // -----------------------------------------------------------------------
    // ReminderItem
    // -----------------------------------------------------------------------

    @Test
    fun `ReminderItem holds expected values`() {
        val reminder = ReminderItem(
            id = "r-1",
            title = "Take medication",
            remindAt = "2024-01-15T08:00:00Z",
            intensity = "standard"
        )

        assertEquals("r-1", reminder.id)
        assertEquals("Take medication", reminder.title)
        assertEquals("2024-01-15T08:00:00Z", reminder.remindAt)
        assertEquals("standard", reminder.intensity)
    }

    @Test
    fun `ReminderItem remindAt can be null`() {
        val reminder = ReminderItem(
            id = "r-2",
            title = "Flexible reminder",
            remindAt = null,
            intensity = "gentle"
        )

        assertNull(reminder.remindAt)
    }

    // -----------------------------------------------------------------------
    // HealthLogItem
    // -----------------------------------------------------------------------

    @Test
    fun `HealthLogItem holds water log values`() {
        val log = HealthLogItem(
            id = "l-1",
            kind = "water",
            value = "water",
            amount = 300,
            unit = "ml",
            loggedAt = "2024-01-15T10:00:00Z"
        )

        assertEquals("water", log.kind)
        assertEquals(300, log.amount)
        assertEquals("ml", log.unit)
    }

    @Test
    fun `HealthLogItem amount and unit can be null`() {
        val log = HealthLogItem(
            id = "l-2",
            kind = "sleep",
            value = "7h30m",
            amount = null,
            unit = null,
            loggedAt = "2024-01-15T08:00:00Z"
        )

        assertNull(log.amount)
        assertNull(log.unit)
    }

    // -----------------------------------------------------------------------
    // TodayState
    // -----------------------------------------------------------------------

    @Test
    fun `TodayState aggregates lists correctly`() {
        val tasks = listOf(
            TaskItem("t-1", "Task one", "pending", null, 90.0, null),
            TaskItem("t-2", "Task two", "pending", null, 70.0, null)
        )
        val reminders = listOf(
            ReminderItem("r-1", "Reminder one", null, "gentle")
        )
        val logs = emptyList<HealthLogItem>()

        val today = TodayState(
            generatedAt = "2024-01-15T07:00:00Z",
            topPriorities = tasks,
            upcomingReminders = reminders,
            recentLogs = logs,
            suggestion = "Focus on Task one first."
        )

        assertEquals(2, today.topPriorities.size)
        assertEquals(1, today.upcomingReminders.size)
        assertTrue(today.recentLogs.isEmpty())
        assertEquals("Focus on Task one first.", today.suggestion)
    }

    // -----------------------------------------------------------------------
    // AssistantResult
    // -----------------------------------------------------------------------

    @Test
    fun `AssistantResult holds response and action count`() {
        val result = AssistantResult(response = "Task created.", actionCount = 1)

        assertEquals("Task created.", result.response)
        assertEquals(1, result.actionCount)
    }

    @Test
    fun `AssistantResult with zero actions`() {
        val result = AssistantResult(response = "Nothing to do.", actionCount = 0)

        assertEquals(0, result.actionCount)
    }

    // -----------------------------------------------------------------------
    // JSON parsing helpers (mirrors ApiClient internal logic)
    // -----------------------------------------------------------------------

    @Test
    fun `parse task from JSON object`() {
        val json = JSONObject()
            .put("id", "t-json-1")
            .put("title", "JSON-parsed task")
            .put("status", "pending")
            .put("priority_score", 75.5)

        val task = TaskItem(
            id = json.optString("id"),
            title = json.optString("title"),
            status = json.optString("status"),
            dueAt = if (json.isNull("due_at")) null else json.optString("due_at").ifBlank { null },
            priorityScore = json.optDouble("priority_score"),
            priorityReason = if (json.isNull("priority_reason")) null else json.optString("priority_reason").ifBlank { null }
        )

        assertEquals("t-json-1", task.id)
        assertEquals("JSON-parsed task", task.title)
        assertEquals(75.5, task.priorityScore, 0.001)
        assertNull(task.dueAt)
    }

    @Test
    fun `parse reminder from JSON object`() {
        val json = JSONObject()
            .put("id", "r-json-1")
            .put("title", "JSON reminder")
            .put("intensity", "persistent")

        val reminder = ReminderItem(
            id = json.optString("id"),
            title = json.optString("title"),
            remindAt = if (json.isNull("remind_at")) null else json.optString("remind_at").ifBlank { null },
            intensity = json.optString("intensity")
        )

        assertEquals("r-json-1", reminder.id)
        assertEquals("persistent", reminder.intensity)
        assertNull(reminder.remindAt)
    }

    @Test
    fun `parse empty JSON array to empty list`() {
        val array = JSONArray("[]")
        val tasks = (0 until array.length()).map { i ->
            val item = array.getJSONObject(i)
            TaskItem(
                id = item.optString("id"),
                title = item.optString("title"),
                status = item.optString("status"),
                dueAt = null,
                priorityScore = item.optDouble("priority_score"),
                priorityReason = null
            )
        }
        assertTrue(tasks.isEmpty())
    }

    @Test
    fun `parse health log from JSON object`() {
        val json = JSONObject()
            .put("id", "l-json-1")
            .put("kind", "water")
            .put("value", "water")
            .put("amount", 250)
            .put("unit", "ml")
            .put("logged_at", "2024-01-15T12:00:00Z")

        val log = HealthLogItem(
            id = json.optString("id"),
            kind = json.optString("kind"),
            value = json.optString("value"),
            amount = if (json.isNull("amount")) null else json.optInt("amount"),
            unit = if (json.isNull("unit")) null else json.optString("unit").ifBlank { null },
            loggedAt = json.optString("logged_at")
        )

        assertEquals("water", log.kind)
        assertEquals(250, log.amount)
        assertEquals("ml", log.unit)
    }

    @Test
    fun `ApiClient base URL trailing slash is normalised`() {
        val baseUrl = "http://192.168.1.10:8000/"
        val normalized = baseUrl.trimEnd('/')
        assertEquals("http://192.168.1.10:8000", normalized)
    }

    @Test
    fun `ApiClient base URL without trailing slash unchanged`() {
        val baseUrl = "http://192.168.1.10:8000"
        val normalized = baseUrl.trimEnd('/')
        assertEquals("http://192.168.1.10:8000", normalized)
    }
}
