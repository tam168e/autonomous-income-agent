package com.masoud.autonomousincome.engine

import com.masoud.autonomousincome.data.IncomeRepository
import com.masoud.autonomousincome.domain.EligibilityStatus
import com.masoud.autonomousincome.domain.Opportunity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.max

class OpportunityEngine(private val repository: IncomeRepository, private val registry: ProviderRegistry) {
    suspend fun scan(): List<Opportunity> = withContext(Dispatchers.IO) {
        val all = registry.all().flatMap { provider ->
            val eligibility = provider.checkEligibility()
            if (eligibility == EligibilityStatus.UNAVAILABLE_IN_COUNTRY || eligibility == EligibilityStatus.REJECTED) emptyList()
            else provider.discover().map { it.copy(eligibilityStatus = eligibility) }
        }
        val scored = all.map { score(it) }
        repository.saveOpportunities(scored)
        repository.log("INFO", "Opportunity scan completed: ${scored.size} candidates")
        scored
    }

    private fun score(o: Opportunity): Opportunity {
        val riskPenalty = when (o.riskLevel.name) { "LOW" -> 0.1; "MEDIUM" -> 0.35; else -> 0.8 }
        val capitalPenalty = if (o.requiresCapital) 1000.0 else 0.0
        val automationPenalty = if (o.automationAllowed) 0.0 else 1000.0
        val base = max(0.0, o.estimatedHourlyUsd - o.feeUsd)
        val score = (base * (1.0 - riskPenalty)) - capitalPenalty - automationPenalty
        return o.copy(score = score)
    }
}
