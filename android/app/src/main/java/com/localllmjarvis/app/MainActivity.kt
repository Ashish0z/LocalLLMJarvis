package com.localllmjarvis.app

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { LocalJarvisApp() }
    }
}

@Composable
fun LocalJarvisApp() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val preferences = remember { AppPreferences(context) }
    val scope = rememberCoroutineScope()

    var apiBaseUrl by remember { mutableStateOf(preferences.apiBaseUrl) }
    var apiKey by remember { mutableStateOf(preferences.apiKey) }
    var today by remember { mutableStateOf<TodayState?>(null) }
    var captureText by remember { mutableStateOf("") }
    var assistantResponse by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var offline by remember { mutableStateOf(false) }

    var todayLoading by remember { mutableStateOf(false) }
    var captureLoading by remember { mutableStateOf(false) }
    var taskSyncing by remember { mutableStateOf(false) }
    var reminderSyncing by remember { mutableStateOf(false) }

    var newTaskTitle by remember { mutableStateOf("") }
    var newTaskDueAt by remember { mutableStateOf("") }
    var savingTask by remember { mutableStateOf(false) }
    var editingTaskId by remember { mutableStateOf<String?>(null) }
    var editTaskTitle by remember { mutableStateOf("") }
    var editTaskDueAt by remember { mutableStateOf("") }

    var newReminderTitle by remember { mutableStateOf("") }
    var newReminderAt by remember { mutableStateOf("") }
    var newReminderIntensity by remember { mutableStateOf("standard") }
    var savingReminder by remember { mutableStateOf(false) }
    var editingReminderId by remember { mutableStateOf<String?>(null) }
    var editReminderTitle by remember { mutableStateOf("") }
    var editReminderAt by remember { mutableStateOf("") }
    var editReminderIntensity by remember { mutableStateOf("standard") }

    fun api() = ApiClient(apiBaseUrl, apiKey)

    fun onError(defaultMessage: String, error: Exception) {
        val message = error.message ?: defaultMessage
        errorMessage = message
        offline = message.startsWith("Network unavailable")
    }

    fun refreshToday() {
        scope.launch {
            todayLoading = true
            try {
                today = api().getToday()
                offline = false
                errorMessage = null
            } catch (error: Exception) {
                onError("Could not load Today.", error)
            } finally {
                todayLoading = false
            }
        }
    }

    fun refreshAfterTaskMutation() {
        scope.launch {
            taskSyncing = true
            try {
                today = api().getToday()
                offline = false
            } catch (error: Exception) {
                onError("Could not sync tasks.", error)
            } finally {
                taskSyncing = false
            }
        }
    }

    fun refreshAfterReminderMutation() {
        scope.launch {
            reminderSyncing = true
            try {
                today = api().getToday()
                offline = false
            } catch (error: Exception) {
                onError("Could not sync reminders.", error)
            } finally {
                reminderSyncing = false
            }
        }
    }

    fun sendCapture() {
        val text = captureText.trim()
        if (text.isBlank()) return
        scope.launch {
            captureLoading = true
            errorMessage = null
            try {
                val result = api().sendAssistantMessage(text)
                assistantResponse = result.response
                captureText = ""
                today = api().getToday()
                offline = false
            } catch (error: Exception) {
                onError("Could not send capture.", error)
            } finally {
                captureLoading = false
            }
        }
    }

    val notificationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) {
            errorMessage = "Notifications are disabled, so reminder alerts may not appear."
        }
    }

    LaunchedEffect(Unit) { refreshToday() }

    LaunchedEffect(apiBaseUrl, apiKey) {
        ReminderWorker.schedule(context, apiBaseUrl, apiKey)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    MaterialTheme(
        colorScheme = MaterialTheme.colorScheme.copy(
            primary = Color(0xFF2F6B45),
            surface = Color.White,
            background = Color(0xFFF6F8F3)
        )
    ) {
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .background(Color(0xFFF6F8F3)),
            color = Color(0xFFF6F8F3)
        ) {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                item {
                    Header(
                        apiBaseUrl = apiBaseUrl,
                        loading = todayLoading,
                        onRefresh = ::refreshToday
                    )
                }
                item {
                    TodayCard(today = today, loading = todayLoading)
                }
                item {
                    CaptureCard(
                        captureText = captureText,
                        assistantResponse = assistantResponse,
                        loading = captureLoading,
                        onTextChanged = { captureText = it },
                        onSend = ::sendCapture
                    )
                }
                if (offline) {
                    item {
                        OfflineCard(onRetry = ::refreshToday)
                    }
                }
                if (errorMessage != null) {
                    item {
                        MessageCard(text = errorMessage.orEmpty(), isError = true)
                    }
                }

                item {
                    SectionTitle("Top priorities", loading = taskSyncing)
                }
                item {
                    TaskEditorCard(
                        title = newTaskTitle,
                        dueAt = newTaskDueAt,
                        loading = savingTask,
                        actionLabel = "Create task",
                        onTitleChanged = { newTaskTitle = it },
                        onDueAtChanged = { newTaskDueAt = it },
                        onSave = {
                            val title = newTaskTitle.trim()
                            if (title.isBlank()) return@TaskEditorCard
                            val dueAt = normalizeDateInputOrNull(newTaskDueAt)
                            if (newTaskDueAt.isNotBlank() && dueAt == null) {
                                errorMessage = "Use ISO date-time for task due date."
                                return@TaskEditorCard
                            }
                            scope.launch {
                                savingTask = true
                                try {
                                    api().createTask(title = title, dueAt = dueAt)
                                    newTaskTitle = ""
                                    newTaskDueAt = ""
                                    refreshAfterTaskMutation()
                                    errorMessage = null
                                } catch (error: Exception) {
                                    onError("Could not create task.", error)
                                } finally {
                                    savingTask = false
                                }
                            }
                        }
                    )
                }
                val tasks = today?.topPriorities.orEmpty()
                if (tasks.isEmpty()) {
                    item { EmptyText("No pending priorities yet.") }
                } else {
                    items(tasks, key = { it.id }) { task ->
                        TaskRow(
                            task = task,
                            busy = taskSyncing && editingTaskId == null,
                            onDone = {
                                scope.launch {
                                    taskSyncing = true
                                    try {
                                        api().completeTask(task.id)
                                        today = api().getToday()
                                        offline = false
                                    } catch (error: Exception) {
                                        onError("Could not complete task.", error)
                                    } finally {
                                        taskSyncing = false
                                    }
                                }
                            },
                            onEdit = {
                                editingTaskId = task.id
                                editTaskTitle = task.title
                                editTaskDueAt = task.dueAt.orEmpty()
                            }
                        )
                        if (editingTaskId == task.id) {
                            TaskEditorCard(
                                title = editTaskTitle,
                                dueAt = editTaskDueAt,
                                loading = taskSyncing,
                                actionLabel = "Save task",
                                onTitleChanged = { editTaskTitle = it },
                                onDueAtChanged = { editTaskDueAt = it },
                                onSave = {
                                    val title = editTaskTitle.trim()
                                    if (title.isBlank()) return@TaskEditorCard
                                    val dueAt = normalizeDateInputOrNull(editTaskDueAt)
                                    if (editTaskDueAt.isNotBlank() && dueAt == null) {
                                        errorMessage = "Use ISO date-time for task due date."
                                        return@TaskEditorCard
                                    }
                                    scope.launch {
                                        taskSyncing = true
                                        try {
                                            api().updateTask(task.id, title = title, dueAt = dueAt)
                                            today = api().getToday()
                                            editingTaskId = null
                                            offline = false
                                        } catch (error: Exception) {
                                            onError("Could not update task.", error)
                                        } finally {
                                            taskSyncing = false
                                        }
                                    }
                                },
                                onCancel = { editingTaskId = null }
                            )
                        }
                    }
                }

                item {
                    SectionTitle("Reminders", loading = reminderSyncing)
                }
                item {
                    ReminderEditorCard(
                        title = newReminderTitle,
                        remindAt = newReminderAt,
                        intensity = newReminderIntensity,
                        loading = savingReminder,
                        actionLabel = "Create reminder",
                        onTitleChanged = { newReminderTitle = it },
                        onRemindAtChanged = { newReminderAt = it },
                        onIntensityChanged = { newReminderIntensity = it },
                        onSave = {
                            val title = newReminderTitle.trim()
                            if (title.isBlank()) return@ReminderEditorCard
                            val remindAt = normalizeDateInputOrNull(newReminderAt)
                            if (newReminderAt.isNotBlank() && remindAt == null) {
                                errorMessage = "Use ISO date-time for reminder time."
                                return@ReminderEditorCard
                            }
                            scope.launch {
                                savingReminder = true
                                try {
                                    api().createReminder(
                                        title = title,
                                        remindAt = remindAt,
                                        intensity = newReminderIntensity
                                    )
                                    newReminderTitle = ""
                                    newReminderAt = ""
                                    refreshAfterReminderMutation()
                                    errorMessage = null
                                } catch (error: Exception) {
                                    onError("Could not create reminder.", error)
                                } finally {
                                    savingReminder = false
                                }
                            }
                        }
                    )
                }
                val reminders = today?.upcomingReminders.orEmpty()
                if (reminders.isEmpty()) {
                    item { EmptyText("No upcoming reminders.") }
                } else {
                    items(reminders, key = { it.id }) { reminder ->
                        ReminderRow(
                            reminder = reminder,
                            busy = reminderSyncing && editingReminderId == null,
                            onDone = {
                                scope.launch {
                                    reminderSyncing = true
                                    try {
                                        api().updateReminder(reminder.id, status = "done")
                                        today = api().getToday()
                                        offline = false
                                    } catch (error: Exception) {
                                        onError("Could not mark reminder done.", error)
                                    } finally {
                                        reminderSyncing = false
                                    }
                                }
                            },
                            onSnooze = {
                                scope.launch {
                                    reminderSyncing = true
                                    try {
                                        api().updateReminder(
                                            reminderId = reminder.id,
                                            status = "active",
                                            remindAt = snoozeUntil(reminder.remindAt)
                                        )
                                        today = api().getToday()
                                        offline = false
                                    } catch (error: Exception) {
                                        onError("Could not snooze reminder.", error)
                                    } finally {
                                        reminderSyncing = false
                                    }
                                }
                            },
                            onEdit = {
                                editingReminderId = reminder.id
                                editReminderTitle = reminder.title
                                editReminderAt = reminder.remindAt.orEmpty()
                                editReminderIntensity = reminder.intensity
                            }
                        )
                        if (editingReminderId == reminder.id) {
                            ReminderEditorCard(
                                title = editReminderTitle,
                                remindAt = editReminderAt,
                                intensity = editReminderIntensity,
                                loading = reminderSyncing,
                                actionLabel = "Save reminder",
                                onTitleChanged = { editReminderTitle = it },
                                onRemindAtChanged = { editReminderAt = it },
                                onIntensityChanged = { editReminderIntensity = it },
                                onSave = {
                                    val title = editReminderTitle.trim()
                                    if (title.isBlank()) return@ReminderEditorCard
                                    val remindAt = normalizeDateInputOrNull(editReminderAt)
                                    if (editReminderAt.isNotBlank() && remindAt == null) {
                                        errorMessage = "Use ISO date-time for reminder time."
                                        return@ReminderEditorCard
                                    }
                                    scope.launch {
                                        reminderSyncing = true
                                        try {
                                            api().updateReminder(
                                                reminderId = reminder.id,
                                                title = title,
                                                remindAt = remindAt,
                                                intensity = editReminderIntensity
                                            )
                                            today = api().getToday()
                                            editingReminderId = null
                                            offline = false
                                        } catch (error: Exception) {
                                            onError("Could not update reminder.", error)
                                        } finally {
                                            reminderSyncing = false
                                        }
                                    }
                                },
                                onCancel = { editingReminderId = null }
                            )
                        }
                    }
                }

                item {
                    SettingsCard(
                        apiBaseUrl = apiBaseUrl,
                        apiKey = apiKey,
                        onApiBaseUrlChanged = {
                            apiBaseUrl = it
                            preferences.apiBaseUrl = it
                        },
                        onApiKeyChanged = {
                            apiKey = it
                            preferences.apiKey = it
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun Header(apiBaseUrl: String, loading: Boolean, onRefresh: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.Bottom
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text("Local LLM Jarvis", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text(
                text = apiBaseUrl,
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFF3E4D43),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
        TextButton(onClick = onRefresh, enabled = !loading, modifier = Modifier.heightIn(min = 48.dp)) {
            Text(if (loading) "Syncing..." else "Refresh")
        }
    }
}

@Composable
private fun TodayCard(today: TodayState?, loading: Boolean) {
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Today", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            val generated = formatApiDateTime(today?.generatedAt)
            if (generated != null) {
                Text("Last synced: $generated", style = MaterialTheme.typography.bodySmall, color = Color(0xFF3E4D43))
            } else if (loading) {
                Text("Syncing latest day summary...", style = MaterialTheme.typography.bodySmall, color = Color(0xFF3E4D43))
            }
            Text(
                text = today?.suggestion ?: "Connect to the local assistant to load your day.",
                style = MaterialTheme.typography.bodyLarge
            )
        }
    }
}

@Composable
private fun CaptureCard(
    captureText: String,
    assistantResponse: String,
    loading: Boolean,
    onTextChanged: (String) -> Unit,
    onSend: () -> Unit
) {
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Quick capture", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = captureText,
                onValueChange = onTextChanged,
                modifier = Modifier.fillMaxWidth(),
                minLines = 3,
                placeholder = { Text("Add a task, set a reminder, or log water and meals") }
            )
            Button(
                onClick = onSend,
                enabled = !loading && captureText.isNotBlank(),
                modifier = Modifier.heightIn(min = 48.dp)
            ) {
                Text(if (loading) "Sending..." else "Send")
            }
            if (assistantResponse.isNotBlank()) {
                MessageCard(text = assistantResponse, isError = false)
            }
        }
    }
}

@Composable
private fun TaskEditorCard(
    title: String,
    dueAt: String,
    loading: Boolean,
    actionLabel: String,
    onTitleChanged: (String) -> Unit,
    onDueAtChanged: (String) -> Unit,
    onSave: () -> Unit,
    onCancel: (() -> Unit)? = null
) {
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedTextField(
                value = title,
                onValueChange = onTitleChanged,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Task title") },
                singleLine = true
            )
            OutlinedTextField(
                value = dueAt,
                onValueChange = onDueAtChanged,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Due at (ISO, optional)") },
                singleLine = true
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onSave, enabled = !loading, modifier = Modifier.heightIn(min = 48.dp)) {
                    Text(if (loading) "Saving..." else actionLabel)
                }
                if (onCancel != null) {
                    TextButton(onClick = onCancel, enabled = !loading, modifier = Modifier.heightIn(min = 48.dp)) {
                        Text("Cancel")
                    }
                }
            }
        }
    }
}

@Composable
private fun ReminderEditorCard(
    title: String,
    remindAt: String,
    intensity: String,
    loading: Boolean,
    actionLabel: String,
    onTitleChanged: (String) -> Unit,
    onRemindAtChanged: (String) -> Unit,
    onIntensityChanged: (String) -> Unit,
    onSave: () -> Unit,
    onCancel: (() -> Unit)? = null
) {
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedTextField(
                value = title,
                onValueChange = onTitleChanged,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Reminder title") },
                singleLine = true
            )
            OutlinedTextField(
                value = remindAt,
                onValueChange = onRemindAtChanged,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Remind at (ISO, optional)") },
                singleLine = true
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("gentle", "standard", "persistent").forEach { option ->
                    TextButton(
                        onClick = { onIntensityChanged(option) },
                        modifier = Modifier.heightIn(min = 48.dp)
                    ) {
                        Text(if (intensity == option) "• $option" else option)
                    }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onSave, enabled = !loading, modifier = Modifier.heightIn(min = 48.dp)) {
                    Text(if (loading) "Saving..." else actionLabel)
                }
                if (onCancel != null) {
                    TextButton(onClick = onCancel, enabled = !loading, modifier = Modifier.heightIn(min = 48.dp)) {
                        Text("Cancel")
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageCard(text: String, isError: Boolean) {
    val color = if (isError) Color(0xFFFFEDE8) else Color(0xFFEAF4EC)
    val textColor = if (isError) Color(0xFF5D2216) else Color(0xFF1E3A2A)
    Surface(color = color, shape = RoundedCornerShape(8.dp)) {
        Text(text = text, color = textColor, modifier = Modifier.padding(12.dp))
    }
}

@Composable
private fun OfflineCard(onRetry: () -> Unit) {
    Surface(color = Color(0xFFFFF6E8), shape = RoundedCornerShape(8.dp)) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("You appear to be offline. Data shown may be stale.", color = Color(0xFF5C4300))
            Button(onClick = onRetry, modifier = Modifier.heightIn(min = 48.dp)) {
                Text("Retry sync")
            }
        }
    }
}

@Composable
private fun SectionTitle(title: String, loading: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        if (loading) {
            Text("Syncing...", style = MaterialTheme.typography.bodySmall, color = Color(0xFF3E4D43))
        }
    }
}

@Composable
private fun TaskRow(task: TaskItem, busy: Boolean, onDone: () -> Unit, onEdit: () -> Unit) {
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(task.title, fontWeight = FontWeight.Medium)
                Spacer(Modifier.height(4.dp))
                val due = formatApiDateTime(task.dueAt)
                val detail = buildString {
                    append("Priority ${task.priorityScore.toInt()}")
                    append(" • ${task.priorityReason ?: "waiting for more context"}")
                    if (due != null) append(" • due $due")
                }
                Text(detail, style = MaterialTheme.typography.bodySmall, color = Color(0xFF4B594F))
            }
            Spacer(Modifier.width(6.dp))
            TextButton(onClick = onEdit, enabled = !busy, modifier = Modifier.heightIn(min = 48.dp)) {
                Text("Edit")
            }
            TextButton(onClick = onDone, enabled = !busy, modifier = Modifier.heightIn(min = 48.dp)) {
                Text(if (busy) "..." else "Done")
            }
        }
    }
}

@Composable
private fun ReminderRow(reminder: ReminderItem, busy: Boolean, onDone: () -> Unit, onSnooze: () -> Unit, onEdit: () -> Unit) {
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(reminder.title, fontWeight = FontWeight.Medium)
            val reminderAt = formatApiDateTime(reminder.remindAt) ?: "No schedule"
            Text(
                "${reminder.intensity} • ${reminder.status} • $reminderAt",
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFF4B594F)
            )
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                TextButton(onClick = onEdit, enabled = !busy, modifier = Modifier.heightIn(min = 48.dp)) {
                    Text("Edit")
                }
                TextButton(onClick = onSnooze, enabled = !busy, modifier = Modifier.heightIn(min = 48.dp)) {
                    Text("Snooze")
                }
                TextButton(onClick = onDone, enabled = !busy, modifier = Modifier.heightIn(min = 48.dp)) {
                    Text("Done")
                }
            }
        }
    }
}

@Composable
private fun SettingsCard(
    apiBaseUrl: String,
    apiKey: String,
    onApiBaseUrlChanged: (String) -> Unit,
    onApiKeyChanged: (String) -> Unit
) {
    var draft by remember(apiBaseUrl) { mutableStateOf(apiBaseUrl) }
    var apiKeyDraft by remember(apiKey) { mutableStateOf(apiKey) }
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Settings", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = draft,
                onValueChange = { draft = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Assistant API URL") },
                singleLine = true
            )
            OutlinedTextField(
                value = apiKeyDraft,
                onValueChange = { apiKeyDraft = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("API key") },
                singleLine = true
            )
            Button(
                onClick = {
                    onApiBaseUrlChanged(draft)
                    onApiKeyChanged(apiKeyDraft)
                },
                modifier = Modifier.heightIn(min = 48.dp)
            ) {
                Text("Save settings")
            }
        }
    }
}

@Composable
private fun EmptyText(text: String) {
    Text(text = text, color = Color(0xFF4B594F), modifier = Modifier.padding(vertical = 4.dp))
}
