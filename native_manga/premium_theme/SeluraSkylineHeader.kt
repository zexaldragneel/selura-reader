package eu.kanade.presentation.theme

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Original vector-only atmospheric header, intentionally independent of
 * manga image loading and of all manga/extension storage. Nothing is animated
 * or allocated per library item. Drawn just once above the category pager.
 */
@Composable
fun SeluraSkylineHeader(modifier: Modifier = Modifier) {
    val appearance = LocalSeluraLibraryAppearance.current
    val theme = appearance?.theme ?: SeluraLibraryTheme.DEFAULT
    if (theme == SeluraLibraryTheme.DEFAULT) return

    val celestial = theme == SeluraLibraryTheme.CELESTIAL_XIANXIA
    val primary = MaterialTheme.colorScheme.primary
    val artwork = appearance?.backgroundArtwork != false
    val height = if (celestial) 108.dp else 68.dp

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(height)
            .background(
                Brush.verticalGradient(
                    if (celestial) {
                        listOf(Color(0xFF14243E), Color(0xFF233957), Color(0xFF080F20))
                    } else {
                        listOf(Color(0xFF24104B), Color(0xFF171530), Color(0xFF080A18))
                    },
                ),
            ),
    ) {
        if (artwork) {
            Canvas(Modifier.fillMaxSize()) {
                val w = size.width
                val h = size.height
                if (celestial) {
                    val moonCenter = Offset(w * 0.75f, h * 0.31f)
                    drawCircle(Color(0xFFF5DDA7).copy(alpha = 0.10f), h * 0.34f, moonCenter)
                    drawCircle(Color(0xFFF5DDA7).copy(alpha = 0.16f), h * 0.27f, moonCenter)
                    drawCircle(Color(0xFFF8E9C8).copy(alpha = 0.82f), h * 0.21f, moonCenter)

                    val back = Path().apply {
                        moveTo(0f, h * 0.83f)
                        lineTo(w * 0.12f, h * 0.27f)
                        lineTo(w * 0.21f, h * 0.63f)
                        lineTo(w * 0.31f, h * 0.21f)
                        lineTo(w * 0.44f, h * 0.77f)
                        lineTo(w * 0.55f, h * 0.38f)
                        lineTo(w * 0.67f, h * 0.81f)
                        lineTo(w * 0.82f, h * 0.42f)
                        lineTo(w, h * 0.8f)
                        lineTo(w, h)
                        lineTo(0f, h)
                        close()
                    }
                    drawPath(back, Color(0xFF304A69).copy(alpha = 0.65f))

                    val front = Path().apply {
                        moveTo(0f, h * 0.94f)
                        lineTo(w * 0.18f, h * 0.51f)
                        lineTo(w * 0.30f, h * 0.91f)
                        lineTo(w * 0.46f, h * 0.44f)
                        lineTo(w * 0.62f, h * 0.91f)
                        lineTo(w * 0.85f, h * 0.51f)
                        lineTo(w, h * 0.82f)
                        lineTo(w, h)
                        lineTo(0f, h)
                        close()
                    }
                    drawPath(front, Color(0xFF101B30).copy(alpha = 0.94f))

                    // Three distant pagodas use flat silhouettes rather than a bitmap.
                    listOf(0.18f to 0.56f, 0.50f to 0.48f, 0.88f to 0.58f).forEach { (x, y) ->
                        val px = w * x
                        val roofWidth = w * 0.058f
                        val baseY = h * 0.94f
                        val topY = h * y
                        drawRect(
                            color = Color(0xFF060F20),
                            topLeft = Offset(px - roofWidth * 0.27f, topY + h * 0.045f),
                            size = Size(roofWidth * 0.54f, baseY - topY),
                        )
                        for (level in 0..2) {
                            val ry = topY + level * h * 0.085f
                            val roof = Path().apply {
                                moveTo(px - roofWidth * 0.60f, ry + h * 0.025f)
                                lineTo(px - roofWidth * 0.40f, ry)
                                lineTo(px + roofWidth * 0.40f, ry)
                                lineTo(px + roofWidth * 0.60f, ry + h * 0.025f)
                                close()
                            }
                            drawPath(roof, Color(0xFF060F20))
                            drawLine(
                                color = Color(0xFFD2AF78).copy(alpha = 0.58f),
                                start = Offset(px - roofWidth * 0.4f, ry),
                                end = Offset(px + roofWidth * 0.4f, ry),
                                strokeWidth = 1.6f,
                            )
                        }
                    }

                    for (index in 0..13) {
                        val x = w * ((index * 37 % 100) / 100f)
                        val y = h * (0.08f + (index * 17 % 46) / 100f)
                        drawCircle(Color(0xFFFFE5B4).copy(alpha = 0.48f), 1.2f, Offset(x, y))
                    }
                    for (index in 0..3) {
                        val x = w * (0.07f + index * 0.23f)
                        drawArc(
                            color = Color(0xFFA1BCD7).copy(alpha = 0.35f),
                            startAngle = 195f,
                            sweepAngle = 140f,
                            useCenter = false,
                            topLeft = Offset(x, h * 0.62f),
                            size = Size(w * 0.34f, h * 0.28f),
                            style = Stroke(width = 1.4f),
                        )
                    }
                } else {
                    drawCircle(Color(0xFF8B4DFF).copy(alpha = 0.14f), h * 0.66f, Offset(w * 0.72f, h * 0.35f))
                    drawCircle(Color(0xFF61A7FF).copy(alpha = 0.18f), h * 0.42f, Offset(w * 0.28f, h * 0.45f))
                    for (index in 0..14) {
                        val x = w * (index / 14f)
                        val y = h * (0.42f + ((index * 7) % 6) * 0.05f)
                        drawLine(
                            color = primary.copy(alpha = 0.19f),
                            start = Offset(x, y),
                            end = Offset(x + w * 0.07f, y - h * 0.14f),
                            strokeWidth = 1.3f,
                        )
                    }
                }
            }
        }
        Text(
            text = if (celestial) "✦     S E L U R A     ✦" else "✧   S E L U R A   ✧",
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(bottom = 9.dp),
            textAlign = TextAlign.Center,
            color = primary,
            fontFamily = if (celestial) FontFamily.Serif else FontFamily.SansSerif,
            fontSize = if (celestial) 14.sp else 13.sp,
            letterSpacing = 2.sp,
        )
    }
}
