package com.masoud.autonomousincome.engine

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.masoud.autonomousincome.BuildConfig
import com.masoud.autonomousincome.domain.EligibilityStatus
import com.masoud.autonomousincome.domain.Opportunity
import com.masoud.autonomousincome.domain.RiskLevel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.time.Instant

class RemoteOpportunityProvider(
    private val client: OkHttpClient = OkHttpClient(),
    private val baseUrl: String = BuildConfig.BACKEND_BASE_URL
) : IncomeProvider {
    override val id: String = "remote-feed"
    override val name: String = "Verified Opportunity Feed"
    private val gson = Gson()

    override suspend fun discover(): List<Opportunity> = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("${baseUrl.trimEnd('/')}/opportunities").get().build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Opportunity feed HTTP ${response.code}")
            val body = response.body?.string().orEmpty()
            val type = object : TypeToken<List<RemoteOpportunity>>() {}.type
            gson.fromJson<List<RemoteOpportunity>>(body, type).map { it.toDomain() }
        }
    }

    override suspend fun checkEligibility(): EligibilityStatus = EligibilityStatus.ELIGIBLE

    override suspend fun execute(opportunity: Opportunity): Result<String> = Result.failure(
        UnsupportedOperationException("No executable provider is configured for ${opportunity.providerId}")
    )

    override suspend fun verifyPayment(paymentId: String): Result<Double> = Result.failure(
        UnsupportedOperationException("Payment verification belongs to a concrete provider adapter")
    )

    override suspend fun requestWithdrawal(amountUsd: Double): Result<String> = Result.failure(
        UnsupportedOperationException("Withdrawal belongs to a concrete provider adapter")
    )

    private data class RemoteOpportunity(
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
        val riskLevel: String,
        val eligibilityStatus: String,
        val sourceUrl: String,
        val lastVerifiedAt: String
    ) {
        fun toDomain() = Opportunity(
            id = id,
            providerId = providerId,
            name = name,
            description = description,
            estimatedHourlyUsd = estimatedHourlyUsd,
            feeUsd = feeUsd,
            minimumWithdrawalUsd = minimumWithdrawalUsd,
            requiresCapital = requiresCapital,
            requiresKyc = requiresKyc,
            automationAllowed = automationAllowed,
            riskLevel = runCatching { RiskLevel.valueOf(riskLevel.uppercase()) }.getOrDefault(RiskLevel.HIGH),
            eligibilityStatus = runCatching { EligibilityStatus.valueOf(eligibilityStatus.uppercase()) }.getOrDefault(EligibilityStatus.REJECTED),
            sourceUrl = sourceUrl,
            lastVerifiedAt = runCatching { Instant.parse(lastVerifiedAt) }.getOrNull()
        )
    }
}
