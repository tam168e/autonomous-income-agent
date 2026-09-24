package com.masoud.autonomousincome.data

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

class AppDatabase(context: Context) : SQLiteOpenHelper(context, "income_agent.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""
            CREATE TABLE opportunities(
              id TEXT PRIMARY KEY,
              provider_id TEXT NOT NULL,
              name TEXT NOT NULL,
              description TEXT NOT NULL,
              estimated_hourly_usd REAL NOT NULL,
              fee_usd REAL NOT NULL,
              minimum_withdrawal_usd REAL NOT NULL,
              requires_capital INTEGER NOT NULL,
              requires_kyc INTEGER NOT NULL,
              automation_allowed INTEGER NOT NULL,
              risk_level TEXT NOT NULL,
              eligibility_status TEXT NOT NULL,
              source_url TEXT NOT NULL,
              last_verified_at TEXT,
              score REAL NOT NULL
            )
        """.trimIndent())
        db.execSQL("CREATE TABLE earnings(id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL, gross_usd REAL NOT NULL, fee_usd REAL NOT NULL, payment_id TEXT NOT NULL, verified_at TEXT NOT NULL)")
        db.execSQL("CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execSQL("CREATE TABLE wallets(id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT NOT NULL, network TEXT NOT NULL, asset TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)")
        db.execSQL("CREATE TABLE logs(id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, level TEXT NOT NULL, message TEXT NOT NULL)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Future schema migrations go here.
    }
}
