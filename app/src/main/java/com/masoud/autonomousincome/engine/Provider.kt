package com.masoud.autonomousincome.engine

import com.masoud.autonomousincome.domain.EligibilityStatus
import com.masoud.autonomousincome.domain.Opportunity
import com.masoud.autonomousincome.domain.WalletDestination

enum class ExecutionMode { TASK, PERSISTENT }

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
