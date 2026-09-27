package com.masoud.autonomousincome.wallet

import com.masoud.autonomousincome.domain.WalletDestination

object WalletValidator {
    private val evm = Regex("^0x[a-fA-F0-9]{40}$")
    private val tron = Regex("^T[1-9A-HJ-NP-Za-km-z]{33}$")

    fun validate(wallet: WalletDestination): Result<Unit> {
        if (wallet.address.isBlank()) return Result.failure(IllegalArgumentException("Wallet address is empty"))
        if (wallet.network.isBlank()) return Result.failure(IllegalArgumentException("Network is empty"))
        if (wallet.asset.isBlank()) return Result.failure(IllegalArgumentException("Asset is empty"))

        if (wallet.network.uppercase() in setOf("ETHEREUM", "POLYGON", "BSC", "ARBITRUM", "OPTIMISM", "BASE", "TRON")) {
            if (wallet.network.uppercase() == "TRON" && !tron.matches(wallet.address)) {
                return Result.failure(IllegalArgumentException("Invalid TRON address format"))
            }
            if (wallet.network.uppercase() != "TRON" && !evm.matches(wallet.address)) {
                return Result.failure(IllegalArgumentException("Invalid EVM address"))
            }
        }
        return Result.success(Unit)
    }
}
