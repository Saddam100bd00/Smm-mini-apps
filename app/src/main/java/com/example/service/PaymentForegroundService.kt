package com.example.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.example.MainActivity
import com.example.R
import com.example.data.db.AppDatabase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class PaymentForegroundService : Service() {

    private var wakeLock: PowerManager.WakeLock? = null

    companion object {
        const val CHANNEL_ID = "autopay_gateway_channel"
        const val NOTIFICATION_ID = 1001

        const val ACTION_START = "com.example.service.ACTION_START"
        const val ACTION_STOP = "com.example.service.ACTION_STOP"

        private val _isRunning = MutableStateFlow(false)
        val isRunning = _isRunning.asStateFlow()

        fun startService(context: Context) {
            val intent = Intent(context, PaymentForegroundService::class.java).apply {
                action = ACTION_START
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stopService(context: Context) {
            val intent = Intent(context, PaymentForegroundService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                releaseWakeLock()
                _isRunning.value = false
                updateDbServiceState(false)
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_START, null -> {
                acquireWakeLock()
                _isRunning.value = true
                updateDbServiceState(true)
                val notification = buildNotification(
                    title = "AutoPay BD সার্ভিস সক্রিয় (রানিং)",
                    body = "স্ক্রিন অফ থাকলেও সার্বক্ষণিক SMS ভেরিফিকেশন চলছে..."
                )
                startForeground(NOTIFICATION_ID, notification)
            }
        }
        return START_STICKY
    }

    private fun acquireWakeLock() {
        try {
            if (wakeLock == null) {
                val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
                wakeLock = powerManager.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK,
                    "AutoPayBD::GatewayWakeLock"
                ).apply {
                    setReferenceCounted(false)
                    acquire()
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun releaseWakeLock() {
        try {
            wakeLock?.let {
                if (it.isHeld) {
                    it.release()
                }
            }
            wakeLock = null
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun updateDbServiceState(running: Boolean) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val dao = AppDatabase.getInstance(applicationContext).paymentDao()
                val config = dao.getMerchantConfigOnce()
                if (config != null) {
                    dao.insertOrUpdateConfig(config.copy(serviceRunning = running))
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun buildNotification(title: String, body: String): Notification {
        val openAppIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            openAppIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AutoPay Gateway Background Engine",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "সার্বক্ষণিক পেমেন্ট SMS রিসিভ ও ব্যাকগ্রাউন্ড ট্র্যাকিং চ্যানেল"
                setShowBadge(false)
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        releaseWakeLock()
        _isRunning.value = false
        updateDbServiceState(false)
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
