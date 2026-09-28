package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.Web
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.MainViewModel
import com.example.ui.theme.DarkNavyBorder
import com.example.ui.theme.DarkNavyCard
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.theme.NagadOrange

@Composable
fun IntegrationGuideScreen(
    viewModel: MainViewModel
) {
    val context = LocalContext.current
    val merchantConfig by viewModel.merchantConfig.collectAsState()

    var activeTab by remember { mutableIntStateOf(0) } // 0 = PHP, 1 = Node.js, 2 = HTML Embed, 3 = Python, 4 = Guide
    var webhookUrlInput by remember { mutableStateOf(merchantConfig?.defaultWebhookUrl ?: "") }

    val copyToClipboard: (String, String) -> Unit = { label, text ->
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        viewModel.showMessage("$label কপি করা হয়েছে!")
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("integration_guide_screen")
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Spacer(modifier = Modifier.height(8.dp))
            // Header Card
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
                            Icon(Icons.Default.Code, contentDescription = "Integration", tint = EmeraldPrimary)
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = "অন্যান্য সাইটে যুক্ত করার নিয়ম ও কোড",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                            Text(
                                text = "টপ-আপ সাইট, টুর্নামেন্ট বা ই-কমার্স সাইটে অটো পেমেন্ট বসান",
                                fontSize = 11.sp,
                                color = Color.Gray
                            )
                        }
                    }
                }
            }
        }

        item {
            // API Credentials Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "আপনার মার্চেন্ট API কী (API Credentials)",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = EmeraldPrimary
                        )

                        OutlinedButton(
                            onClick = { viewModel.regenerateApiKeys() },
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(12.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("নতুন কী তৈরি", fontSize = 10.sp)
                        }
                    }

                    // API Key
                    ApiKeyDisplayRow(
                        label = "API Public Key:",
                        key = merchantConfig?.apiKey ?: "live_pub_bd89329048a1",
                        onCopy = { copyToClipboard("API Key", it) }
                    )

                    // Secret Key
                    ApiKeyDisplayRow(
                        label = "API Secret Key:",
                        key = merchantConfig?.secretKey ?: "live_sec_ff4982a178bc9910",
                        onCopy = { copyToClipboard("Secret Key", it) }
                    )

                    // Webhook URL Setting
                    Text("আপনার সাইটের Webhook URL (যেখানে অটো নোটিফিকেশন যাবে):", fontSize = 11.sp, color = Color.Gray)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedTextField(
                            value = webhookUrlInput.ifBlank { merchantConfig?.defaultWebhookUrl ?: "" },
                            onValueChange = { webhookUrlInput = it },
                            placeholder = { Text("https://yoursite.com/api/payment-webhook.php") },
                            modifier = Modifier
                                .weight(1f)
                                .testTag("webhook_url_input"),
                            shape = RoundedCornerShape(8.dp),
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = EmeraldPrimary,
                                unfocusedBorderColor = DarkNavyBorder
                            )
                        )

                        Spacer(modifier = Modifier.width(8.dp))

                        Button(
                            onClick = {
                                merchantConfig?.let {
                                    viewModel.updateConfig(it.copy(defaultWebhookUrl = webhookUrlInput.trim()))
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Icon(Icons.Default.Save, contentDescription = "Save", tint = Color.Black, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }
        }

        item {
            // Integration Language / Guide Tabs
            val tabs = listOf("PHP (টপ-আপ)", "Node.js", "HTML Embed", "Python", "সম্পূর্ণ গাইড")
            TabRow(
                selectedTabIndex = activeTab,
                containerColor = DarkNavyCard,
                contentColor = EmeraldPrimary,
                indicator = { tabPositions ->
                    TabRowDefaults.SecondaryIndicator(
                        Modifier.tabIndicatorOffset(tabPositions[activeTab]),
                        color = EmeraldPrimary
                    )
                }
            ) {
                tabs.forEachIndexed { index, title ->
                    Tab(
                        selected = activeTab == index,
                        onClick = { activeTab = index },
                        text = {
                            Text(
                                text = title,
                                fontSize = 12.sp,
                                fontWeight = if (activeTab == index) FontWeight.Bold else FontWeight.Normal,
                                color = if (activeTab == index) EmeraldPrimary else Color.Gray
                            )
                        }
                    )
                }
            }
        }

        // TAB 0: PHP Integration
        if (activeTab == 0) {
            item {
                CodeSnippetCard(
                    title = "PHP Integration (টপ-আপ ও ওয়ার্ডপ্রেস সাইটে বসানোর স্ক্রিপ্ট)",
                    description = "আপনার টপ-আপ সাইটে পেমেন্ট শুরু করতে ও পেমেন্ট রিসিভ করতে নিচের কোডটি ব্যবহার করুন:",
                    code = """
<?php
// ১. পেমেন্ট রিকোয়েস্ট তৈরি (checkout.php)
${'$'}apiKey = "${merchantConfig?.apiKey ?: "live_pub_bd89329048a1"}";
${'$'}secretKey = "${merchantConfig?.secretKey ?: "live_sec_ff4982a178bc9910"}";

${'$'}postData = [
    'order_id'       => 'TOPUP_' . rand(1000, 9999),
    'amount'         => 350.00,
    'customer_phone' => '01712345678',
    'website_name'   => 'Diamond Bazar BD',
    'webhook_url'    => 'https://yoursite.com/webhook.php'
];

// ২. ওয়েবহুক রিসিভার (webhook.php - ডায়মন্ড বা UC অটো দেওয়ার কোড)
${'$'}rawPayload = file_get_contents('php://input');
${'$'}data = json_decode(${'$'}rawPayload, true);

if (${'$'}data['event'] === 'PAYMENT_COMPLETED' && ${'$'}data['status'] === 'SUCCESS') {
    ${'$'}orderId = ${'$'}data['order_id'];
    ${'$'}amount = ${'$'}data['amount'];
    ${'$'}trxId = ${'$'}data['trx_id'];
    ${'$'}method = ${'$'}data['method']; // BKASH, NAGAD, etc.
    
    // আপনার ডাটাবেজে ডায়মন্ড ডেলিভারি সম্পন্ন করুন
    // DB::query("UPDATE orders SET status='COMPLETED', trx_id='${'$'}trxId' WHERE id='${'$'}orderId'");
    
    http_response_code(200);
    echo json_encode(['status' => 'success']);
}
?>
                    """.trimIndent(),
                    onCopy = { copyToClipboard("PHP Code", it) }
                )
            }
        }

        // TAB 1: Node.js / Express Integration
        if (activeTab == 1) {
            item {
                CodeSnippetCard(
                    title = "Node.js / Express Integration",
                    description = "Next.js বা Express সার্ভারে ওয়েব হুক রিসিভ ও অটো অর্ডার ডেলিভারি:",
                    code = """
const express = require('express');
const app = express();
app.use(express.json());

// Webhook Endpoint (Auto-Delivery for Free Fire Diamonds / PUBG Tourney)
app.post('/api/autopay-webhook', (req, res) => {
    const { event, status, order_id, amount, trx_id, method } = req.body;
    
    if (event === 'PAYMENT_COMPLETED' && status === 'SUCCESS') {
        console.log(`Payment confirmed! Order #${'$'}{order_id}, TrxID: ${'$'}{trx_id}, ৳${'$'}{amount} via ${'$'}{method}`);
        
        // ডায়মন্ড টপ-আপ এপিআই বা টুর্নামেন্ট স্লট বুক করুন:
        // await deliverDiamondsToUser(order_id);
        
        return res.status(200).json({ success: true, message: 'Delivered' });
    }
    
    res.status(400).send('Invalid');
});

app.listen(3000, () => console.log('Server running on 3000'));
                    """.trimIndent(),
                    onCopy = { copyToClipboard("Node.js Code", it) }
                )
            }
        }

        // TAB 2: HTML Embed Button & Modal
        if (activeTab == 2) {
            item {
                CodeSnippetCard(
                    title = "HTML Embed Payment Button",
                    description = "যেকোনো ওয়েবসাইটের কেনাকাটা বা টপ-আপ পেজে একটি বাটন যুক্ত করতে:",
                    code = """
<!-- আপনার সাইটে পেমেন্ট বাটন যুক্ত করুন -->
<button onclick="openAutoPaymentGateway(350, 'TOPUP-102')" style="background:#00D084;color:#000;padding:12px 24px;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">
    বিকাশ / নগদ দিয়ে পেমেন্ট করুন (৳৩৫০)
</button>

<script>
function openAutoPaymentGateway(amount, orderId) {
    // কাস্টমারকে এই গেটওয়ে অ্যাপের হোস্ট করা লিংকে রিডাইরেক্ট করুন:
    const gatewayUrl = "https://your-domain.com/pay?amount=" + amount + "&order=" + orderId;
    window.location.href = gatewayUrl;
}
</script>
                    """.trimIndent(),
                    onCopy = { copyToClipboard("HTML Embed Code", it) }
                )
            }
        }

        // TAB 3: Python Integration
        if (activeTab == 3) {
            item {
                CodeSnippetCard(
                    title = "Python (Flask) Webhook Handler",
                    description = "Python ব্যাকএন্ডে ইনস্ট্যান্ট অটো-ভেরিফিকেশন হ্যান্ডলার:",
                    code = """
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/autopay-webhook', methods=['POST'])
def handle_payment():
    data = request.get_json()
    if data.get('event') == 'PAYMENT_COMPLETED' and data.get('status') == 'SUCCESS':
        order_id = data.get('order_id')
        amount = data.get('amount')
        trx_id = data.get('trx_id')
        
        # আপনার গেমিং বা শপ ডাটাবেজ আপডেট করুন
        print(f"Order {order_id} verified with TrxID {trx_id}")
        return jsonify({'status': 'ok'}), 200
        
    return jsonify({'error': 'bad request'}), 400

if __name__ == '__main__':
    app.run(port=5000)
                    """.trimIndent(),
                    onCopy = { copyToClipboard("Python Code", it) }
                )
            }
        }

        // TAB 4: Step-by-Step Guide in Bengali
        if (activeTab == 4) {
            item {
                SetupStepCard(
                    title = "🎮 ১. টপ-আপ সাইটে কিভাবে সেট করবেন (Free Fire / PUBG / CodaShop Clone)",
                    content = """
১. আপনার বিকাশ এবং নগদ সিম যে ফোনে লাগানো আছে, সেই ফোনে এই অ্যাপটি ইনস্টল রাখুন।
২. "ওয়ালেট সেটিংস" ট্যাবে গিয়ে আপনার বিকাশ ও নগদ পার্সোনাল বা মার্চেন্ট নম্বর লিখে সংরক্ষণ করুন।
৩. আপনার টপ-আপ সাইটের এডমিন প্যানেল বা কোডে Webhook URL হিসেবে দিন:
   https://yoursite.com/webhook.php
৪. কাস্টমার যখন ডায়মন্ড কেনার জন্য বিকাশ সিলেক্ট করবে, সে আপনার দেয়া নম্বরে টাকা পাঠিয়ে TrxID লিখবে।
৫. আপনার ফোনে টাকা আসার সাথে সাথেই এই অ্যাপ স্বয়ংক্রিয়ভাবে TrxID রিড করবে এবং আপনার সাইটে ৩ সেকেন্ডের মধ্যে অটোমেটিক ডায়মন্ড ডেলিভারি সিগন্যাল পাঠিয়ে দিবে!
                    """.trimIndent()
                )
            }

            item {
                SetupStepCard(
                    title = "🏆 ২. টুর্নামেন্ট সাইটে প্লেয়ার ফি অটো রিসিভ করার নিয়ম",
                    content = """
১. প্লেয়াররা যখন ম্যাচ এন্ট্রি ফি (যেমন: ৳১০০) পেমেন্ট করবে, তাদের চেকআউট পেজে পাঠানো হবে।
২. প্লেয়ার Send Money সম্পন্ন করে TrxID সাবমিট করার সাথে সাথে অ্যাপ অর্ডার ভেরিফাই করবে।
৩. আপনার সাইটের webhook.php ফাইলে কোড প্লেয়ারকে স্বয়ংক্রিয়ভাবে টুর্নামেন্ট স্লটে কনফার্ম করে দিবে। কোনো ম্যানুয়াল স্ক্রিনশট বা এপ্রুভ করার প্রয়োজন নেই!
                    """.trimIndent()
                )
            }

            item {
                SetupStepCard(
                    title = "📱 ৩. অ্যাপটি ব্যাকগ্রাউন্ডে অলওয়েজ চালু রাখার জরুরি টিপস",
                    content = """
১. আপনার ফোনের Settings > Apps > AutoPay BD তে যান।
২. Battery Optimization বন্ধ করে "Unrestricted" বা "No Restrictions" দিন।
৩. Auto-start পারমিশন অন রাখুন যাতে ফোন রিস্টার্ট হলেও অ্যাপ ব্যাকগ্রাউন্ডে চালু থাকে।
৪. অ্যাপের "অটো SMS ইঞ্জিন" থেকে SMS পারমিশন অ্যালাউ করুন।
                    """.trimIndent()
                )
            }
        }

        item {
            Spacer(modifier = Modifier.height(80.dp))
        }
    }
}

@Composable
fun ApiKeyDisplayRow(
    label: String,
    key: String,
    onCopy: (String) -> Unit
) {
    Column {
        Text(text = label, fontSize = 11.sp, color = Color.Gray)
        Spacer(modifier = Modifier.height(2.dp))
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF090E17), RoundedCornerShape(8.dp))
                .padding(horizontal = 10.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = key,
                fontSize = 12.sp,
                fontFamily = FontFamily.Monospace,
                color = Color(0xFF64B5F6)
            )
            IconButton(
                onClick = { onCopy(key) },
                modifier = Modifier.size(24.dp)
            ) {
                Icon(Icons.Default.ContentCopy, contentDescription = "Copy", modifier = Modifier.size(14.dp), tint = Color.Gray)
            }
        }
    }
}

@Composable
fun CodeSnippetCard(
    title: String,
    description: String,
    code: String,
    onCopy: (String) -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = title, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = EmeraldPrimary)
                IconButton(onClick = { onCopy(code) }, modifier = Modifier.size(28.dp)) {
                    Icon(Icons.Default.ContentCopy, contentDescription = "Copy Code", tint = EmeraldPrimary, modifier = Modifier.size(16.dp))
                }
            }

            Text(text = description, fontSize = 11.sp, color = Color.Gray)
            Spacer(modifier = Modifier.height(8.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF090E17), RoundedCornerShape(10.dp))
                    .padding(12.dp)
                    .horizontalScroll(rememberScrollState())
            ) {
                Text(
                    text = code,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    color = Color(0xFFE2E8F0),
                    lineHeight = 16.sp
                )
            }
        }
    }
}

@Composable
fun SetupStepCard(
    title: String,
    content: String
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = title, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = Color.White)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = content,
                fontSize = 12.sp,
                color = Color.LightGray,
                lineHeight = 18.sp
            )
        }
    }
}
