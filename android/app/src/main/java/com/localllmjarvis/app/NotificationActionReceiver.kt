package com.localllmjarvis.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationManagerCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class NotificationActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val reminderId = intent.getStringExtra(EXTRA_REMINDER_ID) ?: return
        val apiBaseUrl = intent.getStringExtra(EXTRA_API_BASE_URL).orEmpty()
        val apiKey = intent.getStringExtra(EXTRA_API_KEY).orEmpty()
        val remindAt = intent.getStringExtra(EXTRA_REMIND_AT)
        val result = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                if (apiBaseUrl.isNotBlank()) {
                    val client = ApiClient(apiBaseUrl, apiKey)
                    when (intent.action) {
                        ACTION_DONE -> client.updateReminder(reminderId = reminderId, status = "done")
                        ACTION_SNOOZE ->
                            client.updateReminder(
                                reminderId = reminderId,
                                status = "active",
                                remindAt = snoozeUntil(remindAt)
                            )
                    }
                }
                if (intent.action == ACTION_SNOOZE) {
                    ReminderWorker.clearNotifiedFlag(context, reminderId)
                }
            } catch (_: Exception) {
                if (intent.action == ACTION_SNOOZE) {
                    ReminderWorker.clearNotifiedFlag(context, reminderId)
                }
            } finally {
                NotificationManagerCompat.from(context).cancel(reminderId.hashCode())
                result.finish()
            }
        }
    }

    companion object {
        const val ACTION_DONE = "com.localllmjarvis.app.ACTION_REMINDER_DONE"
        const val ACTION_SNOOZE = "com.localllmjarvis.app.ACTION_REMINDER_SNOOZE"
        const val EXTRA_REMINDER_ID = "extra_reminder_id"
        const val EXTRA_REMIND_AT = "extra_remind_at"
        const val EXTRA_API_BASE_URL = "extra_api_base_url"
        const val EXTRA_API_KEY = "extra_api_key"
    }
}
