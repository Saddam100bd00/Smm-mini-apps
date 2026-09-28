package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.engine.SmsParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class ExampleRobolectricTest {

    @Test
    fun `read string from context`() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val appName = context.getString(R.string.app_name)
        assertEquals("AutoPay BD", appName)
    }

    @Test
    fun `test bkash sms parsing`() {
        val sms = "You have received Tk 450.00 from 01788990011. Fee Tk 0.00. Balance Tk 450.00. TrxID BLA99K872Q at 26/09/2026"
        val parsed = SmsParser.parse("bKash", sms)
        assertEquals("BKASH", parsed.provider)
        assertEquals(450.0, parsed.amount, 0.01)
        assertEquals("BLA99K872Q", parsed.trxId)
        assertTrue(parsed.isPaymentReceived)
    }

    @Test
    fun `test nagad sms parsing`() {
        val sms = "Received Tk 120.00 from 01955667788. Ref topup. TxnID 9JF843HDK9. Balance: Tk 1,200.00"
        val parsed = SmsParser.parse("NAGAD", sms)
        assertEquals("NAGAD", parsed.provider)
        assertEquals(120.0, parsed.amount, 0.01)
        assertEquals("9JF843HDK9", parsed.trxId)
        assertTrue(parsed.isPaymentReceived)
    }

    @Test
    fun `test rocket sms parsing`() {
        val sms = "Tk500.00 received from 018123456789. TxnId: RCK9921443. New balance: Tk 2,100.00."
        val parsed = SmsParser.parse("16216", sms)
        assertEquals("ROCKET", parsed.provider)
        assertEquals(500.0, parsed.amount, 0.01)
        assertEquals("RCK9921443", parsed.trxId)
    }
}
