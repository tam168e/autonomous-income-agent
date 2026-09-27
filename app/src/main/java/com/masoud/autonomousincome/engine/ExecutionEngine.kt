package com.masoud.autonomousincome.engine

import com.masoud.autonomousincome.data.IncomeRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class ExecutionEngine(private val repository: IncomeRepository, private val registry: ProviderRegistry) {
    suspend fun runBestAvailable(): Result<String> = withContext(Dispatchers.IO) {
        // Intentionally refuses to execute without a real verified task provider.
        repository.log("INFO", "Execution cycle skipped: no executable task provider is configured")
        Result.failure(IllegalStateException("No executable task provider configured"))
    }

    suspend fun monitorPersistentProviders(): Result<Int> = withContext(Dispatchers.IO) {
        var monitored = 0
        registry.persistentProviders().forEach { provider ->
            monitored += 1
            val result = if (provider is PersistentIncomeProvider) {
                provider.getPersistentStatus()
            } else {
                Result.failure(IllegalStateException("Provider does not implement persistent monitoring"))
            }

            result.onSuccess { status ->
                repository.log(
                    if (status.healthy) "INFO" else "WARN",
                    "Persistent provider " + status.providerId + ": " + status.summary
                )
            }.onFailure { error ->
                repository.log("WARN", "Persistent provider " + provider.id + " monitoring failed: " + error.message)
            }
        }
        Result.success(monitored)
    }
}
