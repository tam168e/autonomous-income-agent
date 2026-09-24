package com.masoud.autonomousincome.engine

class ProviderRegistry(private val providers: List<IncomeProvider> = emptyList()) {
    fun all(): List<IncomeProvider> = providers
}
