package com.localllmjarvis.app

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat.Action
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.util.concurrent.TimeUnit

class ReminderWorker(
    private val context: Context,
    workerParameters: WorkerParameters
) : CoroutineWorker(context, workerParameters) {
    override suspend fun doWork(): Result {
        val apiBaseUrl = inputData.getString(KEY_API_BASE_URL) ?: return Result.success()
        val apiKey = inputData.getString(KEY_API_KEY).orEmpty()
        val reminders = try {
            ApiClient(apiBaseUrl, apiKey).listReminders()
        } catch (_: Exception) {
            return Result.retry()
        }

        ensureNotificationChannel(context)
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now = OffsetDateTime.now(ZoneOffset.UTC).toInstant()
        reminders.forEach { reminder ->
            val due = reminder.remindAt?.let(::parseApiInstantOrNull) ?: return@forEach
            val alreadyNotified = prefs.getBoolean(reminder.id, false)
            if (!alreadyNotified && !due.isAfter(now)) {
                showReminderNotification(context, reminder, apiBaseUrl, apiKey)
                prefs.edit().putBoolean(reminder.id, true).apply()
            }
        }

        return Result.success()
    }

    companion object {
        private const val WORK_NAME = "local_llm_jarvis_reminders"
        private const val CHANNEL_ID = "jarvis_reminders"
        internal const val PREFS = "notified_reminders"
        private const val KEY_API_BASE_URL = "api_base_url"
        private const val KEY_API_KEY = "api_key"

        fun schedule(context: Context, apiBaseUrl: String, apiKey: String) {
            val request = PeriodicWorkRequestBuilder<ReminderWorker>(15, TimeUnit.MINUTES)
                .setInputData(
                    workDataOf(
                        KEY_API_BASE_URL to apiBaseUrl,
                        KEY_API_KEY to apiKey
                    )
                )
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request
            )
        }

        private fun ensureNotificationChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val manager = context.getSystemService(NotificationManager::class.java)
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Jarvis reminders",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Reminders created by Local LLM Jarvis"
            }
            manager.createNotificationChannel(channel)
        }

        internal fun clearNotifiedFlag(context: Context, reminderId: String) {
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(reminderId).apply()
        }

        private fun showReminderNotification(context: Context, reminder: ReminderItem, apiBaseUrl: String, apiKey: String) {
            if (
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) {
                return
            }

            val openAppIntent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val openAppPendingIntent = PendingIntent.getActivity(
                context,
                reminder.id.hashCode(),
                openAppIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            val doneIntent = Intent(context, NotificationActionReceiver::class.java).apply {
                action = NotificationActionReceiver.ACTION_DONE
                putExtra(NotificationActionReceiver.EXTRA_REMINDER_ID, reminder.id)
                putExtra(NotificationActionReceiver.EXTRA_REMIND_AT, reminder.remindAt)
                putExtra(NotificationActionReceiver.EXTRA_API_BASE_URL, apiBaseUrl)
                putExtra(NotificationActionReceiver.EXTRA_API_KEY, apiKey)
            }
            val donePendingIntent = PendingIntent.getBroadcast(
                context,
                reminder.id.hashCode() + 1,
                doneIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            val snoozeIntent = Intent(context, NotificationActionReceiver::class.java).apply {
                action = NotificationActionReceiver.ACTION_SNOOZE
                putExtra(NotificationActionReceiver.EXTRA_REMINDER_ID, reminder.id)
                putExtra(NotificationActionReceiver.EXTRA_REMIND_AT, reminder.remindAt)
                putExtra(NotificationActionReceiver.EXTRA_API_BASE_URL, apiBaseUrl)
                putExtra(NotificationActionReceiver.EXTRA_API_KEY, apiKey)
            }
            val snoozePendingIntent = PendingIntent.getBroadcast(
                context,
                reminder.id.hashCode() + 2,
                snoozeIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            val doneAction = Action.Builder(0, "Done", donePendingIntent).build()
            val snoozeAction = Action.Builder(0, "Snooze", snoozePendingIntent).build()

            val notification = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("Jarvis reminder")
                .setContentText(reminder.title)
                .setStyle(NotificationCompat.BigTextStyle().bigText(reminder.title))
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setContentIntent(openAppPendingIntent)
                .addAction(doneAction)
                .addAction(snoozeAction)
                .setAutoCancel(true)
                .build()

            NotificationManagerCompat.from(context).notify(reminder.id.hashCode(), notification)
        }
    }
}
