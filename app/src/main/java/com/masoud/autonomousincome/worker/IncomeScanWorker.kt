package com.masoud.autonomousincome.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.masoud.autonomousincome.BuildConfig
import com.masoud.autonomousincome.data.AppDatabase
import com.masoud.autonomousincome.data.IncomeRepository
import com.masoud.autonomousincome.engine.MysteriumNodeProvider
import com.masoud.autonomousincome.engine.OpportunityEngine
import com.masoud.autonomousincome.engine.ProviderRegistry
import com.masoud.autonomousincome.engine.RemoteOpportunityProvider

class IncomeScanWorker(appContext: Context, workerParams: WorkerParameters) : CoroutineWorker(appContext, workerParams) {
    override suspend fun doWork(): Result {
        val repository = IncomeRepository(AppDatabase(applicationContext))
        val registry = ProviderRegistry(
            listOf(
                RemoteOpportunityProvider(),
                MysteriumNodeProvider(baseUrl = BuildConfig.BACKEND_BASE_URL)
            )
        )
        return try {
            OpportunityEngine(repository, registry).scan()
            Result.success()
        } catch (t: Throwable) {
            repository.log("ERROR", "Background scan failed: ${t.message}")
            Result.retry()
        }
    }
}
