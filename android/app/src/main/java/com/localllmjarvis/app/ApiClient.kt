package com.localllmjarvis.app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
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
        request(
            path = "/tasks/$taskId",
            method = "PATCH",
            body = JSONObject().put("status", "done").toString()
        )
        Unit
    }

    suspend fun listReminders(): List<ReminderItem> = withContext(Dispatchers.IO) {
        val body = request(path = "/reminders", method = "GET")
        JSONArray(body).toReminders()
    }

    private fun request(path: String, method: String, body: String? = null): String {
        val normalizedBase = baseUrl.trimEnd('/')
        val connection = URL("$normalizedBase$path").openConnection() as HttpURLConnection
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
        val response = stream.use { input ->
            BufferedReader(InputStreamReader(input)).readText()
        }

        if (status !in 200..299) {
            throw IllegalStateException("API request failed: $status $response")
        }
        return response
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
            val item = getJSONObject(index)
            TaskItem(
                id = item.optString("id"),
                title = item.optString("title"),
                status = item.optString("status"),
                dueAt = item.optNullableString("due_at"),
                priorityScore = item.optDouble("priority_score"),
                priorityReason = item.optNullableString("priority_reason")
            )
        }
    }

    private fun JSONArray?.toReminders(): List<ReminderItem> {
        if (this == null) return emptyList()
        return (0 until length()).map { index ->
            val item = getJSONObject(index)
            ReminderItem(
                id = item.optString("id"),
                title = item.optString("title"),
                remindAt = item.optNullableString("remind_at"),
                intensity = item.optString("intensity")
            )
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

private fun JSONObject.optNullableString(name: String): String? {
    if (isNull(name)) return null
    return optString(name).ifBlank { null }
}
