package com.masoud.autonomousincome.engine

import com.google.gson.Gson
import com.google.gson.JsonObject
import com.masoud.autonomousincome.BuildConfig
import com.masoud.autonomousincome.domain.EligibilityStatus
import com.masoud.autonomousincome.domain.Opportunity
import com.masoud.autonomousincome.domain.RiskLevel
import com.masoud.autonomousincome.domain.WalletDestination
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.time.Instant

class MysteriumNodeProvider(
    private val client: OkHttpClient = OkHttpClient(),
    private val baseUrl: String = BuildConfig.BACKEND_BASE_URL
) : IncomeProvider, PersistentIncomeProvider {
    override val id: String = "mysterium-node"
    override val name: String = "Mysterium Node"
    override val executionMode: ExecutionMode = ExecutionMode.PERSISTENT

    private val gson = Gson()
    private val mediaType = "application/json; charset=utf-8".toMediaType()

    override suspend fun checkEligibility(): EligibilityStatus {
        val status = runCatching { getRuntimeStatus() }.getOrElse {
            return EligibilityStatus.USER_ACTION_REQUIRED
        }
        if (!status.healthy) return EligibilityStatus.USER_ACTION_REQUIRED
        if (status.countryConfirmationRequired) return EligibilityStatus.USER_ACTION_REQUIRED
        if (status.identityId.isNullOrBlank()) return EligibilityStatus.USER_ACTION_REQUIRED
        if (!status.registrationStatus.equals("Registered", ignoreCase = true)) {
            return EligibilityStatus.USER_ACTION_REQUIRED
        }
        if (status.activeServices == 0) return EligibilityStatus.USER_ACTION_REQUIRED
        if (status.supportedCountries.isEmpty()) return EligibilityStatus.USER_ACTION_REQUIRED
        return EligibilityStatus.ELIGIBLE
    }

    override suspend fun discover(): List<Opportunity> {
        val request = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/opportunities")
            .get()
            .build()
        return client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Mysterium opportunity feed HTTP ${response.code}")
            val body = response.body?.string().orEmpty()
            gson.fromJson(body, Array<RemoteOpportunity>::class.java)?.map { it.toDomain() }.orEmpty()
                .filter { it.providerId == id }
        }
    }

    override suspend fun execute(opportunity: Opportunity): Result<String> =
        Result.failure(UnsupportedOperationException(
            "Mysterium is a persistent provider; income accrues while the node service is running."
        ))

    override suspend fun verifyPayment(paymentId: String): Result<Double> =
        postForAmount(
            "/providers/$id/verify-payment",
            mapOf("paymentId" to paymentId)
        )

    override suspend fun requestWithdrawal(
        amountUsd: Double,
        wallet: WalletDestination
    ): Result<String> =
        postForReference(
            "/providers/$id/withdraw",
            mapOf(
                "amountUsd" to amountUsd,
                "wallet" to wallet
            )
        )

    override suspend fun getPersistentStatus(): Result<PersistentProviderStatus> =
        runCatching {
            val status = getRuntimeStatus()
            PersistentProviderStatus(
                providerId = id,
                healthy = status.healthy,
                summary = when {
                    !status.healthy -> "Mysterium backend/node is not healthy."
                    status.countryConfirmationRequired -> "Country confirmation is required."
                    status.activeServices == 0 -> "No active Mysterium provider service is running."
                    else -> "Running " + status.activeServices + " service(s); balance " + status.balanceMyst + " MYST."
                }
            )
        }

    suspend fun getRuntimeStatus(): RuntimeStatus {
        val request = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/providers/$id/status")
            .get()
            .build()
        return client.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) error("Mysterium status HTTP ${response.code}")
            gson.fromJson(body, RuntimeStatus::class.java)
        }
    }

    private fun postForAmount(path: String, payload: Map<String, Any>): Result<Double> =
        runCatching {
            val request = Request.Builder()
                .url(baseUrl.trimEnd('/') + path)
                .post(gson.toJson(payload).toRequestBody(mediaType))
                .build()
            client.newCall(request).execute().use { response ->
                val body = response.body?.string().orEmpty()
                val json = gson.fromJson(body, JsonObject::class.java)
                if (!response.isSuccessful || json?.get("success")?.asBoolean != true) {
                    error(json?.get("error")?.asString ?: "Provider verification failed")
                }
                json.getAsJsonObject("data")?.get("netUsd")?.asDouble
                    ?: json.getAsJsonObject("data")?.get("grossUsd")?.asDouble
                    ?: error("Provider returned no verified USD amount")
            }
        }

    private fun postForReference(path: String, payload: Map<String, Any>): Result<String> =
        runCatching {
            val request = Request.Builder()
                .url(baseUrl.trimEnd('/') + path)
                .post(gson.toJson(payload).toRequestBody(mediaType))
                .build()
            client.newCall(request).execute().use { response ->
                val body = response.body?.string().orEmpty()
                val json = gson.fromJson(body, JsonObject::class.java)
                if (!response.isSuccessful || json?.get("success")?.asBoolean != true) {
                    error(json?.get("error")?.asString ?: "Provider withdrawal failed")
                }
                json.getAsJsonObject("data")?.get("providerReference")?.asString
                    ?: error("Provider returned no withdrawal reference")
            }
        }

    data class RuntimeStatus(
        val providerId: String = "mysterium-node",
        val healthy: Boolean = false,
        val identityId: String? = null,
        val registrationStatus: String? = null,
        val activeServices: Int = 0,
        val balanceMyst: Double = 0.0,
        val earningsTotalMyst: Double = 0.0,
        val quality: Double = 0.0,
        val onlinePercent: Double = 0.0,
        val supportedCountries: List<String> = emptyList(),
        val countryConfirmationRequired: Boolean = true
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
