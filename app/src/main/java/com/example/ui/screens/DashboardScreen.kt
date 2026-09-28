package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.TransactionEntity
import com.example.ui.DashboardStats
import com.example.ui.MainViewModel
import com.example.ui.components.MethodBadge
import com.example.ui.components.StatusBadge
import com.example.ui.theme.DarkNavyBorder
import com.example.ui.theme.DarkNavyCard
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.theme.StatusFailed
import com.example.ui.theme.StatusPending
import com.example.ui.theme.StatusSuccess
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun DashboardScreen(
    viewModel: MainViewModel,
    onNavigateToCheckout: () -> Unit
) {
    val context = LocalContext.current
    val stats by viewModel.stats.collectAsState()
    val transactions by viewModel.filteredTransactions.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val statusFilter by viewModel.statusFilter.collectAsState()
    val methodFilter by viewModel.methodFilter.collectAsState()
    val latestAlert by viewModel.latestTransactionAlert.collectAsState()

    var selectedTransactionForDetails by remember { mutableStateOf<TransactionEntity?>(null) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("dashboard_screen")
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Spacer(modifier = Modifier.height(8.dp))
            // Dashboard Top Stats Card
            DashboardStatsCard(
                stats = stats,
                onTestCheckout = onNavigateToCheckout
            )
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = {
                        val report = viewModel.generateDailyReport()
                        val sendIntent = android.content.Intent().apply {
                            action = android.content.Intent.ACTION_SEND
                            putExtra(android.content.Intent.EXTRA_TEXT, report)
                            type = "text/plain"
                        }
                        val shareIntent = android.content.Intent.createChooser(sendIntent, "আজকের পেমেন্ট রিপোর্ট শেয়ার করুন")
                        context.startActivity(shareIntent)
                    },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = EmeraldPrimary)
                ) {
                    Icon(Icons.Default.Send, contentDescription = "Share", modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("📊 আজকের রিপোর্ট শেয়ার", fontSize = 12.sp)
                }

                OutlinedButton(
                    onClick = {
                        val report = viewModel.generateDailyReport()
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(ClipData.newPlainText("Daily Report", report))
                        viewModel.showMessage("আজকের রিপোর্ট ক্লিপবোর্ডে কপি করা হয়েছে!")
                    },
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
                ) {
                    Icon(Icons.Default.ContentCopy, contentDescription = "Copy", modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("কপি", fontSize = 12.sp)
                }
            }
        }

        item {
            // Search Input
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { viewModel.setSearchQuery(it) },
                placeholder = { Text("TrxID, অর্ডার ID, বা কাস্টমার নম্বর দিয়ে খুঁজুন...", fontSize = 13.sp) },
                leadingIcon = {
                    Icon(Icons.Default.Search, contentDescription = "Search", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { viewModel.setSearchQuery("") }) {
                            Icon(Icons.Default.Close, contentDescription = "Clear", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("search_input"),
                shape = RoundedCornerShape(12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = EmeraldPrimary,
                    unfocusedBorderColor = DarkNavyBorder,
                    focusedContainerColor = DarkNavyCard,
                    unfocusedContainerColor = DarkNavyCard
                ),
                singleLine = true
            )
        }

        item {
            // Filter Rows: Status and Providers
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                // Status Filters
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    val statusOptions = listOf(
                        "ALL" to "সকল লেনদেন",
                        "PENDING" to "অপেক্ষমান",
                        "COMPLETED" to "সফল",
                        "REJECTED" to "বাতিল"
                    )
                    items(statusOptions) { (key, label) ->
                        FilterChip(
                            selected = statusFilter == key,
                            onClick = { viewModel.setStatusFilter(key) },
                            label = { Text(label, fontSize = 12.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = EmeraldPrimary.copy(alpha = 0.2f),
                                selectedLabelColor = EmeraldPrimary
                            )
                        )
                    }
                }

                // Payment Provider Filters
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    val providers = listOf(
                        "ALL" to "সকল মেথড",
                        "BKASH" to "বিকাশ",
                        "NAGAD" to "নগদ",
                        "ROCKET" to "রকেট",
                        "UPAY" to "উপায়"
                    )
                    items(providers) { (key, label) ->
                        FilterChip(
                            selected = methodFilter == key,
                            onClick = { viewModel.setMethodFilter(key) },
                            label = { Text(label, fontSize = 12.sp) }
                        )
                    }
                }
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "লেনদেন তালিকা (${transactions.size}টি)",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onBackground
                )
            }
        }

        if (transactions.isEmpty()) {
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 24.dp),
                    colors = CardDefaults.cardColors(containerColor = DarkNavyCard),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(32.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            imageVector = Icons.Default.ShoppingCart,
                            contentDescription = "Empty",
                            modifier = Modifier.size(48.dp),
                            tint = Color.Gray
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "কোনো লেনদেন পাওয়া যায়নি",
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "নতুন পেমেন্ট তৈরি করতে 'চেকআউট টেস্ট করুন' চাপুন",
                            fontSize = 12.sp,
                            color = Color.Gray
                        )
                    }
                }
            }
        } else {
            items(transactions, key = { it.id }) { tx ->
                TransactionCard(
                    transaction = tx,
                    onClick = { selectedTransactionForDetails = tx },
                    onCopyTrxId = {
                        if (tx.trxId.isNotEmpty()) {
                            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                            clipboard.setPrimaryClip(ClipData.newPlainText("TrxID", tx.trxId))
                            viewModel.showMessage("TrxID কপি করা হয়েছে: ${tx.trxId}")
                        }
                    }
                )
            }
        }

        item {
            Spacer(modifier = Modifier.height(80.dp))
        }
    }

    // Transaction Details & Action Modal Dialog
    selectedTransactionForDetails?.let { tx ->
        TransactionDetailsDialog(
            transaction = tx,
            onDismiss = { selectedTransactionForDetails = null },
            onApprove = {
                viewModel.markTransactionStatus(tx.id, "COMPLETED")
                selectedTransactionForDetails = null
            },
            onReject = {
                viewModel.markTransactionStatus(tx.id, "REJECTED")
                selectedTransactionForDetails = null
            },
            onResendWebhook = {
                viewModel.resendWebhook(tx.id)
            },
            onDelete = {
                viewModel.deleteTransaction(tx.id)
                selectedTransactionForDetails = null
            }
        )
    }

    // Live Real-Time Transaction Popup Alert Dialog
    latestAlert?.let { tx ->
        AlertDialog(
            onDismissRequest = { viewModel.dismissTransactionAlert() },
            containerColor = DarkNavyCard,
            shape = RoundedCornerShape(20.dp),
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .background(EmeraldPrimary.copy(alpha = 0.2f), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = "Success",
                            tint = EmeraldPrimary,
                            modifier = Modifier.size(22.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "নতুন পেমেন্ট সম্পন্ন হয়েছে! 🎉",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                }
            },
            text = {
                Column(
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "৳ ${String.format(Locale.US, "%.2f", tx.totalAmount)}",
                        fontSize = 26.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = EmeraldPrimary
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("পেমেন্ট মেথড:", color = Color.Gray, fontSize = 12.sp)
                        MethodBadge(method = tx.method)
                    }
                    if (tx.trxId.isNotEmpty()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("TrxID:", color = Color.Gray, fontSize = 12.sp)
                            Text(
                                tx.trxId,
                                fontWeight = FontWeight.Bold,
                                color = Color.White,
                                fontSize = 13.sp
                            )
                        }
                    }
                    if (tx.customerPhone.isNotEmpty()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text("কাস্টমার ফোন:", color = Color.Gray, fontSize = 12.sp)
                            Text(tx.customerPhone, color = Color.White, fontSize = 12.sp)
                        }
                    }
                    if (tx.websiteName.isNotEmpty()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text("অর্ডার সূত্র:", color = Color.Gray, fontSize = 12.sp)
                            Text(tx.websiteName, color = Color.LightGray, fontSize = 12.sp)
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (tx.trxId.isNotEmpty()) {
                            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                            clipboard.setPrimaryClip(ClipData.newPlainText("TrxID", tx.trxId))
                            viewModel.showMessage("TrxID কপি করা হয়েছে: ${tx.trxId}")
                        }
                        viewModel.dismissTransactionAlert()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(Icons.Default.ContentCopy, contentDescription = "Copy", modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("TrxID কপি করুন", color = Color.Black, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.dismissTransactionAlert() }) {
                    Text("ঠিক আছে", color = Color.Gray, fontSize = 13.sp)
                }
            }
        )
    }
}

@Composable
fun DashboardStatsCard(
    stats: DashboardStats,
    onTestCheckout: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "মোট সংগ্রহ (সফল)",
                        fontSize = 12.sp,
                        color = Color.Gray
                    )
                    Text(
                        text = "৳ ${String.format(Locale.US, "%.2f", stats.totalCollected)}",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = EmeraldPrimary
                    )
                }

                Button(
                    onClick = onTestCheckout,
                    colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.testTag("test_checkout_button")
                ) {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = "Test",
                        tint = Color.Black,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("চেকআউট টেস্ট", color = Color.Black, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Sub-metrics row
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF0D1420), RoundedCornerShape(12.dp))
                    .padding(vertical = 12.dp, horizontal = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                MetricItem(label = "সফল অর্ডার", value = "${stats.completedCount}", color = StatusSuccess)
                MetricItem(label = "অপেক্ষমান", value = "${stats.pendingCount}", color = StatusPending)
                MetricItem(label = "বাতিল", value = "${stats.failedCount}", color = StatusFailed)
                MetricItem(label = "সফলতার হার", value = "${stats.successRate}%", color = EmeraldPrimary)
            }
        }
    }
}

@Composable
fun MetricItem(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = value, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = color)
        Text(text = label, fontSize = 10.sp, color = Color.Gray)
    }
}

@Composable
fun TransactionCard(
    transaction: TransactionEntity,
    onClick: () -> Unit,
    onCopyTrxId: () -> Unit
) {
    val dateFormat = remember { SimpleDateFormat("hh:mm a, dd MMM", Locale.getDefault()) }
    val formattedDate = dateFormat.format(Date(transaction.createdAt))

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .testTag("tx_item_${transaction.id}"),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = DarkNavyCard)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Header: Site name & Date & Status
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    MethodBadge(method = transaction.method)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = transaction.orderId,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                }
                StatusBadge(status = transaction.status)
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Body: Amount and Customer Phone
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom
            ) {
                Column {
                    Text(
                        text = "সাইট: ${transaction.websiteName}",
                        fontSize = 11.sp,
                        color = Color.Gray,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    if (transaction.customerPhone.isNotEmpty()) {
                        Text(
                            text = "গ্রাহক: ${transaction.customerPhone}",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Text(
                    text = "৳ ${String.format(Locale.US, "%.2f", transaction.totalAmount)}",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = EmeraldPrimary
                )
            }

            // TrxID bar (if provided)
            if (transaction.trxId.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0xFF090E17), RoundedCornerShape(8.dp))
                        .padding(horizontal = 8.dp, vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "TrxID: ${transaction.trxId}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF64B5F6)
                    )
                    IconButton(
                        onClick = onCopyTrxId,
                        modifier = Modifier.size(24.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.ContentCopy,
                            contentDescription = "Copy TrxID",
                            modifier = Modifier.size(14.dp),
                            tint = Color.Gray
                        )
                    }
                }
            }

            // Footer: Timestamp and Webhook status
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = formattedDate,
                    fontSize = 10.sp,
                    color = Color.Gray
                )

                if (transaction.webhookStatus == "DELIVERED") {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(6.dp)
                                .background(StatusSuccess, CircleShape)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(text = "ওয়েবহুক সফল", fontSize = 10.sp, color = StatusSuccess)
                    }
                } else if (transaction.webhookStatus == "FAILED") {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(6.dp)
                                .background(StatusFailed, CircleShape)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(text = "ওয়েবহুক ব্যর্থ (${transaction.webhookResponseCode})", fontSize = 10.sp, color = StatusFailed)
                    }
                }
            }
        }
    }
}

@Composable
fun TransactionDetailsDialog(
    transaction: TransactionEntity,
    onDismiss: () -> Unit,
    onApprove: () -> Unit,
    onReject: () -> Unit,
    onResendWebhook: () -> Unit,
    onDelete: () -> Unit
) {
    val dateFormat = remember { SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("অর্ডার বিবরণ #${transaction.orderId}", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                StatusBadge(status = transaction.status)
            }
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                DetailRow(label = "পেমেন্ট মাধ্যম", value = transaction.method)
                DetailRow(label = "মূল পরিমাণ", value = "৳ ${transaction.amount}")
                DetailRow(label = "মোট পরিমাণ", value = "৳ ${transaction.totalAmount}")
                DetailRow(label = "ওয়েবসাইট", value = transaction.websiteName)
                DetailRow(label = "কাস্টমার নম্বর", value = transaction.customerPhone.ifBlank { "দেওয়া হয়নি" })
                DetailRow(label = "TrxID", value = transaction.trxId.ifBlank { "এখনো দেয়নি" })
                DetailRow(label = "তৈরির সময়", value = dateFormat.format(Date(transaction.createdAt)))

                if (transaction.matchedSmsSnippet.isNotBlank()) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("ম্যাচ হওয়া SMS:", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = EmeraldPrimary)
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFF090E17), RoundedCornerShape(8.dp))
                            .padding(8.dp)
                    ) {
                        Text(transaction.matchedSmsSnippet, fontSize = 10.sp, color = Color.LightGray)
                    }
                }

                if (transaction.webhookUrl.isNotBlank()) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("ওয়েবহুক ইউআরএল:", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    Text(transaction.webhookUrl, fontSize = 10.sp, color = Color.Gray)
                    Text("স্ট্যাটাস: ${transaction.webhookStatus} (Code: ${transaction.webhookResponseCode})", fontSize = 10.sp, color = if (transaction.webhookStatus == "DELIVERED") StatusSuccess else StatusFailed)
                }
            }
        },
        confirmButton = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                IconButton(onClick = onDelete) {
                    Icon(Icons.Default.Delete, contentDescription = "Delete", tint = StatusFailed)
                }

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (transaction.status == "PENDING") {
                        OutlinedButton(
                            onClick = onReject,
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = StatusFailed)
                        ) {
                            Text("বাতিল", fontSize = 12.sp)
                        }
                        Button(
                            onClick = onApprove,
                            colors = ButtonDefaults.buttonColors(containerColor = StatusSuccess)
                        ) {
                            Text("এপ্রুভ করুন", fontSize = 12.sp, color = Color.Black, fontWeight = FontWeight.Bold)
                        }
                    } else {
                        Button(
                            onClick = onResendWebhook,
                            colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary)
                        ) {
                            Icon(Icons.Default.Send, contentDescription = null, modifier = Modifier.size(14.dp), tint = Color.Black)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("ওয়েবহুক পুনরায় পাঠান", fontSize = 11.sp, color = Color.Black)
                        }
                    }
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("বন্ধ করুন", fontSize = 12.sp)
            }
        }
    )
}

@Composable
fun DetailRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = label, fontSize = 11.sp, color = Color.Gray)
        Text(text = value, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurface)
    }
}
