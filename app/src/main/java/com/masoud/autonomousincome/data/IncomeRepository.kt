package com.masoud.autonomousincome.data

import android.content.ContentValues
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.masoud.autonomousincome.domain.Opportunity
import com.masoud.autonomousincome.domain.WalletDestination
import java.time.Instant
import java.util.UUID

class IncomeRepository(private val db: AppDatabase) {
    private val gson = Gson()

    fun saveOpportunity(o: Opportunity) {
        val v = ContentValues().apply {
            put("id", o.id)
            put("provider_id", o.providerId)
            put("name", o.name)
            put("description", o.description)
            put("estimated_hourly_usd", o.estimatedHourlyUsd)
            put("fee_usd", o.feeUsd)
            put("minimum_withdrawal_usd", o.minimumWithdrawalUsd)
            put("requires_capital", if (o.requiresCapital) 1 else 0)
            put("requires_kyc", if (o.requiresKyc) 1 else 0)
            put("automation_allowed", if (o.automationAllowed) 1 else 0)
            put("risk_level", o.riskLevel.name)
            put("eligibility_status", o.eligibilityStatus.name)
            put("source_url", o.sourceUrl)
            put("last_verified_at", o.lastVerifiedAt?.toString())
            put("score", o.score)
        }
        db.writableDatabase.insertWithOnConflict("opportunities", null, v, android.database.sqlite.SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun saveOpportunities(items: List<Opportunity>) = items.forEach(::saveOpportunity)

    fun countOpportunities(): Int = db.readableDatabase.rawQuery("SELECT COUNT(*) FROM opportunities WHERE eligibility_status='ELIGIBLE'", null).use { c -> if (c.moveToFirst()) c.getInt(0) else 0 }

    fun totalVerifiedEarningsUsd(): Double = db.readableDatabase.rawQuery("SELECT COALESCE(SUM(gross_usd - fee_usd),0) FROM earnings", null).use { c -> if (c.moveToFirst()) c.getDouble(0) else 0.0 }

    fun saveWallet(wallet: WalletDestination) {
        db.writableDatabase.execSQL("UPDATE wallets SET active=0 WHERE active=1")
        val values = ContentValues().apply {
            put("address", wallet.address)
            put("network", wallet.network)
            put("asset", wallet.asset)
            put("active", 1)
        }
        db.writableDatabase.insert("wallets", null, values)
    }

    fun getActiveWallet(): WalletDestination? = db.readableDatabase.rawQuery("SELECT address,network,asset FROM wallets WHERE active=1 ORDER BY id DESC LIMIT 1", null).use { c ->
        if (!c.moveToFirst()) return null
        WalletDestination(c.getString(0), c.getString(1), c.getString(2))
    }

    fun log(level: String, message: String) {
        val v = ContentValues().apply {
            put("timestamp", Instant.now().toString())
            put("level", level)
            put("message", message)
        }
        db.writableDatabase.insert("logs", null, v)
    }

    fun generateId(): String = UUID.randomUUID().toString()
}
