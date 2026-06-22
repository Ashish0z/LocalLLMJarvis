package com.localllmjarvis.app

import android.content.Context

class AppPreferences(context: Context) {
    private val prefs = context.getSharedPreferences("local_llm_jarvis", Context.MODE_PRIVATE)

    var apiBaseUrl: String
        get() = prefs.getString(KEY_API_BASE_URL, DEFAULT_API_BASE_URL) ?: DEFAULT_API_BASE_URL
        set(value) {
            prefs.edit().putString(KEY_API_BASE_URL, value.trim().trimEnd('/')).apply()
        }

    var apiKey: String
        get() = prefs.getString(KEY_API_KEY, "") ?: ""
        set(value) {
            prefs.edit().putString(KEY_API_KEY, value.trim()).apply()
        }

    companion object {
        const val DEFAULT_API_BASE_URL = "http://10.0.2.2:8000"
        private const val KEY_API_BASE_URL = "api_base_url"
        private const val KEY_API_KEY = "api_key"
    }
}
