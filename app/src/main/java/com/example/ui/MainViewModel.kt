package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.model.MerchantConfigEntity
import com.example.data.model.PaymentMethodEntity
import com.example.data.model.SmsLogEntity
import com.example.data.model.TransactionEntity
import com.example.data.repository.PaymentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class DashboardStats(
    val totalCollected: Double = 0.0,
    val completedCount: Int = 0,
    val pendingCount: Int = 0,
    val failedCount: Int = 0,
    val successRate: Int = 100
)

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = PaymentRepository(application)

    init {
        viewModelScope.launch {
            repository.ensureDefaultMethods()
        }
    }

    val methods: StateFlow<List<PaymentMethodEntity>> = repository.allMethods
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val merchantConfig: StateFlow<MerchantConfigEntity?> = repository.merchantConfig
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    val smsLogs: StateFlow<List<SmsLogEntity>> = repository.smsLogs
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Transactions and filtering
    private val _searchQuery = MutableStateFlow("")
    val searchQuery = _searchQuery.asStateFlow()

    private val _statusFilter = MutableStateFlow("ALL") // "ALL", "PENDING", "COMPLETED", "REJECTED"
    val statusFilter = _statusFilter.asStateFlow()

    private val _methodFilter = MutableStateFlow("ALL") // "ALL", "BKASH", "NAGAD", "ROCKET", "UPAY"
    val methodFilter = _methodFilter.asStateFlow()

    val rawTransactions: StateFlow<List<TransactionEntity>> = repository.allTransactions
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val filteredTransactions: StateFlow<List<TransactionEntity>> = combine(
        rawTransactions,
        _searchQuery,
        _statusFilter,
        _methodFilter
    ) { txList, query, status, method ->
        txList.filter { tx ->
            val matchesQuery = query.isBlank() ||
                    tx.orderId.contains(query, ignoreCase = true) ||
                    tx.customerPhone.contains(query, ignoreCase = true) ||
                    tx.trxId.contains(query, ignoreCase = true) ||
                    tx.websiteName.contains(query, ignoreCase = true)

            val matchesStatus = status == "ALL" || tx.status.equals(status, ignoreCase = true)
            val matchesMethod = method == "ALL" || tx.method.equals(method, ignoreCase = true)

            matchesQuery && matchesStatus && matchesMethod
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val stats: StateFlow<DashboardStats> = rawTransactions.combine(rawTransactions) { list, _ ->
        val completed = list.filter { it.status == "COMPLETED" }
        val pending = list.filter { it.status == "PENDING" }
        val failed = list.filter { it.status == "REJECTED" }

        val totalAmount = completed.sumOf { it.totalAmount }
        val totalDecided = completed.size + failed.size
        val rate = if (totalDecided > 0) ((completed.size.toDouble() / totalDecided) * 100).toInt() else 100

        DashboardStats(
            totalCollected = totalAmount,
            completedCount = completed.size,
            pendingCount = pending.size,
            failedCount = failed.size,
            successRate = rate
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), DashboardStats())

    // Feedback message state
    private val _snackbarMessage = MutableStateFlow<String?>(null)
    val snackbarMessage = _snackbarMessage.asStateFlow()

    // Live transaction popup alert state
    private val _latestTransactionAlert = MutableStateFlow<TransactionEntity?>(null)
    val latestTransactionAlert = _latestTransactionAlert.asStateFlow()

    fun triggerTransactionAlert(tx: TransactionEntity) {
        _latestTransactionAlert.value = tx
    }

    fun dismissTransactionAlert() {
        _latestTransactionAlert.value = null
    }

    fun generateDailyReport(): String {
        val completed = rawTransactions.value.filter { it.status == "COMPLETED" }
        val totalAmount = completed.sumOf { it.totalAmount }
        val bkashAmount = completed.filter { it.method.equals("BKASH", ignoreCase = true) }.sumOf { it.totalAmount }
        val nagadAmount = completed.filter { it.method.equals("NAGAD", ignoreCase = true) }.sumOf { it.totalAmount }
        val rocketAmount = completed.filter { it.method.equals("ROCKET", ignoreCase = true) }.sumOf { it.totalAmount }
        val upayAmount = completed.filter { it.method.equals("UPAY", ignoreCase = true) }.sumOf { it.totalAmount }

        val dateFormat = java.text.SimpleDateFormat("dd MMMM yyyy, hh:mm a", java.util.Locale("bn", "BD"))
        val nowStr = dateFormat.format(java.util.Date())

        return """
            📊 AutoPay BD • পেমেন্ট কালেকশন রিপোর্ট
            📅 তারিখ: $nowStr
            ━━━━━━━━━━━━━━━━━━━━
            💰 মোট কালেকশন: ৳ ${String.format(java.util.Locale.US, "%.2f", totalAmount)}
            ✅ সফল অর্ডার: ${completed.size} টি
            
            💳 মেথড ভিত্তিক কালেকশন:
            • 🔴 বিকাশ (bKash): ৳ ${String.format(java.util.Locale.US, "%.2f", bkashAmount)}
            • 🟠 নগদ (Nagad): ৳ ${String.format(java.util.Locale.US, "%.2f", nagadAmount)}
            • 🟣 রকেট (Rocket): ৳ ${String.format(java.util.Locale.US, "%.2f", rocketAmount)}
            • 🟡 উপায় (Upay): ৳ ${String.format(java.util.Locale.US, "%.2f", upayAmount)}
            ━━━━━━━━━━━━━━━━━━━━
            🚀 AutoPay BD Gateway • সক্রিয় ও সুরক্ষিত
        """.trimIndent()
    }

    fun showMessage(msg: String) {
        _snackbarMessage.value = msg
    }

    fun clearMessage() {
        _snackbarMessage.value = null
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun setStatusFilter(status: String) {
        _statusFilter.value = status
    }

    fun setMethodFilter(method: String) {
        _methodFilter.value = method
    }

    // Wallet settings actions
    fun updateMethod(method: PaymentMethodEntity) {
        viewModelScope.launch {
            repository.saveMethod(method)
            showMessage("${method.name} সেটিংস সফলভাবে আপডেট হয়েছে")
        }
    }

    fun addNewMethod(method: PaymentMethodEntity) {
        viewModelScope.launch {
            repository.saveMethod(method)
            showMessage("নতুন পেমেন্ট মেথড '${method.name}' সফলভাবে যুক্ত হয়েছে!")
        }
    }

    fun deleteMethod(id: String) {
        viewModelScope.launch {
            repository.deleteMethod(id)
            showMessage("পেমেন্ট মেথড মুছে ফেলা হয়েছে")
        }
    }

    fun restoreDefaultMethods() {
        viewModelScope.launch {
            repository.restoreDefaultMethods()
            showMessage("বিকাশ, নগদ, রকেট এবং উপায় মেথড সফলভাবে রিস্টোর করা হয়েছে!")
        }
    }

    fun updateConfig(config: MerchantConfigEntity) {
        viewModelScope.launch {
            repository.updateMerchantConfig(config)
            showMessage("মার্চেন্ট ও এপিআই সেটিংস সংরক্ষিত হয়েছে")
        }
    }

    fun regenerateApiKeys() {
        viewModelScope.launch {
            repository.regenerateApiKeys()
            showMessage("নতুন API Key এবং Secret Key তৈরি করা হয়েছে!")
        }
    }

    // Transaction actions
    fun markTransactionStatus(id: Long, status: String) {
        viewModelScope.launch {
            repository.markTransactionStatus(id, status)
            val text = if (status == "COMPLETED") "অর্ডার সফলভাবে ভেরিফাই ও এপ্রুভ করা হয়েছে" else "অর্ডার বাতিল করা হয়েছে"
            showMessage(text)
        }
    }

    fun deleteTransaction(id: Long) {
        viewModelScope.launch {
            repository.deleteTransaction(id)
            showMessage("ট্রানজেকশন মুছে ফেলা হয়েছে")
        }
    }

    fun resendWebhook(txId: Long) {
        viewModelScope.launch {
            val (code, _) = repository.resendWebhook(txId)
            if (code in 200..299) {
                showMessage("ওয়েবহুক সফলভাবে সাইটে পাঠানো হয়েছে (HTTP $code)")
            } else {
                showMessage("ওয়েবহুক পাঠাতে সমস্যা হয়েছে (Code: $code)")
            }
        }
    }

    // Checkout Simulator Action
    fun createCheckoutInvoice(
        amount: Double,
        orderId: String,
        websiteName: String,
        customerPhone: String,
        customerName: String,
        method: String,
        webhookUrl: String,
        onCreated: (Long) -> Unit
    ) {
        viewModelScope.launch {
            val id = repository.createTransaction(
                orderId = orderId,
                websiteName = websiteName,
                method = method,
                amount = amount,
                customerPhone = customerPhone,
                customerName = customerName,
                webhookUrl = webhookUrl
            )
            onCreated(id)
        }
    }

    fun verifyStrictPayment(
        txId: Long,
        trxId: String,
        onResult: (com.example.engine.VerificationResult) -> Unit
    ) {
        viewModelScope.launch {
            val result = repository.verifyStrictPayment(txId, trxId)
            if (result is com.example.engine.VerificationResult.Success) {
                result.transaction?.let { tx ->
                    _latestTransactionAlert.value = tx
                }
            }
            onResult(result)
        }
    }

    fun submitTrxId(txId: Long, trxId: String, onComplete: (Boolean) -> Unit) {
        viewModelScope.launch {
            val autoApproved = repository.submitCustomerTrxId(txId, trxId)
            if (autoApproved) {
                val tx = rawTransactions.value.find { it.id == txId }
                if (tx != null) {
                    _latestTransactionAlert.value = tx.copy(status = "COMPLETED", trxId = trxId)
                }
            }
            onComplete(autoApproved)
        }
    }

    // Service controls for background running with screen off
    val isServiceRunning: StateFlow<Boolean> = com.example.service.PaymentForegroundService.isRunning

    fun toggleService(enable: Boolean) {
        val app = getApplication<Application>()
        if (enable) {
            com.example.service.PaymentForegroundService.startService(app)
        } else {
            com.example.service.PaymentForegroundService.stopService(app)
        }
        viewModelScope.launch {
            val current = merchantConfig.value
            if (current != null) {
                repository.updateMerchantConfig(current.copy(serviceRunning = enable))
            }
        }
    }

    fun updateSiteSettings(siteName: String, siteLogoUrl: String) {
        viewModelScope.launch {
            val current = merchantConfig.value
            if (current != null) {
                repository.updateMerchantConfig(
                    current.copy(
                        siteName = siteName.trim(),
                        siteLogoUrl = siteLogoUrl.trim()
                    )
                )
            }
        }
    }

    // SMS Simulation action
    fun simulateSms(sender: String, body: String, onResult: (Boolean, String) -> Unit) {
        viewModelScope.launch {
            val res = repository.simulateIncomingSms(sender, body)
            onResult(res.first, res.second)
        }
    }
}
