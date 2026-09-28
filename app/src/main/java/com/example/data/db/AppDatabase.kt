package com.example.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.data.model.MerchantConfigEntity
import com.example.data.model.PaymentMethodEntity
import com.example.data.model.SmsLogEntity
import com.example.data.model.TransactionEntity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@Database(
    entities = [
        PaymentMethodEntity::class,
        TransactionEntity::class,
        MerchantConfigEntity::class,
        SmsLogEntity::class
    ],
    version = 2,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {

    abstract fun paymentDao(): PaymentDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "autopay_bd_database"
                )
                    .fallbackToDestructiveMigration()
                    .addCallback(DatabaseCallback())
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }

    private class DatabaseCallback : RoomDatabase.Callback() {
        override fun onCreate(db: SupportSQLiteDatabase) {
            super.onCreate(db)
            INSTANCE?.let { database ->
                CoroutineScope(Dispatchers.IO).launch {
                    populateInitialData(database.paymentDao())
                }
            }
        }

        private suspend fun populateInitialData(dao: PaymentDao) {
            val initialMethods = listOf(
                PaymentMethodEntity(
                    id = "bkash",
                    name = "বিকাশ (bKash)",
                    number = "01712345678",
                    type = "PERSONAL",
                    feePercent = 0.0,
                    instructions = "বিকাশ অ্যাপ অথবা *247# ডায়াল করে Send Money করুন। সফল হলে প্রাপ্ত TrxID নিচে লিখুন।",
                    isEnabled = true
                ),
                PaymentMethodEntity(
                    id = "nagad",
                    name = "নগদ (Nagad)",
                    number = "01912345678",
                    type = "PERSONAL",
                    feePercent = 0.0,
                    instructions = "নগদ অ্যাপ অথবা *167# ডায়াল করে Send Money করুন। সফল হলে প্রাপ্ত TxnID নিচে লিখুন।",
                    isEnabled = true
                ),
                PaymentMethodEntity(
                    id = "rocket",
                    name = "রকেট (Rocket)",
                    number = "018123456789",
                    type = "PERSONAL",
                    feePercent = 0.0,
                    instructions = "রকেট অ্যাপ বা *322# ডায়াল করে Send Money করুন। ১২ ডিজিটের একাউন্ট নম্বরে পাঠান।",
                    isEnabled = true
                ),
                PaymentMethodEntity(
                    id = "upay",
                    name = "উপায় (Upay)",
                    number = "01612345678",
                    type = "PERSONAL",
                    feePercent = 0.0,
                    instructions = "উপায় অ্যাপ বা *268# দিয়ে Send Money সম্পন্ন করুন এবং TrxID দিন।",
                    isEnabled = true
                )
            )
            dao.insertMethods(initialMethods)

            dao.insertOrUpdateConfig(
                MerchantConfigEntity(
                    id = 1,
                    businessName = "মাই অটো পেমেন্ট গেটওয়ে",
                    apiKey = "live_pub_bd89329048a1",
                    secretKey = "live_sec_ff4982a178bc9910",
                    defaultWebhookUrl = "https://example.com/api/autopay-webhook.php",
                    autoApproveSms = true,
                    soundNotification = true
                )
            )

            // Add a few realistic starter transactions for dashboard view
            val now = System.currentTimeMillis()
            dao.insertTransaction(
                TransactionEntity(
                    orderId = "TOPUP-1029",
                    websiteName = "Diamond Bazar BD",
                    method = "BKASH",
                    amount = 450.0,
                    feeAmount = 0.0,
                    totalAmount = 450.0,
                    customerPhone = "01788990011",
                    customerName = "Tanvir Ahmed",
                    trxId = "BLA99K872Q",
                    status = "COMPLETED",
                    matchedSmsSnippet = "You have received Tk 450.00 from 01788990011. Fee Tk 0.00. Balance Tk 450.00. TrxID BLA99K872Q",
                    webhookUrl = "https://diamondbazarbd.com/api/ipn.php",
                    webhookStatus = "DELIVERED",
                    webhookResponseCode = 200,
                    createdAt = now - 1800000,
                    verifiedAt = now - 1795000
                )
            )

            dao.insertTransaction(
                TransactionEntity(
                    orderId = "PUBG-MATCH-55",
                    websiteName = "Esports Arena BD",
                    method = "NAGAD",
                    amount = 120.0,
                    feeAmount = 0.0,
                    totalAmount = 120.0,
                    customerPhone = "01955667788",
                    customerName = "Rakib Hasan",
                    trxId = "9JF843HDK9",
                    status = "COMPLETED",
                    matchedSmsSnippet = "Received Tk 120.00 from 01955667788. Ref . TxnID 9JF843HDK9",
                    webhookUrl = "https://esportsbd.com/webhook",
                    webhookStatus = "DELIVERED",
                    webhookResponseCode = 200,
                    createdAt = now - 7200000,
                    verifiedAt = now - 7192000
                )
            )

            dao.insertTransaction(
                TransactionEntity(
                    orderId = "SHOP-4091",
                    websiteName = "BD Gamers Hub",
                    method = "ROCKET",
                    amount = 890.0,
                    feeAmount = 0.0,
                    totalAmount = 890.0,
                    customerPhone = "01811223344",
                    customerName = "Shakil Hossain",
                    trxId = "RCK9921443",
                    status = "PENDING",
                    matchedSmsSnippet = "",
                    webhookUrl = "https://gamershub.com/api/payment_callback",
                    webhookStatus = "NOT_SET",
                    webhookResponseCode = 0,
                    createdAt = now - 600000,
                    verifiedAt = null
                )
            )
        }
    }
}
