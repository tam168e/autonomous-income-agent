package com.masoud.autonomousincome.engine

class ProviderRegistry(private val providers: List<IncomeProvider> = emptyList()) {
    fun all(): List<IncomeProvider> = providers
    fun get(providerId: String): IncomeProvider? = providers.firstOrNull { it.id == providerId }

    fun productionProviders(): List<IncomeProvider> = providers.filter {
        it.executionMode == ExecutionMode.TASK
    }

    fun persistentProviders(): List<IncomeProvider> = providers.filter {
        it.executionMode == ExecutionMode.PERSISTENT
    }
}
