package com.masoud.autonomousincome.engine

import com.masoud.autonomousincome.domain.EligibilityStatus
import com.masoud.autonomousincome.domain.Opportunity
import com.masoud.autonomousincome.domain.WalletDestination

enum class ExecutionMode { TASK, PERSISTENT }

data class PersistentProviderStatus(
    val providerId: String,
    val healthy: Boolean,
    val summary: String
)

interface PersistentIncomeProvider {
    suspend fun getPersistentStatus(): Result<PersistentProviderStatus>
}

interface IncomeProvider {
    val id: String
    val name: String
    val executionMode: ExecutionMode
        get() = ExecutionMode.TASK

    suspend fun discover(): List<Opportunity>
    suspend fun checkEligibility(): EligibilityStatus
    suspend fun execute(opportunity: Opportunity): Result<String>
    suspend fun verifyPayment(paymentId: String): Result<Double>
    suspend fun requestWithdrawal(amountUsd: Double, wallet: WalletDestination): Result<String>
}
