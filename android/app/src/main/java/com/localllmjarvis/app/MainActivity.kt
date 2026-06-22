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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            LocalJarvisApp()
        }
    }
}

@Composable
fun LocalJarvisApp() {
    val context = LocalContext.current
    val preferences = remember { AppPreferences(context) }
    val scope = rememberCoroutineScope()

    var apiBaseUrl by remember { mutableStateOf(preferences.apiBaseUrl) }
    var apiKey by remember { mutableStateOf(preferences.apiKey) }
    var today by remember { mutableStateOf<TodayState?>(null) }
    var captureText by remember { mutableStateOf("") }
    var assistantResponse by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }

    fun api() = ApiClient(apiBaseUrl, apiKey)

    val notificationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) {
            errorMessage = "Notifications are disabled, so reminder alerts may not appear."
        }
    }

    fun refreshToday() {
        scope.launch {
            loading = true
            errorMessage = null
            try {
                today = api().getToday()
            } catch (error: Exception) {
                errorMessage = error.message ?: "Could not load Today."
            } finally {
                loading = false
            }
        }
    }

    fun sendCapture() {
        val text = captureText.trim()
        if (text.isBlank()) return
        scope.launch {
            loading = true
            errorMessage = null
            try {
                val result = api().sendAssistantMessage(text)
                assistantResponse = result.response
                captureText = ""
                today = api().getToday()
            } catch (error: Exception) {
                errorMessage = error.message ?: "Could not send capture."
            } finally {
                loading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshToday()
    }

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
                    Header(apiBaseUrl = apiBaseUrl, loading = loading, onRefresh = ::refreshToday)
                }
                item {
                    TodayCard(today = today)
                }
                item {
                    CaptureCard(
                        captureText = captureText,
                        assistantResponse = assistantResponse,
                        loading = loading,
                        onTextChanged = { captureText = it },
                        onSend = ::sendCapture
                    )
                }
                if (errorMessage != null) {
                    item {
                        MessageCard(text = errorMessage.orEmpty(), isError = true)
                    }
                }
                item {
                    SectionTitle("Top priorities")
                }
                val tasks = today?.topPriorities.orEmpty()
                if (tasks.isEmpty()) {
                    item { EmptyText("No pending priorities yet.") }
                } else {
                    items(tasks, key = { it.id }) { task ->
                        TaskRow(task = task) {
                            scope.launch {
                                try {
                                    api().completeTask(task.id)
                                    today = api().getToday()
                                } catch (error: Exception) {
                                    errorMessage = error.message ?: "Could not complete task."
                                }
                            }
                        }
                    }
                }
                item {
                    SectionTitle("Reminders")
                }
                val reminders = today?.upcomingReminders.orEmpty()
                if (reminders.isEmpty()) {
                    item { EmptyText("No upcoming reminders.") }
                } else {
                    items(reminders, key = { it.id }) { reminder ->
                        ReminderRow(reminder)
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
                color = Color(0xFF5B6B60),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
        TextButton(onClick = onRefresh, enabled = !loading) {
            Text(if (loading) "Syncing" else "Refresh")
        }
    }
}

@Composable
private fun TodayCard(today: TodayState?) {
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Today", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
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
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(onClick = onSend, enabled = !loading && captureText.isNotBlank()) {
                    Text("Send")
                }
            }
            if (assistantResponse.isNotBlank()) {
                MessageCard(text = assistantResponse, isError = false)
            }
        }
    }
}

@Composable
private fun MessageCard(text: String, isError: Boolean) {
    val color = if (isError) Color(0xFFFFEDE8) else Color(0xFFEAF4EC)
    val textColor = if (isError) Color(0xFF7B2E1F) else Color(0xFF244832)
    Surface(color = color, shape = RoundedCornerShape(8.dp)) {
        Text(text = text, color = textColor, modifier = Modifier.padding(12.dp))
    }
}

@Composable
private fun SectionTitle(title: String) {
    Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun TaskRow(task: TaskItem, onDone: () -> Unit) {
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
                Text(
                    "Priority ${task.priorityScore.toInt()} - ${task.priorityReason ?: "waiting for more context"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFF637166)
                )
            }
            Spacer(Modifier.width(10.dp))
            TextButton(onClick = onDone) {
                Text("Done")
            }
        }
    }
}

@Composable
private fun ReminderRow(reminder: ReminderItem) {
    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(reminder.title, fontWeight = FontWeight.Medium)
            Text(
                "${reminder.intensity} reminder${reminder.remindAt?.let { " - $it" } ?: ""}",
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFF637166)
            )
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
                }
            ) {
                Text("Save settings")
            }
        }
    }
}

@Composable
private fun EmptyText(text: String) {
    Text(text = text, color = Color(0xFF637166), modifier = Modifier.padding(vertical = 4.dp))
}
