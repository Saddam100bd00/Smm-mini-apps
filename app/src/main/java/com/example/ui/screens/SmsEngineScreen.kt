package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Sms
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.engine.SmsParser
import com.example.ui.MainViewModel
import com.example.ui.components.MethodBadge
import com.example.ui.theme.DarkNavyBorder
import com.example.ui.theme.DarkNavyCard
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.theme.StatusSuccess
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun SmsEngineScreen(
    viewModel: MainViewModel
) {
    val smsLogs by viewModel.smsLogs.collectAsState()

    var testSender by remember { mutableStateOf("bKash") }
    var testBody by remember {
        mutableStateOf(
            "You have received Tk 350.00 from 01712345678. Fee Tk 0.00. Balance Tk 3,450.00. TrxID BKA8921J92 at 26/09/2026 17:15"
        )
    }
    var parseFeedback by remember { mutableStateOf<String?>(null) }

    val liveParsed = remember(testSender, testBody) {
        SmsParser.parse(testSender, testBody)
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("sms_engine_screen")
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Spacer(modifier = Modifier.height(8.dp))
            // Information Card on SIM auto-verification
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .background(EmeraldPrimary.copy(alpha = 0.15f), RoundedCornerShape(10.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Default.Sms, contentDescription = "SMS", tint = EmeraldPrimary)
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = "অটোমেটিক SMS ভেরিফিকেশন ইঞ্জিন",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                            Text(
                                text = "সিম থেকে রিয়েল-টাইম SMS পড়ে ট্রানজেকশন অটো ভেরিফাই হয়",
                                fontSize = 11.sp,
                                color = Color.Gray
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = "এই অ্যাপটি আপনার বিকাশ/নগদ সিম চালিত ফোনে চালু রাখলে, পেমেন্ট আসার সাথে সাথে সিস্টেম TrxID ও টাকার পরিমাণ স্বয়ংক্রিয়ভাবে পড়ে আপনার ওয়েবসাইটে ইনস্ট্যান্ট নোটিফিকেশন পাঠিয়ে দিবে!",
                        fontSize = 11.sp,
                        color = Color(0xFFB0BEC5),
                        lineHeight = 16.sp
                    )
                }
            }
        }

        item {
            // Interactive Sandbox Simulator
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "SMS রিসিভ ও পার্সিং ল্যাব (টেস্ট করুন)",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = EmeraldPrimary
                    )

                    // Template Presets
                    Text("রেডিমেড টেমপ্লেট বেছে নিন:", fontSize = 11.sp, color = Color.Gray)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        val templates = listOf(
                            Triple(
                                "বিকাশ SMS",
                                "bKash",
                                "You have received Tk 350.00 from 01712345678. Fee Tk 0.00. Balance Tk 3,450.00. TrxID BKA8921J92 at 26/09/2026 17:15"
                            ),
                            Triple(
                                "নগদ SMS",
                                "NAGAD",
                                "Received Tk 200.00 from 01911223344. Ref diamond. TxnID: 7JF82491DK. Balance: Tk 1,500.00 at 26/09/2026 17:20"
                            ),
                            Triple(
                                "রকেট SMS",
                                "16216",
                                "Tk500.00 received from 018123456789. TxnId: RCK9921443. New balance: Tk 2,100.00."
                            ),
                            Triple(
                                "উপায় SMS",
                                "UPAY",
                                "Received Tk 120.00 from 01612345678. Fee Tk 0.00. Trx ID UP992182."
                            )
                        )
                        items(templates) { (title, sender, text) ->
                            FilterChip(
                                selected = testBody == text,
                                onClick = {
                                    testSender = sender
                                    testBody = text
                                    parseFeedback = null
                                },
                                label = { Text(title, fontSize = 11.sp) }
                            )
                        }
                    }

                    // Sender
                    Text("প্রেরক (SMS Sender):", fontSize = 11.sp, color = Color.Gray)
                    OutlinedTextField(
                        value = testSender,
                        onValueChange = { testSender = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = RoundedCornerShape(8.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = EmeraldPrimary,
                            unfocusedBorderColor = DarkNavyBorder
                        )
                    )

                    // SMS Body
                    Text("SMS টেক্সট:", fontSize = 11.sp, color = Color.Gray)
                    OutlinedTextField(
                        value = testBody,
                        onValueChange = { testBody = it },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 4,
                        shape = RoundedCornerShape(8.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = EmeraldPrimary,
                            unfocusedBorderColor = DarkNavyBorder
                        )
                    )

                    // Real-time parsed preview
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFF090E17), RoundedCornerShape(8.dp))
                            .padding(10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(text = "ইঞ্জিন দ্বারা পার্স করা রেজাল্ট:", fontSize = 10.sp, color = Color.Gray)
                            Text(
                                text = "মাধ্যম: ${liveParsed.provider} | টাকা: ৳${liveParsed.amount} | TrxID: ${liveParsed.trxId.ifBlank { "পাওয়া যায়নি" }}",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = EmeraldPrimary
                            )
                        }
                    }

                    // Simulate Button
                    Button(
                        onClick = {
                            viewModel.simulateSms(testSender, testBody) { success, msg ->
                                parseFeedback = msg
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(46.dp)
                            .testTag("simulate_sms_button"),
                        colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Icon(Icons.Default.PlayArrow, contentDescription = null, tint = Color.Black, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("SMS প্রসেস করুন ও অর্ডার ম্যাচ করান", color = Color.Black, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    }

                    parseFeedback?.let { feedback ->
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Color(0xFF0B2418), RoundedCornerShape(8.dp))
                                .padding(10.dp)
                        ) {
                            Text(text = feedback, fontSize = 11.sp, color = StatusSuccess)
                        }
                    }
                }
            }
        }

        item {
            Text(
                text = "রিসিভ হওয়া SMS হিস্ট্রি (${smsLogs.size}টি)",
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
        }

        if (smsLogs.isEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
                ) {
                    Text(
                        text = "এখনো কোনো SMS রিসিভ হয়নি। উপরের টেস্ট ল্যাব থেকে 'SMS প্রসেস করুন' চাপুন।",
                        fontSize = 11.sp,
                        color = Color.Gray,
                        modifier = Modifier.padding(16.dp)
                    )
                }
            }
        } else {
            items(smsLogs, key = { it.id }) { log ->
                val dateFormat = remember { SimpleDateFormat("hh:mm a, dd MMM", Locale.getDefault()) }
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                MethodBadge(method = log.parsedProvider)
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(text = "৳ ${log.parsedAmount}", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color.White)
                            }
                            if (log.isMatched) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.CheckCircle, contentDescription = null, tint = StatusSuccess, modifier = Modifier.size(12.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("অর্ডারে ম্যাচড", fontSize = 10.sp, color = StatusSuccess)
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(6.dp))
                        Text(text = log.body, fontSize = 11.sp, color = Color.LightGray)

                        Spacer(modifier = Modifier.height(6.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(text = "TrxID: ${log.parsedTrxId}", fontSize = 10.sp, color = Color(0xFF64B5F6))
                            Text(text = dateFormat.format(Date(log.timestamp)), fontSize = 10.sp, color = Color.Gray)
                        }
                    }
                }
            }
        }

        item {
            Spacer(modifier = Modifier.height(80.dp))
        }
    }
}
