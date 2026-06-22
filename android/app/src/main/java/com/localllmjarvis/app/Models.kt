package com.localllmjarvis.app

data class TaskItem(
    val id: String,
    val title: String,
    val status: String,
    val dueAt: String?,
    val priorityScore: Double,
    val priorityReason: String?
)

data class ReminderItem(
    val id: String,
    val title: String,
    val remindAt: String?,
    val intensity: String
)

data class HealthLogItem(
    val id: String,
    val kind: String,
    val value: String,
    val amount: Int?,
    val unit: String?,
    val loggedAt: String
)

data class TodayState(
    val generatedAt: String,
    val topPriorities: List<TaskItem>,
    val upcomingReminders: List<ReminderItem>,
    val recentLogs: List<HealthLogItem>,
    val suggestion: String
)

data class AssistantResult(
    val response: String,
    val actionCount: Int
)

