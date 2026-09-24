package com.masoud.autonomousincome.security

import android.content.Context
import android.content.SharedPreferences

class SecureSettings(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("secure_settings", Context.MODE_PRIVATE)

    fun getBoolean(key: String, default: Boolean) = prefs.getBoolean(key, default)
    fun putBoolean(key: String, value: Boolean) { prefs.edit().putBoolean(key, value).apply() }
    fun getString(key: String, default: String = "") = prefs.getString(key, default) ?: default
    fun putString(key: String, value: String) { prefs.edit().putString(key, value).apply() }
}
