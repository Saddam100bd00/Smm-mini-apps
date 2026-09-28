package com.example.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "payment_methods")
data class PaymentMethodEntity(
    @PrimaryKey
    val id: String, // "bkash", "nagad", "rocket", "upay"
    val name: String, // "বিকাশ", "নগদ", "রকেট", "উপায়"
    val number: String,
    val type: String = "PERSONAL", // "PERSONAL", "MERCHANT", "AGENT"
    val feePercent: Double = 0.0,
    val instructions: String = "",
    val isEnabled: Boolean = true,
    val qrData: String = "",
    val customLogoUrl: String = ""
)

@Entity(tableName = "transactions")
data class TransactionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val orderId: String,
    val websiteName: String = "Top-up & Gaming Shop",
    val method: String, // "BKASH", "NAGAD", "ROCKET", "UPAY"
    val amount: Double,
    val feeAmount: Double = 0.0,
    val totalAmount: Double,
    val customerPhone: String = "",
    val customerName: String = "",
    val trxId: String = "",
    val status: String = "PENDING", // "PENDING", "COMPLETED", "REJECTED"
    val matchedSmsSnippet: String = "",
    val webhookUrl: String = "",
    val webhookStatus: String = "NOT_SET", // "DELIVERED", "FAILED", "PENDING", "NOT_SET"
    val webhookResponseCode: Int = 0,
    val createdAt: Long = System.currentTimeMillis(),
    val verifiedAt: Long? = null
)

@Entity(tableName = "merchant_config")
data class MerchantConfigEntity(
    @PrimaryKey
    val id: Int = 1,
    val businessName: String = "AutoPay BD Merchant",
    val apiKey: String = "live_pub_84f932e18d9b",
    val secretKey: String = "live_sec_77c290a14fe8b6",
    val defaultWebhookUrl: String = "https://mysite.com/api/payment-webhook.php",
    val autoApproveSms: Boolean = true,
    val soundNotification: Boolean = true,
    val siteName: String = "DREAMTOPUP",
    val siteLogoUrl: String = "",
    val serviceRunning: Boolean = true
)

@Entity(tableName = "sms_logs")
data class SmsLogEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val sender: String,
    val body: String,
    val parsedProvider: String, // "BKASH", "NAGAD", "ROCKET", "UPAY", "UNKNOWN"
    val parsedAmount: Double,
    val parsedTrxId: String,
    val parsedSenderPhone: String,
    val isMatched: Boolean = false,
    val timestamp: Long = System.currentTimeMillis()
)
