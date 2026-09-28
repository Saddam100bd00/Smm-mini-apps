package com.example.engine

import android.content.Context
import android.util.Log
import com.example.data.db.AppDatabase
import com.example.data.model.SmsLogEntity
import com.example.data.model.TransactionEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

sealed class VerificationResult {
    data class Success(val message: String, val transaction: TransactionEntity) : VerificationResult()
    data class DuplicateTrxId(val message: String) : VerificationResult()
    data class InvalidTrxId(val message: String) : VerificationResult()
    data class AmountMismatch(val expectedAmount: Double, val receivedAmount: Double, val message: String) : VerificationResult()
}

object PaymentVerificationEngine {
    private const val TAG = "AutoPayEngine"

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    /**
     * Strict verification as requested:
     * - Checks if TrxID is duplicate (already completed)
     * - Checks if TrxID exists in received SMS logs
     * - Checks if received SMS amount EXACTLY matches the set account order amount (more or less fails)
     * - If everything is correct -> Successful verification and webhook dispatched!
     */
    suspend fun verifyCustomerSubmission(
        context: Context,
        transactionId: Long,
        enteredTrxId: String
    ): VerificationResult = withContext(Dispatchers.IO) {
        val database = AppDatabase.getInstance(context)
        val dao = database.paymentDao()
        val tx = dao.getTransactionById(transactionId)
            ?: return@withContext VerificationResult.InvalidTrxId("অর্ডার পাওয়া যায়নি!")

        val cleanTrxId = enteredTrxId.trim().uppercase()
        if (cleanTrxId.length < 5) {
            return@withContext VerificationResult.InvalidTrxId("ভুল ট্রানজেকশন আইডি! অনুগ্রহ করে সঠিক TrxID লিখুন।")
        }

        // 1. DUPLICATE CHECK: Did someone already use this TrxID in a completed transaction?
        val duplicateCount = dao.countCompletedByTrxId(cleanTrxId)
        if (duplicateCount > 0) {
            return@withContext VerificationResult.DuplicateTrxId(
                "❌ ভেরিফিকেশন ব্যর্থ! একই ট্রানজেকশন আইডি ($cleanTrxId) ইতিমধ্যে ব্যবহার করা হয়েছে। নতুন TrxID দিন।"
            )
        }

        // 2. CHECK IF SMS LOG HAS THIS TrxID
        val sms = dao.findSmsByTrxId(cleanTrxId)
        if (sms == null) {
            return@withContext VerificationResult.InvalidTrxId(
                "❌ ট্রানজেকশন আইডি ভুল অথবা খুঁজে পাওয়া যায়নি! সিস্টেমে ($cleanTrxId) এর কোনো পেমেন্ট এসএমএস আসেনি।"
            )
        }

        // 3. CHECK EXACT AMOUNT MATCH (e.g. set 50, but sent 40 or 60 -> FAIL)
        val expectedAmount = tx.amount
        val receivedAmount = sms.parsedAmount
        if (Math.abs(expectedAmount - receivedAmount) > 0.01) {
            return@withContext VerificationResult.AmountMismatch(
                expectedAmount = expectedAmount,
                receivedAmount = receivedAmount,
                message = "❌ টাকার পরিমাণ মিল নেই! নির্ধারিত টাকার পরিমাণ ছিল ৳${expectedAmount} কিন্তু পাঠানো হয়েছে ৳${receivedAmount}। বেশি বা কম টাকা গ্রহণযোগ্য নয়, ভেরিফিকেশন ব্যর্থ!"
            )
        }

        // 4. EVERYTHING IS CORRECT -> Mark SUCCESS!
        val completedTx = tx.copy(
            status = "COMPLETED",
            trxId = cleanTrxId,
            matchedSmsSnippet = sms.body,
            verifiedAt = System.currentTimeMillis()
        )
        dao.updateTransaction(completedTx)
        dao.markSmsMatched(sms.id)

        // Trigger Webhook
        val config = dao.getMerchantConfigOnce()
        val targetWebhook = if (completedTx.webhookUrl.isNotBlank()) completedTx.webhookUrl else (config?.defaultWebhookUrl ?: "")
        if (targetWebhook.isNotBlank() && config != null) {
            dispatchWebhook(context, completedTx, targetWebhook, config.secretKey)
        }

        return@withContext VerificationResult.Success(
            message = "✅ পেমেন্ট সফল ও ভেরিফাইড! ট্রানজেকশন আইডি ($cleanTrxId) এবং টাকার পরিমাণ (৳${expectedAmount}) সঠিকভাবে মিলেছে।",
            transaction = completedTx
        )
    }

    /**
     * Process an incoming SMS text and auto-verify any matching pending transaction.
     */
    suspend fun processIncomingSms(
        context: Context,
        sender: String,
        body: String
    ): Pair<ParsedPaymentSms, TransactionEntity?> = withContext(Dispatchers.IO) {
        val database = AppDatabase.getInstance(context)
        val dao = database.paymentDao()

        val parsed = SmsParser.parse(sender, body)

        // Save raw SMS log
        val logId = dao.insertSmsLog(
            SmsLogEntity(
                sender = sender,
                body = body,
                parsedProvider = parsed.provider,
                parsedAmount = parsed.amount,
                parsedTrxId = parsed.trxId,
                parsedSenderPhone = parsed.senderPhone,
                isMatched = false,
                timestamp = System.currentTimeMillis()
            )
        )

        if (!parsed.isPaymentReceived && parsed.trxId.isEmpty()) {
            return@withContext Pair(parsed, null)
        }

        // Sync parsed payment SMS directly to Firebase Firestore collection "sms_payments"
        // This enables instant auto-verification for Telegram bots, websites, and external backends!
        if (parsed.trxId.isNotEmpty()) {
            try {
                val firestore = com.google.firebase.firestore.FirebaseFirestore.getInstance()
                val cleanTrx = parsed.trxId.trim().uppercase()
                val docData = hashMapOf(
                    "trx_id" to cleanTrx,
                    "amount" to parsed.amount,
                    "provider" to parsed.provider,
                    "sender_phone" to parsed.senderPhone,
                    "raw_sms" to body,
                    "created_at" to com.google.firebase.Timestamp.now(),
                    "used" to false
                )
                firestore.collection("sms_payments").document(cleanTrx).set(docData)
                Log.d(TAG, "Synced SMS to Firestore: sms_payments/$cleanTrx (Amount: ${parsed.amount})")
            } catch (e: Exception) {
                Log.e(TAG, "Firestore sync failed: ${e.message}")
            }
        }

        // Webhook trigger: Automatically dispatch parsed SMS to merchant default Webhook URL (e.g. Telegram Bot on Render)
        val config = dao.getMerchantConfigOnce()
        val defaultWebhookUrl = config?.defaultWebhookUrl ?: ""
        if (defaultWebhookUrl.isNotBlank() && parsed.trxId.isNotEmpty()) {
            try {
                dispatchSmsWebhook(context, parsed, body, defaultWebhookUrl, config?.secretKey ?: "")
            } catch (e: Exception) {
                Log.e(TAG, "Auto webhook dispatch error: ${e.message}")
            }
        }

        // Try matching: 1. By TrxID
        var matchedTx: TransactionEntity? = null
        if (parsed.trxId.isNotEmpty()) {
            matchedTx = dao.findTransactionByTrxId(parsed.trxId)
        }

        // 2. If not found by TrxID, try matching by pending provider + exact amount
        if (matchedTx == null && parsed.amount > 0 && parsed.provider != "UNKNOWN") {
            matchedTx = dao.findPendingMatchingPayment(parsed.provider, parsed.amount)
        }

        if (matchedTx != null && matchedTx.status != "COMPLETED") {
            // Update matched transaction
            val updatedTx = matchedTx.copy(
                status = "COMPLETED",
                trxId = if (matchedTx.trxId.isEmpty()) parsed.trxId else matchedTx.trxId,
                matchedSmsSnippet = body,
                verifiedAt = System.currentTimeMillis()
            )
            dao.updateTransaction(updatedTx)
            dao.markSmsMatched(logId)

            // Trigger Webhook callback
            val config = dao.getMerchantConfigOnce()
            val targetWebhookUrl = if (updatedTx.webhookUrl.isNotBlank()) {
                updatedTx.webhookUrl
            } else {
                config?.defaultWebhookUrl ?: ""
            }

            if (targetWebhookUrl.isNotBlank()) {
                dispatchWebhook(context, updatedTx, targetWebhookUrl, config?.secretKey ?: "")
            }

            return@withContext Pair(parsed, updatedTx)
        }

        return@withContext Pair(parsed, null)
    }

    /**
     * Send Webhook notification to external merchant website (e.g. Diamond top-up site, PUBG tournament site)
     */
    suspend fun dispatchWebhook(
        context: Context,
        transaction: TransactionEntity,
        webhookUrl: String,
        secretKey: String
    ): Pair<Int, String> = withContext(Dispatchers.IO) {
        val dao = AppDatabase.getInstance(context).paymentDao()

        try {
            val payload = JSONObject().apply {
                put("event", "PAYMENT_COMPLETED")
                put("status", "SUCCESS")
                put("order_id", transaction.orderId)
                put("amount", transaction.amount)
                put("total_amount", transaction.totalAmount)
                put("method", transaction.method)
                put("trx_id", transaction.trxId)
                put("customer_phone", transaction.customerPhone)
                put("customer_name", transaction.customerName)
                put("website_name", transaction.websiteName)
                put("timestamp", transaction.verifiedAt ?: System.currentTimeMillis())
                put("token", secretKey)
            }

            val requestBody = payload.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
            val request = Request.Builder()
                .url(webhookUrl)
                .post(requestBody)
                .addHeader("X-AutoPay-Signature", secretKey)
                .addHeader("User-Agent", "AutoPay-BD-Gateway/1.0")
                .build()

            val response = httpClient.newCall(request).execute()
            val code = response.code
            val bodyString = response.body?.string() ?: ""

            // Update transaction webhook status
            val updated = transaction.copy(
                webhookStatus = if (response.isSuccessful) "DELIVERED" else "FAILED",
                webhookResponseCode = code,
                webhookUrl = webhookUrl
            )
            dao.updateTransaction(updated)

            Log.d(TAG, "Webhook delivered to $webhookUrl with code $code")
            return@withContext Pair(code, bodyString)
        } catch (e: Exception) {
            Log.e(TAG, "Webhook dispatch failed: ${e.message}")
            val updated = transaction.copy(
                webhookStatus = "FAILED",
                webhookResponseCode = 500,
                webhookUrl = webhookUrl
            )
            dao.updateTransaction(updated)
            return@withContext Pair(500, e.localizedMessage ?: "Network error")
        }
    }

    /**
     * Dispatch newly received SMS directly to merchant Webhook (Render Telegram Bot, website, etc.)
     */
    suspend fun dispatchSmsWebhook(
        context: Context,
        parsed: ParsedPaymentSms,
        rawSms: String,
        webhookUrl: String,
        secretKey: String
    ): Pair<Int, String> = withContext(Dispatchers.IO) {
        if (webhookUrl.isBlank()) return@withContext Pair(0, "No Webhook URL configured")
        try {
            val payload = JSONObject().apply {
                put("event", "SMS_RECEIVED")
                put("trx_id", parsed.trxId.trim().uppercase())
                put("amount", parsed.amount)
                put("provider", parsed.provider)
                put("sender_phone", parsed.senderPhone)
                put("raw_sms", rawSms)
                put("timestamp", System.currentTimeMillis())
                put("token", secretKey)
            }

            val requestBody = payload.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
            val request = Request.Builder()
                .url(webhookUrl)
                .post(requestBody)
                .addHeader("X-AutoPay-Signature", secretKey)
                .addHeader("User-Agent", "AutoPay-BD-Gateway/1.0")
                .build()

            val response = httpClient.newCall(request).execute()
            val code = response.code
            val bodyString = response.body?.string() ?: ""
            Log.d(TAG, "Sms Webhook delivered to $webhookUrl with code $code: $bodyString")
            return@withContext Pair(code, bodyString)
        } catch (e: Exception) {
            Log.e(TAG, "Sms Webhook dispatch failed: ${e.message}")
            return@withContext Pair(500, e.localizedMessage ?: "Network error")
        }
    }
}
