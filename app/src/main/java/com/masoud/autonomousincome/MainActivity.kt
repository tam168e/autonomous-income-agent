package com.masoud.autonomousincome

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.masoud.autonomousincome.data.AppDatabase
import com.masoud.autonomousincome.data.IncomeRepository
import com.masoud.autonomousincome.domain.WalletDestination
import com.masoud.autonomousincome.wallet.WalletValidator
import com.masoud.autonomousincome.worker.IncomeScanWorker
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    private lateinit var repository: IncomeRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = IncomeRepository(AppDatabase(this))
        scheduleBackgroundScan()

        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    DashboardScreen(repository)
                }
            }
        }
    }

    private fun scheduleBackgroundScan() {
        val request = PeriodicWorkRequestBuilder<IncomeScanWorker>(6, TimeUnit.HOURS).build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "income-opportunity-scan",
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )
    }
}

@Composable
private fun DashboardScreen(repository: IncomeRepository) {
    var address by remember { mutableStateOf(repository.getActiveWallet()?.address.orEmpty()) }
    var network by remember { mutableStateOf(repository.getActiveWallet()?.network ?: "Polygon") }
    var asset by remember { mutableStateOf(repository.getActiveWallet()?.asset ?: "USDT") }
    var message by remember { mutableStateOf("Ready. Mysterium persistent adapter is configured; live earnings depend on the local node and backend state.") }
    var earnings by remember { mutableStateOf(repository.totalVerifiedEarningsUsd()) }

    Column(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Autonomous Income Agent", style = MaterialTheme.typography.headlineSmall)
        Text("Verified earnings: $${"%.2f".format(earnings)}")
        Text("Eligible opportunities: ${repository.countOpportunities()}")

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Wallet destination", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(address, { address = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Address") })
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    OutlinedTextField(network, { network = it }, modifier = Modifier.weight(1f), label = { Text("Network") })
                    OutlinedTextField(asset, { asset = it }, modifier = Modifier.weight(1f), label = { Text("Asset") })
                }
                Button(onClick = {
                    val wallet = WalletDestination(address.trim(), network.trim(), asset.trim())
                    val result = WalletValidator.validate(wallet)
                    if (result.isSuccess) {
                        repository.saveWallet(wallet)
                        message = "Wallet saved."
                    } else {
                        message = result.exceptionOrNull()?.message ?: "Invalid wallet"
                    }
                }) { Text("Save wallet") }
            }
        }

        Spacer(Modifier.height(4.dp))
        Text(message)
        Text("Background discovery is scheduled every 6 hours. The app will not invent earnings or bypass provider restrictions.")
    }
}
