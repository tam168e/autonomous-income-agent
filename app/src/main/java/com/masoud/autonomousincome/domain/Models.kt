package com.masoud.autonomousincome.domain

import java.time.Instant

enum class RiskLevel { LOW, MEDIUM, HIGH }
enum class EligibilityStatus {
    ELIGIBLE, CONDITIONALLY_ELIGIBLE, UNAVAILABLE_IN_COUNTRY, USER_ACTION_REQUIRED, REJECTED
}

enum class TaskStatus { QUEUED, RUNNING, COMPLETED, FAILED, PAUSED, USER_ACTION_REQUIRED }

data class Opportunity(
    val id: String,
    val providerId: String,
    val name: String,
    val description: String,
    val estimatedHourlyUsd: Double,
    val feeUsd: Double,
    val minimumWithdrawalUsd: Double,
    val requiresCapital: Boolean,
    val requiresKyc: Boolean,
    val automationAllowed: Boolean,
    val riskLevel: RiskLevel,
    val eligibilityStatus: EligibilityStatus,
    val sourceUrl: String,
    val lastVerifiedAt: Instant?,
    val score: Double = 0.0
)

data class WalletDestination(
    val address: String,
    val network: String,
    val asset: String
)

data class EarningsRecord(
    val id: String,
    val opportunityId: String,
    val grossUsd: Double,
    val feeUsd: Double,
    val paymentId: String,
    val verifiedAt: Instant
)
