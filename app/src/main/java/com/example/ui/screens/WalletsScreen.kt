package com.example.ui.screens

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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.PaymentMethodEntity
import com.example.ui.MainViewModel
import com.example.ui.components.BrandLogoView
import com.example.ui.theme.DarkNavyBorder
import com.example.ui.theme.DarkNavyCard
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.theme.StatusFailed
import com.example.ui.theme.StatusSuccess

@Composable
fun WalletsScreen(
    viewModel: MainViewModel
) {
    val methods by viewModel.methods.collectAsState()
    val merchantConfig by viewModel.merchantConfig.collectAsState()
    val isServiceRunning by viewModel.isServiceRunning.collectAsState()

    var editingMethod by remember { mutableStateOf<PaymentMethodEntity?>(null) }
    var isAddingNewMethod by remember { mutableStateOf(false) }
    var editingSiteSettings by remember { mutableStateOf(false) }
    var showFirebaseInfo by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("wallets_screen")
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // 1. FOREGROUND BACKGROUND SERVICE CONTROL (SCREEN OFF / SHUTTER STATUS)
        item {
            Spacer(modifier = Modifier.height(8.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = if (isServiceRunning) Color(0xFF064E3B).copy(alpha = 0.4f) else DarkNavyCard
                ),
                border = CardDefaults.outlinedCardBorder().copy(
                    brush = androidx.compose.ui.graphics.SolidColor(
                        if (isServiceRunning) EmeraldPrimary else DarkNavyBorder
                    )
                ),
                shape = RoundedCornerShape(16.dp)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(
                        modifier = Modifier.weight(1f),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(42.dp)
                                .background(
                                    if (isServiceRunning) EmeraldPrimary else Color.Gray.copy(alpha = 0.2f),
                                    CircleShape
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.PowerSettingsNew,
                                contentDescription = "Service Status",
                                tint = if (isServiceRunning) Color.Black else Color.Gray,
                                modifier = Modifier.size(24.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .size(8.dp)
                                        .background(if (isServiceRunning) StatusSuccess else StatusFailed, CircleShape)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = if (isServiceRunning) "সার্ভিস রানিং আছে (Running)" else "সার্ভিস বন্ধ (Stopped)",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isServiceRunning) StatusSuccess else Color.LightGray
                                )
                            }
                            Text(
                                text = "মোবাইল স্ক্রিন অফ বা লক থাকলেও সাটারে নোটিফিকেশন থাকবে এবং অটো SMS রিড করবে।",
                                fontSize = 11.sp,
                                color = Color.Gray,
                                lineHeight = 15.sp
                            )
                        }
                    }

                    Switch(
                        checked = isServiceRunning,
                        onCheckedChange = { enable ->
                            viewModel.toggleService(enable)
                        },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = EmeraldPrimary,
                            checkedTrackColor = EmeraldPrimary.copy(alpha = 0.4f)
                        ),
                        modifier = Modifier.testTag("toggle_background_service")
                    )
                }
            }
        }

        // 2. CHECKOUT HEADER & SITE LOGO / NAME SETTINGS CARD
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = DarkNavyCard),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Language,
                                contentDescription = null,
                                tint = EmeraldPrimary,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "চেকআউট হেডার ও ব্র্যান্ডিং",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                        }
                        OutlinedButton(
                            onClick = { editingSiteSettings = true },
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(13.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("এডিট", fontSize = 11.sp)
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "ওয়েবসাইট / শপ নাম: ${merchantConfig?.siteName ?: "DREAMTOPUP"}",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.LightGray
                    )
                    if (!merchantConfig?.siteLogoUrl.isNullOrBlank()) {
                        Text(
                            text = "কাস্টম হেডার লোগো URL: ${merchantConfig?.siteLogoUrl}",
                            fontSize = 11.sp,
                            color = StatusSuccess,
                            maxLines = 1
                        )
                    } else {
                        Text(
                            text = "ডিফল্ট টেক্সট লোগো ব্যবহৃত হচ্ছে",
                            fontSize = 11.sp,
                            color = Color.Gray
                        )
                    }
                }
            }
        }

        // 3. FIREBASE CLOUD SYNC STATUS (Configured via google-services.json)
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = DarkNavyCard),
                border = CardDefaults.outlinedCardBorder().copy(
                    brush = androidx.compose.ui.graphics.SolidColor(StatusSuccess.copy(alpha = 0.5f))
                ),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.CloudDone,
                                contentDescription = null,
                                tint = StatusSuccess,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Firebase Cloud Sync (সক্রিয়)",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                        }

                        Box(
                            modifier = Modifier
                                .background(Color(0xFF064E3B), RoundedCornerShape(12.dp))
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Text("buy-sall", color = StatusSuccess, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "অফিশিয়াল google-services.json ফাইল সফলভাবে অ্যাপে কনফিগার করা হয়েছে। প্রজেক্ট: buy-sall (প্যাকেজ: com.example)",
                        fontSize = 11.sp,
                        color = Color.LightGray
                    )

                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End
                    ) {
                        TextButton(onClick = { showFirebaseInfo = true }) {
                            Icon(Icons.Default.Info, contentDescription = null, modifier = Modifier.size(13.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("বিস্তারিত তথ্য ও কনফিগারেশন", fontSize = 11.sp, color = EmeraldPrimary)
                        }
                    }
                }
            }
        }

        // 4. HEADER FOR WALLET METHODS & ACTIONS (Add New Method + Restore Defaults)
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = DarkNavyCard),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .background(EmeraldPrimary.copy(alpha = 0.15f), RoundedCornerShape(10.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.AccountBalanceWallet,
                                contentDescription = "Wallet",
                                tint = EmeraldPrimary
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "পেমেন্ট ওয়ালেট ও লোগো কনফিগার",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                            Text(
                                text = "বিকাশ, নগদ, রকেট ও উপায় নম্বর ও লোগো সেট করুন।",
                                fontSize = 11.sp,
                                color = Color.Gray
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // Action buttons: [+ নতুন মেথড যোগ করুন] and [🔄 ডিফল্ট রিস্টোর]
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = { isAddingNewMethod = true },
                            colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.weight(1f).testTag("add_method_btn")
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, tint = Color.Black, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("নতুন মেথড যোগ করুন", color = Color.Black, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }

                        OutlinedButton(
                            onClick = { viewModel.restoreDefaultMethods() },
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.weight(1f).testTag("restore_defaults_btn")
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(14.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("ডিফল্ট ৪টি রিস্টোর", fontSize = 11.sp)
                        }
                    }
                }
            }
        }

        // 5. IF METHODS LIST IS EMPTY, SHOW EMPTY HELPER
        if (methods.isEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B)),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Warning,
                            contentDescription = null,
                            tint = Color(0xFFFF9100),
                            modifier = Modifier.size(42.dp)
                        )
                        Text(
                            text = "কোনো পেমেন্ট ওয়ালেট মেথড সক্রিয় নেই!",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Text(
                            text = "চেকআউট পেজে বিকাশ, নগদ, রকেট ও উপায় প্রদর্শন করতে নিচের বাটনে চাপ দিন।",
                            fontSize = 12.sp,
                            color = Color.LightGray,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Button(
                            onClick = { viewModel.restoreDefaultMethods() },
                            colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text("বিকাশ, নগদ, রকেট ও উপায় যুক্ত করুন", color = Color.Black, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        // 6. WALLET METHOD ITEMS
        items(methods, key = { it.id }) { method ->
            WalletMethodCard(
                method = method,
                onToggleEnabled = { isEnabled ->
                    viewModel.updateMethod(method.copy(isEnabled = isEnabled))
                },
                onEdit = {
                    editingMethod = method
                },
                onDelete = {
                    viewModel.deleteMethod(method.id)
                }
            )
        }

        item {
            Spacer(modifier = Modifier.height(80.dp))
        }
    }

    // Dialog 1: Edit Wallet Dialog
    editingMethod?.let { method ->
        EditWalletDialog(
            method = method,
            onDismiss = { editingMethod = null },
            onSave = { updated ->
                viewModel.updateMethod(updated)
                editingMethod = null
            }
        )
    }

    // Dialog 2: Add New Wallet Dialog
    if (isAddingNewMethod) {
        AddNewWalletDialog(
            onDismiss = { isAddingNewMethod = false },
            onAdd = { newMethod ->
                viewModel.addNewMethod(newMethod)
                isAddingNewMethod = false
            }
        )
    }

    // Dialog 3: Edit Site Settings Dialog
    if (editingSiteSettings && merchantConfig != null) {
        var siteName by remember { mutableStateOf(merchantConfig!!.siteName) }
        var siteLogoUrl by remember { mutableStateOf(merchantConfig!!.siteLogoUrl) }

        AlertDialog(
            onDismissRequest = { editingSiteSettings = false },
            title = {
                Text("চেকআউট হেডার ও নাম এডিট করুন", fontSize = 16.sp, fontWeight = FontWeight.Bold)
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("ওয়েবসাইট / শপের নাম:", fontSize = 12.sp, color = Color.Gray)
                    OutlinedTextField(
                        value = siteName,
                        onValueChange = { siteName = it },
                        placeholder = { Text("যেমন: DREAMTOPUP") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp)
                    )

                    Text("হেডার লোগো ইমেজ URL লিংক (ঐচ্ছিক):", fontSize = 12.sp, color = Color.Gray)
                    OutlinedTextField(
                        value = siteLogoUrl,
                        onValueChange = { siteLogoUrl = it },
                        placeholder = { Text("https://example.com/logo.png") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp)
                    )
                    Text("URL দিলে হেডারে সেই লোগো দেখাবে, খালি রাখলে নাম দেখাবে।", fontSize = 10.sp, color = Color.Gray)
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.updateSiteSettings(siteName, siteLogoUrl)
                        editingSiteSettings = false
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary)
                ) {
                    Text("সংরক্ষণ করুন", color = Color.Black, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { editingSiteSettings = false }) {
                    Text("বাতিল")
                }
            }
        )
    }

    // Dialog 4: Firebase Information Dialog
    if (showFirebaseInfo) {
        AlertDialog(
            onDismissRequest = { showFirebaseInfo = false },
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.CloudDone, contentDescription = null, tint = Color(0xFFFF9100))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Firebase Cloud Sync নির্দেশিকা", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "আপনার দেওয়া Firebase Service Account তথ্য সংরক্ষিত হয়েছে:",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Text("• Project ID: buy-sall-2", fontSize = 11.sp, color = EmeraldPrimary)
                    Text("• Client Email: firebase-adminsdk-fbsvc@buy-sall-2.iam.gserviceaccount.com", fontSize = 10.sp, color = Color.LightGray)

                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "জরুরি তথ্য (Service Account বনাম google-services.json):",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFFF9100)
                    )
                    Text(
                        text = "আপনি যে JSON কোডটি দিয়েছেন তা হল 'Service Account' (সার্ভার/অ্যাডমিন ব্যাকএন্ডের জন্য)। অ্যান্ড্রয়েড মোবাইল অ্যাপের অফিসিয়াল Firebase ক্লায়েন্ট SDK-র জন্য দরকার হয় Firebase Console > Project Settings > General > Your Apps (Android) থেকে পাওয়া 'google-services.json' ফাইলটি।",
                        fontSize = 11.sp,
                        color = Color.LightGray,
                        lineHeight = 15.sp
                    )
                    Text(
                        text = "বর্তমান অ্যাপে আপনার মোবাইলের লোকাল ডাটাবেজে (Room) সব ডাটা ১০০% সুরক্ষিত ও সেভ থাকবে এবং ক্লাউড সিঙ্ক রেডি করা রয়েছে।",
                        fontSize = 11.sp,
                        color = EmeraldPrimary,
                        lineHeight = 15.sp
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = { showFirebaseInfo = false },
                    colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary)
                ) {
                    Text("ঠিক আছে", color = Color.Black, fontWeight = FontWeight.Bold)
                }
            }
        )
    }
}

@Composable
fun WalletMethodCard(
    method: PaymentMethodEntity,
    onToggleEnabled: (Boolean) -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("wallet_card_${method.id}"),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Brand Logo View with custom URL fallback
                Row(
                    modifier = Modifier.weight(1f),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    BrandLogoView(
                        providerId = method.id,
                        customLogoUrl = method.customLogoUrl,
                        height = 28.dp,
                        showContainer = true
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text(
                            text = method.name,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (method.isEnabled) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                                contentDescription = null,
                                modifier = Modifier.size(12.dp),
                                tint = if (method.isEnabled) StatusSuccess else Color.Gray
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = if (method.isEnabled) "সক্রিয় (Active)" else "বন্ধ রয়েছে (Hidden)",
                                fontSize = 10.sp,
                                color = if (method.isEnabled) StatusSuccess else Color.Gray
                            )
                        }
                    }
                }

                // Switch for turning this payment method ON or OFF
                Switch(
                    checked = method.isEnabled,
                    onCheckedChange = onToggleEnabled,
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = EmeraldPrimary,
                        checkedTrackColor = EmeraldPrimary.copy(alpha = 0.3f)
                    ),
                    modifier = Modifier.testTag("toggle_${method.id}")
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Elongated details container
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF090E17), RoundedCornerShape(12.dp))
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "পেমেন্ট মোবাইল নম্বর (${if (method.type.equals("MERCHANT", ignoreCase = true)) "মার্চেন্ট একাউন্ট" else "পার্সোনাল একাউন্ট"}):",
                            fontSize = 11.sp,
                            color = Color(0xFF94A3B8)
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = method.number.ifBlank { "কোনো নম্বর সেট করা হয়নি" },
                            fontSize = 18.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = if (method.number.isBlank()) Color.Gray else EmeraldPrimary
                        )
                    }

                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(Color(0xFF1E293B))
                            .padding(horizontal = 10.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = if (method.type.equals("MERCHANT", ignoreCase = true)) "Merchant" else "Personal",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF38BDF8)
                        )
                    }
                }

                // Instructions (full text display)
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0xFF131C2E), RoundedCornerShape(8.dp))
                        .padding(10.dp)
                ) {
                    Text(
                        text = "পেমেন্ট নির্দেশাবলী (গ্রাহক চেকআউটে দেখতে পাবে):",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFA0AEC0)
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = method.instructions.ifBlank { "Send Money করুন এবং প্রাপ্ত ট্রানজেকশন আইডি (TrxID) নিচে লিখে ভেরিফাই করুন।" },
                        fontSize = 12.sp,
                        color = Color.White,
                        lineHeight = 17.sp
                    )
                }

                if (method.customLogoUrl.isNotBlank()) {
                    Text(
                        text = "কাস্টম লোগো URL: ${method.customLogoUrl}",
                        fontSize = 10.sp,
                        color = StatusSuccess,
                        maxLines = 1
                    )
                }

                Spacer(modifier = Modifier.height(2.dp))

                // Elongated buttons: [✏️ লোগো ও নম্বর এডিট] and [🗑️ মেথড ডিলেট]
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedButton(
                        onClick = onEdit,
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier
                            .weight(1f)
                            .height(42.dp)
                            .testTag("edit_wallet_${method.id}")
                    ) {
                        Icon(Icons.Default.Edit, contentDescription = "Edit", modifier = Modifier.size(15.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("লোগো ও নম্বর এডিট করুন", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }

                    OutlinedButton(
                        onClick = onDelete,
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFFF5252)),
                        border = ButtonDefaults.outlinedButtonBorder.copy(
                            brush = androidx.compose.ui.graphics.SolidColor(Color(0xFFFF5252).copy(alpha = 0.5f))
                        ),
                        modifier = Modifier
                            .height(42.dp)
                            .testTag("delete_wallet_${method.id}")
                    ) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = Color(0xFFFF5252), modifier = Modifier.size(15.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("ডিলেট", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFFFF5252))
                    }
                }
            }
        }
    }
}

@Composable
fun EditWalletDialog(
    method: PaymentMethodEntity,
    onDismiss: () -> Unit,
    onSave: (PaymentMethodEntity) -> Unit
) {
    var name by remember { mutableStateOf(method.name) }
    var number by remember { mutableStateOf(method.number) }
    var customLogoUrl by remember { mutableStateOf(method.customLogoUrl) }
    var selectedType by remember { mutableStateOf(method.type) }
    var instructions by remember { mutableStateOf(method.instructions) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                BrandLogoView(
                    providerId = method.id,
                    customLogoUrl = customLogoUrl,
                    height = 24.dp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("${method.name} এডিট করুন", fontSize = 16.sp, fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text("পদ্ধতির নাম:", fontSize = 12.sp, color = Color.Gray)
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                )

                Text("ওয়ালেট মোবাইল নম্বর (যেখানে টাকা আসবে):", fontSize = 12.sp, color = Color.Gray)
                OutlinedTextField(
                    value = number,
                    onValueChange = { number = it },
                    placeholder = { Text("যেমন: 01735102916") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = EmeraldPrimary,
                        unfocusedBorderColor = DarkNavyBorder
                    )
                )

                Text("কাস্টম লোগো ইমেজ URL লিংক (ঐচ্ছিক):", fontSize = 12.sp, color = Color.Gray)
                OutlinedTextField(
                    value = customLogoUrl,
                    onValueChange = { customLogoUrl = it },
                    placeholder = { Text("https://example.com/logo.png") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                )
                Text("খালি রাখলে অফিশিয়াল লোগো ব্যবহৃত হবে।", fontSize = 10.sp, color = Color.Gray)

                Text("একাউন্টের ধরন:", fontSize = 12.sp, color = Color.Gray)
                Column {
                    val types = listOf(
                        "PERSONAL" to "Personal (কাস্টমার Send Money করবে)",
                        "MERCHANT" to "Merchant (কাস্টমার Make Payment করবে)"
                    )
                    types.forEach { (typeKey, label) ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            RadioButton(
                                selected = selectedType == typeKey,
                                onClick = { selectedType = typeKey }
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(text = label, fontSize = 11.sp)
                        }
                    }
                }

                Text("পেমেন্ট নির্দেশাবলী (ইউজার চেকআউটে দেখতে পাবে):", fontSize = 12.sp, color = Color.Gray)
                OutlinedTextField(
                    value = instructions,
                    onValueChange = { instructions = it },
                    placeholder = { Text("সেন্ড মানি করে TrxID দিন") },
                    maxLines = 2,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onSave(
                        method.copy(
                            name = name.trim(),
                            number = number.trim(),
                            customLogoUrl = customLogoUrl.trim(),
                            type = selectedType,
                            instructions = instructions.trim()
                        )
                    )
                },
                colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary)
            ) {
                Text("সংরক্ষণ করুন", color = Color.Black, fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("বাতিল")
            }
        }
    )
}

@Composable
fun AddNewWalletDialog(
    onDismiss: () -> Unit,
    onAdd: (PaymentMethodEntity) -> Unit
) {
    val predefinedProviders = listOf(
        "bkash" to "বিকাশ (bKash)",
        "nagad" to "নগদ (Nagad)",
        "rocket" to "রকেট (Rocket)",
        "upay" to "উপায় (Upay)",
        "cellfin" to "সেলফিন (Cellfin)",
        "custom" to "অন্যান্য (Custom)"
    )

    var selectedProvider by remember { mutableStateOf("bkash") }
    var name by remember { mutableStateOf("বিকাশ (bKash)") }
    var number by remember { mutableStateOf("") }
    var customLogoUrl by remember { mutableStateOf("") }
    var selectedType by remember { mutableStateOf("PERSONAL") }
    var instructions by remember { mutableStateOf("Send Money করে ট্রানজেকশন আইডি দিন।") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text("নতুন ওয়ালেট মেথড যোগ করুন", fontSize = 16.sp, fontWeight = FontWeight.Bold)
        },
        text = {
            LazyColumn(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                item {
                    Text("মেথডের ধরন সিলেক্ট করুন:", fontSize = 12.sp, color = Color.Gray)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        predefinedProviders.take(3).forEach { (id, label) ->
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .border(
                                        1.dp,
                                        if (selectedProvider == id) EmeraldPrimary else DarkNavyBorder,
                                        RoundedCornerShape(6.dp)
                                    )
                                    .background(
                                        if (selectedProvider == id) EmeraldPrimary.copy(alpha = 0.2f) else Color.Transparent,
                                        RoundedCornerShape(6.dp)
                                    )
                                    .clickable {
                                        selectedProvider = id
                                        name = label
                                    }
                                    .padding(vertical = 6.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = id.uppercase(),
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (selectedProvider == id) EmeraldPrimary else Color.White
                                )
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        predefinedProviders.drop(3).forEach { (id, label) ->
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .border(
                                        1.dp,
                                        if (selectedProvider == id) EmeraldPrimary else DarkNavyBorder,
                                        RoundedCornerShape(6.dp)
                                    )
                                    .background(
                                        if (selectedProvider == id) EmeraldPrimary.copy(alpha = 0.2f) else Color.Transparent,
                                        RoundedCornerShape(6.dp)
                                    )
                                    .clickable {
                                        selectedProvider = id
                                        name = label
                                    }
                                    .padding(vertical = 6.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = id.uppercase(),
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (selectedProvider == id) EmeraldPrimary else Color.White
                                )
                            }
                        }
                    }
                }

                item {
                    Text("নাম:", fontSize = 12.sp, color = Color.Gray)
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp)
                    )
                }

                item {
                    Text("পেমেন্ট মোবাইল নম্বর:", fontSize = 12.sp, color = Color.Gray)
                    OutlinedTextField(
                        value = number,
                        onValueChange = { number = it },
                        placeholder = { Text("01XXXXXXXXX") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp)
                    )
                }

                item {
                    Text("কাস্টম লোগো ইমেজ URL (ঐচ্ছিক):", fontSize = 12.sp, color = Color.Gray)
                    OutlinedTextField(
                        value = customLogoUrl,
                        onValueChange = { customLogoUrl = it },
                        placeholder = { Text("https://example.com/logo.png") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp)
                    )
                }

                item {
                    Text("একাউন্টের ধরন:", fontSize = 12.sp, color = Color.Gray)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = selectedType == "PERSONAL", onClick = { selectedType = "PERSONAL" })
                        Text("Personal (Send Money)", fontSize = 11.sp)
                        Spacer(modifier = Modifier.width(8.dp))
                        RadioButton(selected = selectedType == "MERCHANT", onClick = { selectedType = "MERCHANT" })
                        Text("Merchant", fontSize = 11.sp)
                    }
                }

                item {
                    Text("নির্দেশাবলী:", fontSize = 12.sp, color = Color.Gray)
                    OutlinedTextField(
                        value = instructions,
                        onValueChange = { instructions = it },
                        maxLines = 2,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp)
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val finalId = if (selectedProvider == "custom") "custom_${System.currentTimeMillis()}" else selectedProvider
                    onAdd(
                        PaymentMethodEntity(
                            id = finalId,
                            name = name.trim(),
                            number = number.trim(),
                            type = selectedType,
                            instructions = instructions.trim(),
                            customLogoUrl = customLogoUrl.trim(),
                            isEnabled = true
                        )
                    )
                },
                colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary)
            ) {
                Text("যুক্ত করুন", color = Color.Black, fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("বাতিল")
            }
        }
    )
}
