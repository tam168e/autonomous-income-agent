package com.masoud.autonomousincome.engine

import com.masoud.autonomousincome.data.IncomeRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class ExecutionEngine(private val repository: IncomeRepository, private val registry: ProviderRegistry) {
    suspend fun runBestAvailable(): Result<String> = withContext(Dispatchers.IO) {
        // Intentionally refuses to execute without a real verified provider.
        repository.log("INFO", "Execution cycle skipped: no production provider adapter is configured")
        Result.failure(IllegalStateException("No production provider adapter configured"))
    }
}
