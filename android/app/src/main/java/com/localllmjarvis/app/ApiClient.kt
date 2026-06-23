package com.localllmjarvis.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.IOException
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

class ApiClient(private val baseUrl: String, private val apiKey: String) {
    suspend fun getToday(): TodayState = withContext(Dispatchers.IO) {
        val body = request(path = "/today", method = "GET")
        parseToday(JSONObject(body))
    }

    suspend fun sendAssistantMessage(text: String): AssistantResult = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("text", text)
            .put("source", "chat")
            .toString()
        val body = request(path = "/assistant/message", method = "POST", body = payload)
        val json = JSONObject(body)
        AssistantResult(
            response = json.optString("response"),
            actionCount = json.optJSONArray("actions")?.length() ?: 0
        )
    }

    suspend fun completeTask(taskId: String): Unit = withContext(Dispatchers.IO) {
        updateTask(taskId = taskId, status = "done")
        Unit
    }

    suspend fun createTask(title: String, dueAt: String?): TaskItem = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("title", title)
            .put("source", "android")
        if (dueAt != null) {
            payload.put("due_at", dueAt)
        }
        val body = request(path = "/tasks", method = "POST", body = payload.toString())
        JSONObject(body).toTask()
    }

    suspend fun updateTask(taskId: String, title: String? = null, dueAt: String? = null, status: String? = null): TaskItem =
        withContext(Dispatchers.IO) {
            val payload = JSONObject()
            if (title != null) payload.put("title", title)
            if (dueAt != null) payload.put("due_at", dueAt)
            if (status != null) payload.put("status", status)
            val body = request(path = "/tasks/$taskId", method = "PATCH", body = payload.toString())
            JSONObject(body).toTask()
        }

    suspend fun listReminders(): List<ReminderItem> = withContext(Dispatchers.IO) {
        val body = request(path = "/reminders", method = "GET")
        JSONArray(body).toReminders()
    }

    suspend fun createReminder(title: String, remindAt: String?, intensity: String): ReminderItem = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("title", title)
            .put("intensity", intensity)
            .put("source", "android")
        if (remindAt != null) {
            payload.put("remind_at", remindAt)
        }
        val body = request(path = "/reminders", method = "POST", body = payload.toString())
        JSONObject(body).toReminder()
    }

    suspend fun updateReminder(
        reminderId: String,
        title: String? = null,
        remindAt: String? = null,
        status: String? = null,
        intensity: String? = null
    ): ReminderItem = withContext(Dispatchers.IO) {
        val payload = JSONObject()
        if (title != null) payload.put("title", title)
        if (remindAt != null) payload.put("remind_at", remindAt)
        if (status != null) payload.put("status", status)
        if (intensity != null) payload.put("intensity", intensity)
        val body = request(path = "/reminders/$reminderId", method = "PATCH", body = payload.toString())
        JSONObject(body).toReminder()
    }

    private fun request(path: String, method: String, body: String? = null): String {
        val normalizedBase = baseUrl.trimEnd('/')
        val connection = URL("$normalizedBase$path").openConnection() as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = 8000
            connection.readTimeout = 15000
            connection.setRequestProperty("Accept", "application/json")
            if (apiKey.isNotBlank()) {
                connection.setRequestProperty("X-API-Key", apiKey)
            }

            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { stream ->
                    stream.write(body.toByteArray(Charsets.UTF_8))
                }
            }

            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = if (stream != null) {
                stream.use { input ->
                    BufferedReader(InputStreamReader(input)).readText()
                }
            } else {
                ""
            }

            if (status !in 200..299) {
                throw IllegalStateException("API request failed: $status $response")
            }
            return response
        } catch (_: IOException) {
            throw IllegalStateException("Network unavailable. Check connection and API URL, then retry.")
        } finally {
            connection.disconnect()
        }
    }

    private fun parseToday(json: JSONObject): TodayState {
        return TodayState(
            generatedAt = json.optString("generated_at"),
            topPriorities = json.optJSONArray("top_priorities").toTasks(),
            upcomingReminders = json.optJSONArray("upcoming_reminders").toReminders(),
            recentLogs = json.optJSONArray("recent_logs").toHealthLogs(),
            suggestion = json.optString("suggestion")
        )
    }

    private fun JSONArray?.toTasks(): List<TaskItem> {
        if (this == null) return emptyList()
        return (0 until length()).map { index ->
            getJSONObject(index).toTask()
        }
    }

    private fun JSONArray?.toReminders(): List<ReminderItem> {
        if (this == null) return emptyList()
        return (0 until length()).map { index ->
            getJSONObject(index).toReminder()
        }
    }

    private fun JSONArray?.toHealthLogs(): List<HealthLogItem> {
        if (this == null) return emptyList()
        return (0 until length()).map { index ->
            val item = getJSONObject(index)
            HealthLogItem(
                id = item.optString("id"),
                kind = item.optString("kind"),
                value = item.optString("value"),
                amount = if (item.isNull("amount")) null else item.optInt("amount"),
                unit = item.optNullableString("unit"),
                loggedAt = item.optString("logged_at")
            )
        }
    }
}

private fun JSONObject.toTask(): TaskItem {
    return TaskItem(
        id = optString("id"),
        title = optString("title"),
        status = optString("status"),
        dueAt = optNullableString("due_at"),
        priorityScore = optDouble("priority_score"),
        priorityReason = optNullableString("priority_reason")
    )
}

private fun JSONObject.toReminder(): ReminderItem {
    return ReminderItem(
        id = optString("id"),
        title = optString("title"),
        remindAt = optNullableString("remind_at"),
        status = optString("status", "active"),
        intensity = optString("intensity")
    )
}

private fun JSONObject.optNullableString(name: String): String? {
    if (isNull(name)) return null
    return optString(name).ifBlank { null }
}
