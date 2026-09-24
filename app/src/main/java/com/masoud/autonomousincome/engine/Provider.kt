package com.masoud.autonomousincome.engine

import com.masoud.autonomousincome.domain.EligibilityStatus
import com.masoud.autonomousincome.domain.Opportunity

interface IncomeProvider {
    val id: String
    val name: String
    suspend fun discover(): List<Opportunity>
    suspend fun checkEligibility(): EligibilityStatus
    suspend fun execute(opportunity: Opportunity): Result<String>
    suspend fun verifyPayment(paymentId: String): Result<Double>
    suspend fun requestWithdrawal(amountUsd: Double): Result<String>
}
