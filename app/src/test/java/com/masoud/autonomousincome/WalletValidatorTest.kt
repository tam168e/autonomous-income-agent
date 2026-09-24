package com.masoud.autonomousincome

import com.masoud.autonomousincome.domain.WalletDestination
import com.masoud.autonomousincome.wallet.WalletValidator
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WalletValidatorTest {
    @Test fun validPolygonEvmWalletAccepted() {
        val wallet = WalletDestination("0x1111111111111111111111111111111111111111", "Polygon", "USDT")
        assertTrue(WalletValidator.validate(wallet).isSuccess)
    }

    @Test fun invalidPolygonAddressRejected() {
        val wallet = WalletDestination("bad", "Polygon", "USDT")
        assertFalse(WalletValidator.validate(wallet).isSuccess)
    }
}
