package com.masoud.autonomousincome.engine

import com.masoud.autonomousincome.domain.EligibilityStatus

data class ProviderEligibilityInput(
    val supportedCountries: Set<String>,
    val requiresKyc: Boolean,
    val automationAllowed: Boolean,
    val requiresCapital: Boolean
)

class CountryEligibilityEngine(private val userCountry: String = "Iran") {
    fun evaluate(input: ProviderEligibilityInput): EligibilityStatus {
        if (userCountry !in input.supportedCountries) return EligibilityStatus.UNAVAILABLE_IN_COUNTRY
        if (input.requiresCapital) return EligibilityStatus.REJECTED
        if (!input.automationAllowed) return EligibilityStatus.USER_ACTION_REQUIRED
        if (input.requiresKyc) return EligibilityStatus.CONDITIONALLY_ELIGIBLE
        return EligibilityStatus.ELIGIBLE
    }
}
