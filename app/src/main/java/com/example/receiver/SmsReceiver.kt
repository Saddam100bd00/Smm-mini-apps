package com.example.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.example.engine.PaymentVerificationEngine
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SmsReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "AutoPaySmsReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {
            val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            if (messages.isNullOrEmpty()) return

            val sender = messages[0]?.originatingAddress ?: "UNKNOWN"
            val fullBody = StringBuilder()
            for (msg in messages) {
                fullBody.append(msg.messageBody)
            }
            val body = fullBody.toString()

            Log.d(TAG, "SMS Received from: $sender, content: $body")

            // Process with engine in CoroutineScope
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val result = PaymentVerificationEngine.processIncomingSms(
                        context = context.applicationContext,
                        sender = sender,
                        body = body
                    )
                    if (result.second != null) {
                        Log.d(TAG, "Payment matched and auto-verified! TrxID: ${result.first.trxId}")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error handling incoming SMS: ${e.message}")
                }
            }
        }
    }
}
