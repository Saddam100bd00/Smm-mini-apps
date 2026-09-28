package com.example.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.data.model.MerchantConfigEntity
import com.example.data.model.PaymentMethodEntity
import com.example.data.model.SmsLogEntity
import com.example.data.model.TransactionEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface PaymentDao {

    // --- Payment Methods ---
    @Query("SELECT * FROM payment_methods")
    fun getAllMethods(): Flow<List<PaymentMethodEntity>>

    @Query("SELECT * FROM payment_methods WHERE isEnabled = 1")
    fun getActiveMethods(): Flow<List<PaymentMethodEntity>>

    @Query("SELECT * FROM payment_methods WHERE id = :id LIMIT 1")
    suspend fun getMethodById(id: String): PaymentMethodEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMethods(methods: List<PaymentMethodEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdateMethod(method: PaymentMethodEntity)

    @Update
    suspend fun updateMethod(method: PaymentMethodEntity)

    @Query("DELETE FROM payment_methods WHERE id = :id")
    suspend fun deleteMethod(id: String)

    @Query("SELECT COUNT(*) FROM payment_methods")
    suspend fun getMethodsCount(): Int

    // --- Transactions ---
    @Query("SELECT * FROM transactions ORDER BY createdAt DESC")
    fun getAllTransactions(): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE status = :status ORDER BY createdAt DESC")
    fun getTransactionsByStatus(status: String): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE id = :id LIMIT 1")
    suspend fun getTransactionById(id: Long): TransactionEntity?

    @Query("SELECT * FROM transactions WHERE orderId = :orderId LIMIT 1")
    suspend fun getTransactionByOrderId(orderId: String): TransactionEntity?

    @Query("SELECT * FROM transactions WHERE LOWER(trxId) = LOWER(:trxId) LIMIT 1")
    suspend fun findTransactionByTrxId(trxId: String): TransactionEntity?

    @Query("SELECT COUNT(*) FROM transactions WHERE LOWER(trxId) = LOWER(:trxId) AND status = 'COMPLETED'")
    suspend fun countCompletedByTrxId(trxId: String): Int

    @Query("SELECT * FROM sms_logs WHERE UPPER(parsedTrxId) = UPPER(:trxId) ORDER BY timestamp DESC LIMIT 1")
    suspend fun findSmsByTrxId(trxId: String): SmsLogEntity?

    @Query("SELECT * FROM sms_logs WHERE isMatched = 0 AND UPPER(parsedTrxId) = UPPER(:trxId) ORDER BY timestamp DESC LIMIT 1")
    suspend fun findUnmatchedSmsByTrxId(trxId: String): SmsLogEntity?

    @Query("""
        SELECT * FROM transactions 
        WHERE status = 'PENDING' 
        AND method = :provider 
        AND (amount = :amount OR totalAmount = :amount)
        ORDER BY createdAt DESC LIMIT 1
    """)
    suspend fun findPendingMatchingPayment(provider: String, amount: Double): TransactionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTransaction(transaction: TransactionEntity): Long

    @Update
    suspend fun updateTransaction(transaction: TransactionEntity)

    @Query("DELETE FROM transactions WHERE id = :id")
    suspend fun deleteTransaction(id: Long)

    @Query("DELETE FROM transactions")
    suspend fun clearAllTransactions()

    // --- Merchant Config ---
    @Query("SELECT * FROM merchant_config WHERE id = 1 LIMIT 1")
    fun getMerchantConfig(): Flow<MerchantConfigEntity?>

    @Query("SELECT * FROM merchant_config WHERE id = 1 LIMIT 1")
    suspend fun getMerchantConfigOnce(): MerchantConfigEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdateConfig(config: MerchantConfigEntity)

    // --- SMS Logs ---
    @Query("SELECT * FROM sms_logs ORDER BY timestamp DESC")
    fun getAllSmsLogs(): Flow<List<SmsLogEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSmsLog(log: SmsLogEntity): Long

    @Query("UPDATE sms_logs SET isMatched = 1 WHERE id = :logId")
    suspend fun markSmsMatched(logId: Long)
}
