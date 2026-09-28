package com.example

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Payment
import androidx.compose.material.icons.filled.Sms
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.ui.MainViewModel
import com.example.ui.screens.CheckoutSimulatorScreen
import com.example.ui.screens.DashboardScreen
import com.example.ui.screens.IntegrationGuideScreen
import com.example.ui.screens.SmsEngineScreen
import com.example.ui.screens.WalletsScreen
import com.example.ui.theme.DarkNavyBackground
import com.example.ui.theme.DarkNavyCard
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.theme.MyApplicationTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                AutoPayApp()
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AutoPayApp(viewModel: MainViewModel = viewModel()) {
    val context = LocalContext.current
    var selectedTab by remember { mutableIntStateOf(0) }
    val snackbarHostState = remember { SnackbarHostState() }
    val snackbarMsg by viewModel.snackbarMessage.collectAsState()

    // Back handling: If not on Dashboard (0), go back to Dashboard
    BackHandler(enabled = selectedTab != 0) {
        selectedTab = 0
    }

    // Permission launcher for SMS and Notifications
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val smsGranted = permissions[Manifest.permission.RECEIVE_SMS] == true
        if (smsGranted) {
            viewModel.showMessage("স্বয়ংক্রিয় SMS পারমিশন চালু হয়েছে!")
        }
    }

    LaunchedEffect(Unit) {
        val needed = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.RECEIVE_SMS)
        }
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.READ_SMS)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        }
        try {
            com.example.service.PaymentForegroundService.startService(context)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    LaunchedEffect(snackbarMsg) {
        snackbarMsg?.let { msg ->
            snackbarHostState.showSnackbar(msg)
            viewModel.clearMessage()
        }
    }

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(WindowInsets.safeDrawing),
        containerColor = DarkNavyBackground,
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = when (selectedTab) {
                            0 -> "AutoPay BD • ড্যাশবোর্ড"
                            1 -> "ওয়ালেট সেটিংস"
                            2 -> "চেকআউট সিমুলেটর"
                            3 -> "অটো SMS ইঞ্জিন"
                            else -> "অন্য সাইটে যুক্ত করার নিয়ম"
                        },
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkNavyBackground,
                    titleContentColor = Color.White
                )
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = DarkNavyCard,
                contentColor = EmeraldPrimary,
                modifier = Modifier
                    .navigationBarsPadding()
                    .testTag("bottom_nav_bar")
            ) {
                val navItems = listOf(
                    Triple("ড্যাশবোর্ড", Icons.Default.Dashboard, "nav_dashboard"),
                    Triple("ওয়ালেট", Icons.Default.AccountBalanceWallet, "nav_wallets"),
                    Triple("চেকআউট", Icons.Default.Payment, "nav_checkout"),
                    Triple("SMS ল্যাব", Icons.Default.Sms, "nav_sms"),
                    Triple("ইন্টিগ্রেশন", Icons.Default.Code, "nav_integration")
                )

                navItems.forEachIndexed { index, (label, icon, testTag) ->
                    NavigationBarItem(
                        selected = selectedTab == index,
                        onClick = { selectedTab = index },
                        icon = {
                            Icon(
                                imageVector = icon,
                                contentDescription = label,
                                modifier = Modifier.size(20.dp)
                            )
                        },
                        label = {
                            Text(
                                text = label,
                                fontSize = 10.sp,
                                fontWeight = if (selectedTab == index) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = EmeraldPrimary,
                            selectedTextColor = EmeraldPrimary,
                            indicatorColor = EmeraldPrimary.copy(alpha = 0.2f),
                            unselectedIconColor = Color.Gray,
                            unselectedTextColor = Color.Gray
                        ),
                        modifier = Modifier.testTag(testTag)
                    )
                }
            }
        },
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(DarkNavyBackground)
        ) {
            when (selectedTab) {
                0 -> DashboardScreen(
                    viewModel = viewModel,
                    onNavigateToCheckout = { selectedTab = 2 }
                )
                1 -> WalletsScreen(viewModel = viewModel)
                2 -> CheckoutSimulatorScreen(
                    viewModel = viewModel,
                    onBackToDashboard = { selectedTab = 0 }
                )
                3 -> SmsEngineScreen(viewModel = viewModel)
                4 -> IntegrationGuideScreen(viewModel = viewModel)
            }
        }
    }
}
