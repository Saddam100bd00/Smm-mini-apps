package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBackIos
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.data.model.PaymentMethodEntity
import com.example.engine.VerificationResult
import com.example.ui.MainViewModel
import com.example.ui.components.BrandLogoView
import com.example.ui.theme.BkashPink
import com.example.ui.theme.NagadOrange
import com.example.ui.theme.RocketPurple
import com.example.ui.theme.StatusFailed
import com.example.ui.theme.StatusSuccess
import com.example.ui.theme.UpayBlue
import java.util.Locale

data class TopNotice(
    val isSuccess: Boolean,
    val title: String,
    val message: String
)

@Composable
fun CheckoutSimulatorScreen(
    viewModel: MainViewModel,
    onBackToDashboard: () -> Unit
) {
    val context = LocalContext.current
    val allMethods by viewModel.methods.collectAsState()
    val merchantConfig by viewModel.merchantConfig.collectAsState()

    val siteName = merchantConfig?.siteName?.ifBlank { "DREAMTOPUP" } ?: "DREAMTOPUP"
    val siteLogoUrl = merchantConfig?.siteLogoUrl ?: ""

    // Filter to ONLY ACTIVE / ENABLED methods
    val activeMethods = remember(allMethods) {
        allMethods.filter { it.isEnabled }
    }

    // Stages:
    // 0 = Add Money Screen (Cleaned up, no 0৳ or S logo, beautiful instructions)
    // 1 = Wallet Selection (2x2 Grid of big cards: bKash, Nagad, Rocket, Upay)
    // 2 = Exact Screenshot Design (bKash pink or Nagad red with TrxID form, instructions, copy button, crimson Verify button)
    // 3 = Success Verified Receipt Screen
    var currentStage by remember { mutableIntStateOf(0) }

    var enteredAmount by remember { mutableStateOf("10") }
    var currentTxId by remember { mutableLongStateOf(0L) }
    var selectedMethod by remember { mutableStateOf<PaymentMethodEntity?>(null) }
    var userEnteredTrxId by remember { mutableStateOf("") }
    var isVerifying by remember { mutableStateOf(false) }

    // Top Floating Notice Banner state (for Success, Error, Wrong TrxID, Mismatch)
    var topNotice by remember { mutableStateOf<TopNotice?>(null) }

    val copyToClipboard: (String, String) -> Unit = { label, text ->
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        viewModel.showMessage("$label কপি করা হয়েছে: $text")
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAFC))
            .testTag("checkout_simulator_screen")
    ) {
        Column(modifier = Modifier.fillMaxSize()) {

            // ==========================================
            // TOP NAVIGATION BAR (‹ and × buttons on every page)
            // ==========================================
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = Color.White,
                shadowElevation = 1.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Circular Back Button ‹
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .border(1.dp, Color(0xFFE2E8F0), CircleShape)
                            .clickable {
                                topNotice = null
                                when (currentStage) {
                                    3 -> currentStage = 0
                                    2 -> currentStage = 1
                                    1 -> currentStage = 0
                                    else -> onBackToDashboard()
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBackIos,
                            contentDescription = "Back",
                            tint = Color(0xFF64748B),
                            modifier = Modifier.size(16.dp)
                        )
                    }

                    // Site branding in center if not in method screen
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (siteLogoUrl.isNotBlank()) {
                            AsyncImage(
                                model = siteLogoUrl,
                                contentDescription = siteName,
                                modifier = Modifier.height(28.dp),
                                contentScale = ContentScale.Fit
                            )
                        } else {
                            Text(
                                text = siteName,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Black,
                                color = Color(0xFF1E3A8A)
                            )
                        }
                    }

                    // Close Button ×
                    IconButton(
                        onClick = {
                            topNotice = null
                            currentStage = 0
                        },
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "Close",
                            tint = Color(0xFF64748B),
                            modifier = Modifier.size(24.dp)
                        )
                    }
                }
            }

            // ==========================================
            // BODY ACCORDING TO CURRENT STAGE
            // ==========================================
            Box(modifier = Modifier.weight(1f)) {

                // ------------------------------------------
                // STAGE 0: ADD MONEY SCREEN (Cleaned, 0৳ and S removed)
                // ------------------------------------------
                if (currentStage == 0) {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        item {
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "Add Money",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF1E293B)
                            )
                        }

                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = Color.White),
                                shape = RoundedCornerShape(14.dp),
                                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                            ) {
                                Column(
                                    modifier = Modifier.padding(18.dp),
                                    verticalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    Text(
                                        text = "Enter the amount",
                                        fontSize = 13.sp,
                                        color = Color(0xFF475569),
                                        fontWeight = FontWeight.Medium
                                    )

                                    OutlinedTextField(
                                        value = enteredAmount,
                                        onValueChange = { enteredAmount = it },
                                        placeholder = { Text("Amount (যেমন: 10, 50, 100)") },
                                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .testTag("add_money_amount_input"),
                                        shape = RoundedCornerShape(8.dp),
                                        colors = OutlinedTextFieldDefaults.colors(
                                            focusedBorderColor = Color(0xFF00A859),
                                            unfocusedBorderColor = Color(0xFFCBD5E1),
                                            focusedContainerColor = Color.White,
                                            unfocusedContainerColor = Color.White,
                                            focusedTextColor = Color.Black,
                                            unfocusedTextColor = Color.Black
                                        ),
                                        singleLine = true
                                    )

                                    // Preset Amount Chips
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                                    ) {
                                        listOf("10", "20", "50", "100", "500").forEach { preset ->
                                            Box(
                                                modifier = Modifier
                                                    .weight(1f)
                                                    .border(
                                                        1.dp,
                                                        if (enteredAmount == preset) Color(0xFF00A859) else Color(0xFFE2E8F0),
                                                        RoundedCornerShape(8.dp)
                                                    )
                                                    .background(
                                                        if (enteredAmount == preset) Color(0xFFE8F5E9) else Color(0xFFF8FAFC),
                                                        RoundedCornerShape(8.dp)
                                                    )
                                                    .clickable { enteredAmount = preset }
                                                    .padding(vertical = 7.dp),
                                                contentAlignment = Alignment.Center
                                            ) {
                                                Text(
                                                    text = "৳$preset",
                                                    fontSize = 12.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = if (enteredAmount == preset) Color(0xFF00A859) else Color.DarkGray
                                                )
                                            }
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(4.dp))

                                    // Green "Click Here To Add Money" button
                                    Button(
                                        onClick = {
                                            val amount = enteredAmount.toDoubleOrNull() ?: 10.0
                                            val orderId = "TOPUP-${(1000..9999).random()}"
                                            viewModel.createCheckoutInvoice(
                                                amount = amount,
                                                orderId = orderId,
                                                websiteName = siteName,
                                                customerPhone = "01788990011",
                                                customerName = "Customer",
                                                method = "BKASH",
                                                webhookUrl = merchantConfig?.defaultWebhookUrl ?: "",
                                                onCreated = { txId ->
                                                    currentTxId = txId
                                                    userEnteredTrxId = ""
                                                    topNotice = null
                                                    currentStage = 1
                                                }
                                            )
                                        },
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .height(48.dp)
                                            .testTag("click_here_to_add_money_btn"),
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF00A859)),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        Text(
                                            text = "Click Here To Add Money",
                                            color = Color.White,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 14.sp
                                        )
                                    }
                                }
                            }
                        }

                        // Beautiful "How to add money" Instructions Card
                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = Color.White),
                                shape = RoundedCornerShape(14.dp),
                                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                            ) {
                                Column(
                                    modifier = Modifier.padding(18.dp),
                                    verticalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(
                                            imageVector = Icons.Default.HelpOutline,
                                            contentDescription = null,
                                            tint = Color(0xFF00A859),
                                            modifier = Modifier.size(20.dp)
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            text = "How to add money (কীভাবে টাকা অ্যাড করবেন)",
                                            fontSize = 14.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = Color(0xFF1E293B)
                                        )
                                    }

                                    Spacer(modifier = Modifier.height(2.dp))

                                    StepItem(
                                        number = "১",
                                        text = "উপরের বক্সে টাকার পরিমাণ লিখুন এবং 'Click Here To Add Money' বাটনে চাপ দিন।"
                                    )
                                    StepItem(
                                        number = "২",
                                        text = "পছন্দের পেমেন্ট মেথড (বিকাশ, নগদ, রকেট বা উপায়) নির্বাচন করুন।"
                                    )
                                    StepItem(
                                        number = "৩",
                                        text = "স্ক্রিনে দেখানো নম্বরে নির্দিষ্ট পরিমাণ টাকা সেন্ড মানি (Send Money) করুন।"
                                    )
                                    StepItem(
                                        number = "৪",
                                        text = "টাকা পাঠানো শেষে SMS থেকে ট্রানজেকশন আইডি (TrxID) কপি করে বক্সে বসিয়ে 'ভেরিফাই' চাপুন।"
                                    )
                                    StepItem(
                                        number = "৫",
                                        text = "সিস্টেম স্বয়ংক্রিয়ভাবে ট্রানজেকশন যাচাই করে সাথে সাথে আপনার একাউন্টে ব্যালেন্স যুক্ত করে দিবে।"
                                    )
                                }
                            }
                        }

                        item {
                            Spacer(modifier = Modifier.height(20.dp))
                        }
                    }
                }

                // ------------------------------------------
                // STAGE 1: 2x2 WALLET METHOD SELECTION (bKash & Nagad on top, Rocket & Upay below)
                // ------------------------------------------
                if (currentStage == 1) {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 16.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        item {
                            Spacer(modifier = Modifier.height(10.dp))
                            // Top Card: Wallet Icon + Text
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = Color.White),
                                shape = RoundedCornerShape(12.dp),
                                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                            ) {
                                Column(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(18.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.AccountBalanceWallet,
                                        contentDescription = "Wallet",
                                        modifier = Modifier.size(38.dp),
                                        tint = Color.Gray
                                    )
                                    Spacer(modifier = Modifier.height(6.dp))
                                    Text(
                                        text = "Wallet",
                                        fontSize = 17.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFF1E293B)
                                    )
                                }
                            }
                        }

                        item {
                            // Blue Bar: মোবাইল ব্যাংকিং
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(Color(0xFF0056B3), RoundedCornerShape(8.dp))
                                    .padding(vertical = 11.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "মোবাইল ব্যাংকিং",
                                    color = Color.White,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }

                        // 2x2 BIG CARDS:
                        // Row 1: bKash (বিকাশ) and Nagad (নগদ)
                        // Row 2: Rocket (রকেট) and Upay (উপায়)
                        item {
                            val bkashMethod = activeMethods.find { it.id.equals("bkash", true) }
                            val nagadMethod = activeMethods.find { it.id.equals("nagad", true) }

                            if (bkashMethod != null || nagadMethod != null) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    if (bkashMethod != null) {
                                        Box(modifier = Modifier.weight(1f)) {
                                            BigWalletCard(
                                                method = bkashMethod,
                                                onClick = {
                                                    selectedMethod = bkashMethod
                                                    userEnteredTrxId = ""
                                                    topNotice = null
                                                    currentStage = 2
                                                }
                                            )
                                        }
                                    }
                                    if (nagadMethod != null) {
                                        Box(modifier = Modifier.weight(1f)) {
                                            BigWalletCard(
                                                method = nagadMethod,
                                                onClick = {
                                                    selectedMethod = nagadMethod
                                                    userEnteredTrxId = ""
                                                    topNotice = null
                                                    currentStage = 2
                                                }
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        item {
                            val rocketMethod = activeMethods.find { it.id.equals("rocket", true) }
                            val upayMethod = activeMethods.find { it.id.equals("upay", true) }

                            if (rocketMethod != null || upayMethod != null) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    if (rocketMethod != null) {
                                        Box(modifier = Modifier.weight(1f)) {
                                            BigWalletCard(
                                                method = rocketMethod,
                                                onClick = {
                                                    selectedMethod = rocketMethod
                                                    userEnteredTrxId = ""
                                                    topNotice = null
                                                    currentStage = 2
                                                }
                                            )
                                        }
                                    }
                                    if (upayMethod != null) {
                                        Box(modifier = Modifier.weight(1f)) {
                                            BigWalletCard(
                                                method = upayMethod,
                                                onClick = {
                                                    selectedMethod = upayMethod
                                                    userEnteredTrxId = ""
                                                    topNotice = null
                                                    currentStage = 2
                                                }
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        if (activeMethods.isEmpty()) {
                            item {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(24.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = "কোনো পেমেন্ট মেথড সক্রিয় নেই। ওয়ালেট সেটিংস থেকে মেথড চালু করুন।",
                                        color = Color.Red,
                                        fontSize = 13.sp,
                                        textAlign = TextAlign.Center
                                    )
                                }
                            }
                        }
                    }
                }

                // ------------------------------------------
                // STAGE 2: EXACT SCREENSHOT DESIGN (bKash & Nagad screens)
                // ------------------------------------------
                if (currentStage == 2 && selectedMethod != null) {
                    val method = selectedMethod!!
                    val isBkash = method.id.equals("bkash", true)
                    val isNagad = method.id.equals("nagad", true)
                    val isRocket = method.id.equals("rocket", true)

                    // Card Background Color matching Screenshot:
                    // bKash: Hot Magenta Pink #D81B60
                    // Nagad: Vibrant Red #E50914 / #D32F2F
                    // Rocket: #8C3494, Upay: #0056B3
                    val cardBgColor = when {
                        isBkash -> Color(0xFFD81B60)
                        isNagad -> Color(0xFFE50914)
                        isRocket -> RocketPurple
                        else -> UpayBlue
                    }

                    // Copy pill button background:
                    // bKash dark maroon #880E4F / Nagad dark red #8B0000
                    val copyPillBg = when {
                        isBkash -> Color(0xFF880E4F)
                        isNagad -> Color(0xFF8B0000)
                        else -> Color(0xFF1E3A8A)
                    }

                    // Bottom Verify Button: Deep Crimson #990018
                    val verifyButtonColor = Color(0xFF990018)

                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        item {
                            Spacer(modifier = Modifier.height(10.dp))
                            // 1. TOP WHITE CARD WITH BRAND LOGO (Exact as Screenshot)
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(96.dp),
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = Color.White),
                                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                            ) {
                                Box(
                                    modifier = Modifier.fillMaxSize(),
                                    contentAlignment = Alignment.Center
                                ) {
                                    BrandLogoView(
                                        providerId = method.id,
                                        customLogoUrl = method.customLogoUrl,
                                        height = 44.dp,
                                        showContainer = false
                                    )
                                }
                            }
                        }

                        item {
                            // 2. AMOUNT PILL: ৳ 10 (Exact as Screenshot)
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(Color(0xFFF1F5F9))
                                    .padding(horizontal = 24.dp, vertical = 8.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "৳ $enteredAmount",
                                    fontSize = 22.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF2B5885)
                                )
                            }
                        }

                        item {
                            // 3. MAIN COLORED FORM CONTAINER (Exact as Screenshot)
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(16.dp),
                                colors = CardDefaults.cardColors(containerColor = cardBgColor)
                            ) {
                                Column(
                                    modifier = Modifier.padding(18.dp),
                                    verticalArrangement = Arrangement.spacedBy(14.dp)
                                ) {
                                    Text(
                                        text = "ট্রানজেকশন আইডি দিন",
                                        color = Color.White,
                                        fontSize = 16.sp,
                                        fontWeight = FontWeight.Bold,
                                        modifier = Modifier.align(Alignment.CenterHorizontally)
                                    )

                                    // White Rounded Text Input Box (Screenshot)
                                    OutlinedTextField(
                                        value = userEnteredTrxId,
                                        onValueChange = {
                                            userEnteredTrxId = it.uppercase()
                                            topNotice = null
                                        },
                                        placeholder = {
                                            Text(
                                                text = "ট্রানজেকশন আইডি দিন",
                                                color = Color(0xFF94A3B8),
                                                fontSize = 14.sp
                                            )
                                        },
                                        singleLine = true,
                                        keyboardOptions = KeyboardOptions(
                                            capitalization = KeyboardCapitalization.Characters
                                        ),
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .testTag("customer_trxid_input"),
                                        shape = RoundedCornerShape(8.dp),
                                        colors = OutlinedTextFieldDefaults.colors(
                                            focusedBorderColor = Color.White,
                                            unfocusedBorderColor = Color.Transparent,
                                            focusedContainerColor = Color.White,
                                            unfocusedContainerColor = Color.White,
                                            focusedTextColor = Color.Black,
                                            unfocusedTextColor = Color.Black
                                        )
                                    )

                                    // Bulleted Instruction list
                                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                        ScreenshotBullet(
                                            text = when {
                                                isNagad -> "*167# ডায়াল করে আপনার NAGAD মোবাইল মেনুতে যান অথবা NAGAD অ্যাপে যান।"
                                                isRocket -> "*322# ডায়াল করে আপনার Rocket মেনুতে যান অথবা রকেট অ্যাপ খুলুন।"
                                                isBkash -> "*247# ডায়াল করে আপনার bKash মোবাইল মেনুতে যান অথবা bKash অ্যাপ খুলুন।"
                                                else -> "আপনার ${method.name} অ্যাপ খুলুন।"
                                            }
                                        )

                                        ScreenshotBullet(
                                            text = if (method.type == "PERSONAL") "সেন্ড মানি -এ ক্লিক করুন।" else "পেমেন্ট -এ ক্লিক করুন।"
                                        )

                                        // Number with yellow color & copy pill button (Screenshot)
                                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                            Row(
                                                verticalAlignment = Alignment.CenterVertically,
                                                modifier = Modifier.fillMaxWidth()
                                            ) {
                                                Text("• ", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                                Text(
                                                    text = "উপরের নম্বরে টাকা পাঠান। ",
                                                    color = Color.White,
                                                    fontSize = 13.sp
                                                )
                                                Text(
                                                    text = method.number.ifBlank { "01735102916" },
                                                    color = Color(0xFFFFE082),
                                                    fontWeight = FontWeight.Bold,
                                                    fontSize = 14.sp
                                                )
                                            }

                                            // Dark rounded copy pill button [ 📋 কপি ] (Screenshot)
                                            Box(
                                                modifier = Modifier
                                                    .padding(start = 14.dp)
                                                    .clip(RoundedCornerShape(16.dp))
                                                    .background(copyPillBg)
                                                    .clickable {
                                                        copyToClipboard("নম্বর", method.number.ifBlank { "01735102916" })
                                                    }
                                                    .padding(horizontal = 12.dp, vertical = 4.dp)
                                            ) {
                                                Row(verticalAlignment = Alignment.CenterVertically) {
                                                    Icon(
                                                        imageVector = Icons.Default.ContentCopy,
                                                        contentDescription = "Copy",
                                                        modifier = Modifier.size(13.dp),
                                                        tint = Color.White
                                                    )
                                                    Spacer(modifier = Modifier.width(4.dp))
                                                    Text(
                                                        text = "কপি",
                                                        color = Color.White,
                                                        fontSize = 12.sp,
                                                        fontWeight = FontWeight.Bold
                                                    )
                                                }
                                            }
                                        }

                                        // Amount in yellow
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Text("• ", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                            Text(
                                                text = "টাকার পরিমাণঃ ",
                                                color = Color.White,
                                                fontSize = 13.sp
                                            )
                                            Text(
                                                text = enteredAmount,
                                                color = Color(0xFFFFE082),
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 14.sp
                                            )
                                        }

                                        ScreenshotBullet(
                                            text = if (isNagad) {
                                                "নিশ্চিত করে এখন আপনার NAGAD মোবাইল মেনু PIN লিখুন।"
                                            } else {
                                                "নিশ্চিত করে এখন আপনার ${method.name} PIN লিখুন।"
                                            }
                                        )

                                        ScreenshotBullet(text = "টাকা পাঠান এবং ট্রানজেকশন আইডি কপি করুন।")

                                        ScreenshotBullet(text = "ট্রানজেকশন আইডি লিখে ভেরিফাই চাপুন।")
                                    }
                                }
                            }
                        }

                        // 4. BIG BOTTOM "ভেরিফাই" BUTTON (Deep Crimson Red #990018 as in Screenshot)
                        item {
                            Button(
                                onClick = {
                                    if (userEnteredTrxId.isBlank()) {
                                        topNotice = TopNotice(
                                            isSuccess = false,
                                            title = "পেমেন্ট ব্যর্থ হয়েছে!",
                                            message = "অনুগ্রহ করে ট্রানজেকশন আইডি (TrxID) লিখুন!"
                                        )
                                        return@Button
                                    }

                                    isVerifying = true
                                    topNotice = null

                                    // STRICT VERIFICATION:
                                    // 1. Duplicate check
                                    // 2. TrxID existence in received SMS check
                                    // 3. Exact Amount check (more or less fails)
                                    // 4. Success -> Mark completed & send webhook
                                    viewModel.verifyStrictPayment(
                                        txId = currentTxId,
                                        trxId = userEnteredTrxId
                                    ) { result ->
                                        isVerifying = false
                                        when (result) {
                                            is VerificationResult.Success -> {
                                                topNotice = TopNotice(
                                                    isSuccess = true,
                                                    title = "পেমেন্ট সফল হয়েছে!",
                                                    message = "TrxID: ${userEnteredTrxId} | ৳$enteredAmount টাকা সফলভাবে জমা হয়েছে।"
                                                )
                                                currentStage = 3
                                            }
                                            is VerificationResult.DuplicateTrxId -> {
                                                topNotice = TopNotice(
                                                    isSuccess = false,
                                                    title = "পেমেন্ট ব্যর্থ হয়েছে!",
                                                    message = result.message
                                                )
                                            }
                                            is VerificationResult.InvalidTrxId -> {
                                                topNotice = TopNotice(
                                                    isSuccess = false,
                                                    title = "পেমেন্ট ব্যর্থ হয়েছে!",
                                                    message = result.message
                                                )
                                            }
                                            is VerificationResult.AmountMismatch -> {
                                                topNotice = TopNotice(
                                                    isSuccess = false,
                                                    title = "টাকার পরিমাণ মিল নেই!",
                                                    message = result.message
                                                )
                                            }
                                        }
                                    }
                                },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp)
                                    .testTag("verify_payment_action_btn"),
                                colors = ButtonDefaults.buttonColors(containerColor = verifyButtonColor),
                                shape = RoundedCornerShape(10.dp),
                                enabled = !isVerifying
                            ) {
                                if (isVerifying) {
                                    CircularProgressIndicator(modifier = Modifier.size(20.dp), color = Color.White)
                                } else {
                                    Text(
                                        text = "ভেরিফাই",
                                        color = Color.White,
                                        fontSize = 16.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }
                        }

                        // TEST LAB SIMULATOR (To immediately test Success, Wrong TrxID, Mismatch, Duplicate)
                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = Color.White),
                                shape = RoundedCornerShape(12.dp),
                                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                            ) {
                                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text(
                                        text = "🧪 টেস্ট ল্যাব (শর্তগুলো সাথে সাথে যাচাই করুন):",
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFF334155)
                                    )

                                    val currentAmountDouble = enteredAmount.toDoubleOrNull() ?: 10.0
                                    val randomTrx = remember { "BKA" + (100000..999999).random() }

                                    Button(
                                        onClick = {
                                            val smsBody = "You have received Tk ${String.format(Locale.US, "%.2f", currentAmountDouble)} from 01788990011. Balance Tk 4,500.00. TrxID $randomTrx at 26/09/2026."
                                            viewModel.simulateSms(method.id, smsBody) { _, _ ->
                                                userEnteredTrxId = randomTrx
                                                topNotice = TopNotice(
                                                    isSuccess = true,
                                                    title = "টেস্ট SMS প্রাপ্ত হয়েছে",
                                                    message = "সঠিক টাকার SMS তৈরি হয়েছে: TrxID $randomTrx (টাকা: ৳$currentAmountDouble)। এবার 'ভেরিফাই' চাপুন।"
                                                )
                                            }
                                        },
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF00A859)),
                                        shape = RoundedCornerShape(6.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text("১. সঠিক টাকার SMS সিমুলেট করুন (৳$currentAmountDouble)", fontSize = 11.sp)
                                    }

                                    val wrongAmount = if (currentAmountDouble == 50.0) 30.0 else 50.0
                                    val wrongTrx = remember { "WRG" + (100000..999999).random() }
                                    Button(
                                        onClick = {
                                            val smsBody = "You have received Tk ${String.format(Locale.US, "%.2f", wrongAmount)} from 01788990011. TrxID $wrongTrx at 26/09/2026."
                                            viewModel.simulateSms(method.id, smsBody) { _, _ ->
                                                userEnteredTrxId = wrongTrx
                                                topNotice = TopNotice(
                                                    isSuccess = false,
                                                    title = "ভুল টাকার SMS তৈরি হয়েছে",
                                                    message = "SMS এ এসেছে ৳$wrongAmount কিন্তু আপনি চেয়েছেন ৳$currentAmountDouble। 'ভেরিফাই' চাপলে ব্যর্থ বলবে।"
                                                )
                                            }
                                        },
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE53935)),
                                        shape = RoundedCornerShape(6.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text("২. ভুল টাকার SMS টেস্ট (৳$wrongAmount এর SMS পাঠাবে)", fontSize = 11.sp)
                                    }
                                }
                            }
                        }

                        item {
                            Spacer(modifier = Modifier.height(20.dp))
                        }
                    }
                }

                // ------------------------------------------
                // STAGE 3: SUCCESSFUL RECEIPT
                // ------------------------------------------
                if (currentStage == 3) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(Color.White)
                            .padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(14.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(72.dp)
                                    .background(StatusSuccess.copy(alpha = 0.15f), CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.CheckCircle,
                                    contentDescription = "Success",
                                    tint = StatusSuccess,
                                    modifier = Modifier.size(48.dp)
                                )
                            }

                            Text(
                                text = "পেমেন্ট সফল ও ভেরিফাইড!",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF1E293B)
                            )

                            Text(
                                text = "টাকার পরিমাণ ও ট্রানজেকশন আইডি সফলভাবে যাচাই হয়েছে।",
                                fontSize = 12.sp,
                                color = Color.Gray,
                                textAlign = TextAlign.Center
                            )

                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = Color(0xFFF8FAFC)),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    ReceiptRow(label = "সাইটের নাম", value = siteName)
                                    ReceiptRow(label = "পদ্ধতি", value = selectedMethod?.name ?: "MFS")
                                    ReceiptRow(label = "পরিশোধিত টাকা", value = "৳ $enteredAmount")
                                    ReceiptRow(label = "TrxID", value = userEnteredTrxId)
                                    ReceiptRow(label = "স্ট্যাটাস", value = "সফল (SUCCESS)", valueColor = StatusSuccess)
                                }
                            }

                            Button(
                                onClick = {
                                    topNotice = null
                                    currentStage = 0
                                },
                                modifier = Modifier.fillMaxWidth(),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF00A859)),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Text("নতুন পেমেন্ট করুন", color = Color.White, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }

        // ==========================================
        // FLOATING TOP NOTICE / BANNER (Success, Error, Wrong TrxID)
        // ==========================================
        AnimatedVisibility(
            visible = topNotice != null,
            enter = slideInVertically(initialOffsetY = { -it }) + fadeIn(),
            exit = slideOutVertically(targetOffsetY = { -it }) + fadeOut(),
            modifier = Modifier.align(Alignment.TopCenter)
        ) {
            topNotice?.let { notice ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 8.dp)
                        .shadow(6.dp, RoundedCornerShape(12.dp)),
                    colors = CardDefaults.cardColors(
                        containerColor = if (notice.isSuccess) Color(0xFF065F46) else Color(0xFF991B1B)
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 14.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(
                                imageVector = if (notice.isSuccess) Icons.Default.CheckCircle else Icons.Default.Error,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(24.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = notice.title,
                                    color = Color.White,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = notice.message,
                                    color = Color(0xFFF1F5F9),
                                    fontSize = 11.sp,
                                    lineHeight = 15.sp
                                )
                            }
                        }

                        IconButton(
                            onClick = { topNotice = null },
                            modifier = Modifier.size(24.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = "Dismiss",
                                tint = Color.White,
                                modifier = Modifier.size(18.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun BigWalletCard(
    method: PaymentMethodEntity,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(112.dp)
            .shadow(3.dp, RoundedCornerShape(14.dp))
            .clickable(onClick = onClick)
            .testTag("wallet_method_${method.id}"),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = CardDefaults.outlinedCardBorder().copy(
            brush = androidx.compose.ui.graphics.SolidColor(Color(0xFFE2E8F0))
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(vertical = 10.dp, horizontal = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            BrandLogoView(
                providerId = method.id,
                customLogoUrl = method.customLogoUrl,
                height = 46.dp,
                showContainer = false
            )
            Spacer(modifier = Modifier.height(6.dp))
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0xFFF1F5F9))
                    .padding(horizontal = 14.dp, vertical = 3.dp)
            ) {
                Text(
                    text = if (method.type.equals("MERCHANT", ignoreCase = true)) "Merchant" else "Personal",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF475569)
                )
            }
        }
    }
}

@Composable
fun ScreenshotBullet(text: String) {
    Row(
        verticalAlignment = Alignment.Top,
        modifier = Modifier.fillMaxWidth()
    ) {
        Text("• ", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 15.sp)
        Text(
            text = text,
            color = Color.White,
            fontSize = 13.sp,
            lineHeight = 18.sp
        )
    }
}

@Composable
fun StepItem(number: String, text: String) {
    Row(verticalAlignment = Alignment.Top, modifier = Modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier
                .size(20.dp)
                .background(Color(0xFF00A859), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text(number, color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = text,
            color = Color(0xFF334155),
            fontSize = 12.sp,
            lineHeight = 17.sp
        )
    }
}

@Composable
fun ReceiptRow(label: String, value: String, valueColor: Color = Color.Black) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = Color.Gray, fontSize = 12.sp)
        Text(value, color = valueColor, fontWeight = FontWeight.Bold, fontSize = 12.sp)
    }
}
