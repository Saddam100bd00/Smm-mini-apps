package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.BkashPink
import com.example.ui.theme.NagadOrange
import com.example.ui.theme.RocketPurple
import com.example.ui.theme.StatusFailed
import com.example.ui.theme.StatusPending
import com.example.ui.theme.StatusSuccess
import com.example.ui.theme.UpayBlue

@Composable
fun MethodBadge(
    method: String,
    modifier: Modifier = Modifier
) {
    val (bgColor, textColor, label) = when (method.uppercase()) {
        "BKASH" -> Triple(BkashPink, Color.White, "বিকাশ")
        "NAGAD" -> Triple(NagadOrange, Color.White, "নগদ")
        "ROCKET" -> Triple(RocketPurple, Color.White, "রকেট")
        "UPAY" -> Triple(UpayBlue, Color.White, "উপায়")
        else -> Triple(Color(0xFF475569), Color.White, method)
    }

    Box(
        modifier = modifier
            .background(bgColor, RoundedCornerShape(6.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(
            text = label,
            color = textColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
fun StatusBadge(
    status: String,
    modifier: Modifier = Modifier
) {
    val (bgColor, textColor, label) = when (status.uppercase()) {
        "COMPLETED" -> Triple(StatusSuccess.copy(alpha = 0.15f), StatusSuccess, "সফল")
        "PENDING" -> Triple(StatusPending.copy(alpha = 0.15f), StatusPending, "অপেক্ষমান")
        "REJECTED" -> Triple(StatusFailed.copy(alpha = 0.15f), StatusFailed, "বাতিল")
        else -> Triple(Color.Gray.copy(alpha = 0.2f), Color.LightGray, status)
    }

    Box(
        modifier = modifier
            .background(bgColor, RoundedCornerShape(12.dp))
            .padding(horizontal = 10.dp, vertical = 3.dp)
    ) {
        Text(
            text = label,
            color = textColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold
        )
    }
}
