package com.example.engine

data class ParsedPaymentSms(
    val provider: String, // "BKASH", "NAGAD", "ROCKET", "UPAY", "UNKNOWN"
    val amount: Double,
    val senderPhone: String,
    val trxId: String,
    val isPaymentReceived: Boolean,
    val rawMessage: String
)

object SmsParser {

    fun parse(sender: String, body: String): ParsedPaymentSms {
        val normalizedSender = sender.uppercase()
        val text = body.trim()

        // 1. Detect Provider
        val provider = when {
            normalizedSender.contains("BKASH") || text.contains("bKash", ignoreCase = true) -> "BKASH"
            normalizedSender.contains("NAGAD") || text.contains("Nagad", ignoreCase = true) -> "NAGAD"
            normalizedSender.contains("16216") || normalizedSender.contains("ROCKET") || text.contains("Rocket", ignoreCase = true) || text.contains("DBBL", ignoreCase = true) -> "ROCKET"
            normalizedSender.contains("UPAY") || text.contains("Upay", ignoreCase = true) -> "UPAY"
            // Secondary heuristic based on keywords
            text.contains("TrxID", ignoreCase = true) -> "BKASH"
            text.contains("TxnID", ignoreCase = true) -> "NAGAD"
            else -> "UNKNOWN"
        }

        // 2. Check if it's an incoming payment / money received
        val isReceived = text.contains("received", ignoreCase = true) ||
                text.contains("Cash In", ignoreCase = true) ||
                text.contains("পেয়েছেন", ignoreCase = true)

        // 3. Extract Amount
        val amount = extractAmount(text)

        // 4. Extract Sender Phone
        val senderPhone = extractSenderPhone(text)

        // 5. Extract TrxID / TxnID
        val trxId = extractTrxId(text)

        return ParsedPaymentSms(
            provider = provider,
            amount = amount,
            senderPhone = senderPhone,
            trxId = trxId,
            isPaymentReceived = isReceived,
            rawMessage = body
        )
    }

    private fun extractAmount(text: String): Double {
        // Examples: "received Tk 500.00", "Tk 500.00 received", "Tk500 received", "Cash In Tk 250"
        val patterns = listOf(
            Regex("""(?:received|received payment|Cash In)\s*Tk\.?\s*([0-9,]+(?:\.[0-9]+)?)""", RegexOption.IGNORE_CASE),
            Regex("""Tk\.?\s*([0-9,]+(?:\.[0-9]+)?)\s*received""", RegexOption.IGNORE_CASE),
            Regex("""Tk\.?\s*([0-9,]+(?:\.[0-9]+)?)""", RegexOption.IGNORE_CASE)
        )

        for (pattern in patterns) {
            val match = pattern.find(text)
            if (match != null) {
                val rawNumber = match.groupValues[1].replace(",", "").trim()
                return rawNumber.toDoubleOrNull() ?: 0.0
            }
        }
        return 0.0
    }

    private fun extractSenderPhone(text: String): String {
        // Matches BD mobile numbers 01XXXXXXXXX or +8801XXXXXXXXX or 12 digit for Rocket
        val pattern = Regex("""(?:from\s*)(\+?8801[0-9]{9,10}|01[0-9]{9,10})""", RegexOption.IGNORE_CASE)
        val match = pattern.find(text)
        if (match != null) {
            var phone = match.groupValues[1].trim()
            if (phone.startsWith("+880")) {
                phone = phone.removePrefix("+88")
            }
            return phone
        }
        return ""
    }

    private fun extractTrxId(text: String): String {
        // Matches TrxID / TxnID: ABC123XYZ or 9JK38DK
        val patterns = listOf(
            Regex("""(?:TrxID|Trx ID|TrxId|TxnID|Txn ID|TxnId)\s*:?\s*([A-Za-z0-9]+)""", RegexOption.IGNORE_CASE),
            Regex("""(?:Trans ID|Transaction ID)\s*:?\s*([A-Za-z0-9]+)""", RegexOption.IGNORE_CASE)
        )

        for (pattern in patterns) {
            val match = pattern.find(text)
            if (match != null) {
                return match.groupValues[1].trim().uppercase()
            }
        }
        return ""
    }
}
