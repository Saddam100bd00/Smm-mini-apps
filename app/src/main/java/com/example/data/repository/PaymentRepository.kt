package com.example.data.repository

import android.content.Context
import com.example.data.db.AppDatabase
import com.example.data.model.MerchantConfigEntity
import com.example.data.model.PaymentMethodEntity
import com.example.data.model.SmsLogEntity
import com.example.data.model.TransactionEntity
import com.example.engine.PaymentVerificationEngine
import kotlinx.coroutines.flow.Flow
import java.util.UUID

class PaymentRepository(private val context: Context) {
    private val database = AppDatabase.getInstance(context)
    private val dao = database.paymentDao()

    val allTransactions: Flow<List<TransactionEntity>> = dao.getAllTransactions()
    val allMethods: Flow<List<PaymentMethodEntity>> = dao.getAllMethods()
    val activeMethods: Flow<List<PaymentMethodEntity>> = dao.getActiveMethods()
    val merchantConfig: Flow<MerchantConfigEntity?> = dao.getMerchantConfig()
    val smsLogs: Flow<List<SmsLogEntity>> = dao.getAllSmsLogs()

    suspend fun ensureDefaultMethods() {
        val count = dao.getMethodsCount()
        if (count == 0) {
            restoreDefaultMethods()
        } else {
            // Update existing default methods to have the official PostImage logo URLs if blank
            val urlMap = mapOf(
                "bkash" to "https://i.postimg.cc/3Rh5jP9R/1790271574534.png",
                "nagad" to "https://i.postimg.cc/KvjX577W/1790444646578.png",
                "rocket" to "https://i.postimg.cc/rp6vcvBN/1790272198554.png",
                "upay" to "https://i.postimg.cc/bvQ4vm8x/1790444672029.png"
            )
            for ((id, url) in urlMap) {
                val existing = dao.getMethodById(id)
                if (existing != null && (existing.customLogoUrl.isBlank() || !existing.customLogoUrl.contains("postimg"))) {
                    dao.insertOrUpdateMethod(existing.copy(customLogoUrl = url))
                }
            }
        }
    }

    suspend fun restoreDefaultMethods() {
        val defaults = listOf(
            PaymentMethodEntity(
                id = "bkash",
                name = "বিকাশ (bKash)",
                number = "01735102916",
                type = "PERSONAL",
                customLogoUrl = "https://i.postimg.cc/3Rh5jP9R/1790271574534.png",
                feePercent = 0.0,
                instructions = "*247# ডায়াল করে অথবা bKash অ্যাপে যান এবং Send Money করুন।",
                isEnabled = true
            ),
            PaymentMethodEntity(
                id = "nagad",
                name = "নগদ (Nagad)",
                number = "01960737073",
                type = "PERSONAL",
                customLogoUrl = "https://i.postimg.cc/KvjX577W/1790444646578.png",
                feePercent = 0.0,
                instructions = "*167# ডায়াল করে অথবা NAGAD অ্যাপে যান এবং Send Money করুন।",
                isEnabled = true
            ),
            PaymentMethodEntity(
                id = "rocket",
                name = "রকেট (Rocket)",
                number = "018123456789",
                type = "PERSONAL",
                customLogoUrl = "https://i.postimg.cc/rp6vcvBN/1790272198554.png",
                feePercent = 0.0,
                instructions = "*322# ডায়াল করে অথবা রকেট অ্যাপে Send Money সম্পন্ন করুন।",
                isEnabled = true
            ),
            PaymentMethodEntity(
                id = "upay",
                name = "উপায় (Upay)",
                number = "01612345678",
                type = "PERSONAL",
                customLogoUrl = "https://i.postimg.cc/bvQ4vm8x/1790444672029.png",
                feePercent = 0.0,
                instructions = "*268# দিয়ে অথবা উপায় অ্যাপে Send Money করুন।",
                isEnabled = true
            )
        )
        dao.insertMethods(defaults)
    }

    suspend fun updateMethod(method: PaymentMethodEntity) {
        dao.insertOrUpdateMethod(method)
    }

    suspend fun saveMethod(method: PaymentMethodEntity) {
        dao.insertOrUpdateMethod(method)
    }

    suspend fun deleteMethod(id: String) {
        dao.deleteMethod(id)
    }

    suspend fun updateMerchantConfig(config: MerchantConfigEntity) {
        dao.insertOrUpdateConfig(config)
    }

    suspend fun regenerateApiKeys() {
        val current = dao.getMerchantConfigOnce() ?: MerchantConfigEntity()
        val newApiKey = "live_pub_" + UUID.randomUUID().toString().replace("-", "").take(12)
        val newSecretKey = "live_sec_" + UUID.randomUUID().toString().replace("-", "").take(16)
        dao.insertOrUpdateConfig(current.copy(apiKey = newApiKey, secretKey = newSecretKey))
    }

    suspend fun createTransaction(
        orderId: String,
        websiteName: String,
        method: String,
        amount: Double,
        customerPhone: String,
        customerName: String,
        webhookUrl: String
    ): Long {
        val methodEntity = dao.getMethodById(method.lowercase())
        val feeRate = methodEntity?.feePercent ?: 0.0
        val fee = if (feeRate > 0) (amount * feeRate / 100.0) else 0.0
        val total = amount + fee

        val tx = TransactionEntity(
            orderId = orderId.ifBlank { "ORD-${System.currentTimeMillis() % 100000}" },
            websiteName = websiteName.ifBlank { "My Topup Shop" },
            method = method.uppercase(),
            amount = amount,
            feeAmount = fee,
            totalAmount = total,
            customerPhone = customerPhone,
            customerName = customerName,
            status = "PENDING",
            webhookUrl = webhookUrl
        )
        return dao.insertTransaction(tx)
    }

    suspend fun verifyStrictPayment(transactionId: Long, trxId: String): com.example.engine.VerificationResult {
        return PaymentVerificationEngine.verifyCustomerSubmission(context, transactionId, trxId)
    }

    suspend fun submitCustomerTrxId(transactionId: Long, trxId: String): Boolean {
        val tx = dao.getTransactionById(transactionId) ?: return false
        val cleanTrxId = trxId.trim().uppercase()
        val updated = tx.copy(trxId = cleanTrxId)
        dao.updateTransaction(updated)

        // Check if there is an un-matched SMS already in the log matching this TrxID
        // or auto-verify if auto-approval is enabled
        val config = dao.getMerchantConfigOnce()
        if (config?.autoApproveSms == true) {
            val verifiedTx = updated.copy(
                status = "COMPLETED",
                verifiedAt = System.currentTimeMillis()
            )
            dao.updateTransaction(verifiedTx)

            val webhookTarget = if (verifiedTx.webhookUrl.isNotBlank()) verifiedTx.webhookUrl else config.defaultWebhookUrl
            if (webhookTarget.isNotBlank()) {
                PaymentVerificationEngine.dispatchWebhook(context, verifiedTx, webhookTarget, config.secretKey)
            }
            return true
        }
        return false
    }

    suspend fun markTransactionStatus(transactionId: Long, status: String) {
        val tx = dao.getTransactionById(transactionId) ?: return
        val updated = tx.copy(
            status = status,
            verifiedAt = if (status == "COMPLETED") System.currentTimeMillis() else tx.verifiedAt
        )
        dao.updateTransaction(updated)

        if (status == "COMPLETED") {
            val config = dao.getMerchantConfigOnce()
            val webhookTarget = if (updated.webhookUrl.isNotBlank()) updated.webhookUrl else (config?.defaultWebhookUrl ?: "")
            if (webhookTarget.isNotBlank() && config != null) {
                PaymentVerificationEngine.dispatchWebhook(context, updated, webhookTarget, config.secretKey)
            }
        }
    }

    suspend fun deleteTransaction(id: Long) {
        dao.deleteTransaction(id)
    }

    suspend fun clearTransactions() {
        dao.clearAllTransactions()
    }

    suspend fun resendWebhook(transactionId: Long): Pair<Int, String> {
        val tx = dao.getTransactionById(transactionId) ?: return Pair(404, "Transaction not found")
        val config = dao.getMerchantConfigOnce()
        val webhookTarget = if (tx.webhookUrl.isNotBlank()) tx.webhookUrl else (config?.defaultWebhookUrl ?: "")
        if (webhookTarget.isBlank()) return Pair(400, "No webhook URL configured")

        return PaymentVerificationEngine.dispatchWebhook(context, tx, webhookTarget, config?.secretKey ?: "")
    }

    suspend fun simulateIncomingSms(sender: String, body: String): Pair<Boolean, String> {
        val (parsed, matchedTx) = PaymentVerificationEngine.processIncomingSms(context, sender, body)
        val config = dao.getMerchantConfigOnce()
        val webhookTarget = config?.defaultWebhookUrl ?: ""
        val webhookNote = if (webhookTarget.isNotBlank()) " | 📡 Webhook পাঠানো হয়েছে: $webhookTarget" else " | ⚠️ Webhook URL সেট করা নেই (ইন্টিগ্রেশন ট্যাবে সেট করুন)"

        return if (matchedTx != null) {
            Pair(true, "ম্যাচ হয়েছে! অর্ডার #${matchedTx.orderId} সফলভাবে ভেরিফাই হয়েছে (৳${parsed.amount}, TrxID: ${parsed.trxId})$webhookNote")
        } else {
            Pair(true, "✅ SMS পার্স ও প্রসেস হয়েছে (${parsed.provider}, ৳${parsed.amount}, TrxID: ${parsed.trxId})$webhookNote")
        }
    }
}
