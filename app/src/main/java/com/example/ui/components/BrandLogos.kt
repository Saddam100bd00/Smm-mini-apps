package com.example.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.R

@Composable
fun BrandLogoView(
    providerId: String,
    modifier: Modifier = Modifier,
    customLogoUrl: String? = null,
    height: Dp = 38.dp,
    showContainer: Boolean = true
) {
    val cleanId = providerId.lowercase()
    val fallbackUrl = when {
        cleanId.contains("bkash") -> "https://i.postimg.cc/3Rh5jP9R/1790271574534.png"
        cleanId.contains("nagad") -> "https://i.postimg.cc/KvjX577W/1790444646578.png"
        cleanId.contains("rocket") -> "https://i.postimg.cc/rp6vcvBN/1790272198554.png"
        cleanId.contains("upay") -> "https://i.postimg.cc/bvQ4vm8x/1790444672029.png"
        else -> null
    }

    val defaultDrawableRes = when {
        cleanId.contains("bkash") -> R.drawable.logo_bkash
        cleanId.contains("nagad") -> R.drawable.logo_nagad
        cleanId.contains("rocket") -> R.drawable.logo_rocket
        cleanId.contains("upay") -> R.drawable.logo_upay
        else -> R.drawable.logo_bkash
    }

    val targetUrl = if (!customLogoUrl.isNullOrBlank()) customLogoUrl else fallbackUrl

    val contentComposable = @Composable {
        if (!targetUrl.isNullOrBlank()) {
            AsyncImage(
                model = targetUrl,
                contentDescription = providerId,
                modifier = Modifier.height(height),
                contentScale = ContentScale.Fit,
                error = painterResource(id = defaultDrawableRes),
                placeholder = painterResource(id = defaultDrawableRes)
            )
        } else {
            Image(
                painter = painterResource(id = defaultDrawableRes),
                contentDescription = providerId,
                modifier = Modifier.height(height),
                contentScale = ContentScale.Fit
            )
        }
    }

    if (showContainer) {
        Box(
            modifier = modifier
                .shadow(elevation = 2.dp, shape = RoundedCornerShape(8.dp))
                .clip(RoundedCornerShape(8.dp))
                .background(Color.White)
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(8.dp))
                .padding(horizontal = 14.dp, vertical = 6.dp),
            contentAlignment = Alignment.Center
        ) {
            contentComposable()
        }
    } else {
        Box(modifier = modifier, contentAlignment = Alignment.Center) {
            contentComposable()
        }
    }
}
