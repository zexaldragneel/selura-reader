package eu.kanade.presentation.theme

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Celestial Xianxia ornament kit.
 *
 * Everything here is original, static vector drawing: no bitmaps, no network,
 * no per-manga state and no animation. It only decorates theme chrome (toolbar,
 * category tabs, card frames, scenery strip) and never touches cover data.
 */
private val GoldLight = Color(0xFFF6D79D)
private val GoldMid = Color(0xFFD6A85E)
private val GoldDark = Color(0xFF8E6938)
private val InkTop = Color(0xFF05070F)
private val InkMid = Color(0xFF0B1224)
private val Cream = Color(0xFFF7EBD0)
private val Crimson = Color(0xFFB3202A)
private val Blossom = Color(0xFFE88DA3)

// ---------------------------------------------------------------- drawing

/** Tiered pagoda silhouette; [unit] is the full height, [cx]/[baseY] the foot. */
private fun DrawScope.pagoda(cx: Float, baseY: Float, unit: Float, color: Color, tiers: Int) {
    val half = unit * 0.34f
    var top = baseY - unit * 0.06f
    drawRect(color, Offset(cx - half * 1.1f, top), Size(half * 2.2f, unit * 0.06f))
    for (t in 0 until tiers) {
        val w = half * (1f - t * 0.2f)
        val bodyH = unit * 0.15f
        val roofH = unit * 0.12f
        val bodyTop = top - bodyH
        drawRect(color, Offset(cx - w * 0.6f, bodyTop), Size(w * 1.2f, bodyH))
        val roof = Path().apply {
            moveTo(cx - w * 1.3f, bodyTop - roofH * 0.5f)
            quadTo(cx - w * 0.7f, bodyTop + roofH * 0.15f, cx, bodyTop - roofH)
            quadTo(cx + w * 0.7f, bodyTop + roofH * 0.15f, cx + w * 1.3f, bodyTop - roofH * 0.5f)
            quadTo(cx, bodyTop + roofH * 0.1f, cx - w * 1.3f, bodyTop - roofH * 0.5f)
            close()
        }
        drawPath(roof, color)
        top = bodyTop - roofH * 0.6f
    }
    drawLine(
        color,
        Offset(cx, top),
        Offset(cx, top - unit * 0.14f),
        strokeWidth = (unit * 0.03f).coerceAtLeast(1f),
    )
}

/** Smooth curling cloud outline in the traditional "xiangyun" manner. */
private fun DrawScope.wisp(x: Float, y: Float, s: Float, color: Color, strokeWidth: Float) {
    val path = Path().apply {
        moveTo(x, y)
        cubicTo(x + s * 0.2f, y - s * 0.35f, x + s * 0.55f, y - s * 0.35f, x + s * 0.6f, y - s * 0.1f)
        cubicTo(x + s * 0.75f, y - s * 0.4f, x + s * 1.1f, y - s * 0.3f, x + s * 1.1f, y)
        cubicTo(x + s * 1.25f, y + s * 0.05f, x + s * 1.3f, y + s * 0.2f, x + s * 1.15f, y + s * 0.22f)
        lineTo(x + s * 0.1f, y + s * 0.22f)
    }
    drawPath(path, color, style = Stroke(width = strokeWidth, cap = StrokeCap.Round))
}

/** Smooth layered ridge line filled to the bottom edge. */
private fun DrawScope.ridge(baseFrac: Float, amp: Float, flip: Boolean, color: Color) {
    val w = size.width
    val h = size.height
    val base = h * baseFrac
    val steps = 6
    val step = w / steps
    val path = Path().apply {
        moveTo(0f, h)
        lineTo(0f, base)
        for (i in 0 until steps) {
            val x = i * step
            val up = if ((i % 2 == 0) != flip) -amp else amp * 0.35f
            cubicTo(x + step * 0.3f, base + up, x + step * 0.7f, base + up * 0.55f, x + step, base - up * 0.2f)
        }
        lineTo(w, h)
        close()
    }
    drawPath(path, color)
}

private fun DrawScope.petal(x: Float, y: Float, r: Float, alpha: Float) {
    drawCircle(Blossom, radius = r, center = Offset(x, y), alpha = alpha)
    drawCircle(Cream, radius = r * 0.35f, center = Offset(x, y), alpha = alpha * 0.8f)
}

private fun DrawScope.cornerBracket(x: Float, y: Float, dx: Float, dy: Float, len: Float, sw: Float) {
    val path = Path().apply {
        moveTo(x, y + dy * len)
        lineTo(x, y)
        lineTo(x + dx * len, y)
    }
    drawPath(path, GoldLight, style = Stroke(width = sw, cap = StrokeCap.Round))
    drawCircle(GoldLight, radius = sw * 1.3f, center = Offset(x, y))
}

// ---------------------------------------------------------------- modifiers

/** Dark ink toolbar backdrop: crimson sun, moon, gold cloud scrolls, blossoms. */
fun Modifier.xianxiaToolbarBackdrop(artwork: Boolean): Modifier = drawBehind {
    val w = size.width
    val h = size.height
    drawRect(Brush.verticalGradient(listOf(InkTop, InkMid, Color(0xFF060914))))
    if (artwork) {
        val sunC = Offset(w * 0.2f, h * 0.45f)
        drawCircle(
            Brush.radialGradient(
                listOf(Color(0xCCB3202A), Color(0x00B3202A)),
                center = sunC,
                radius = h * 1.15f,
            ),
            radius = h * 1.15f,
            center = sunC,
        )
        val moonC = Offset(w * 0.82f, h * 0.02f)
        drawCircle(
            Brush.radialGradient(
                listOf(Color(0x55F7EBD0), Color(0x00F7EBD0)),
                center = moonC,
                radius = h * 1.1f,
            ),
            radius = h * 1.1f,
            center = moonC,
        )
        drawCircle(Color(0xFFEDE6D0), radius = h * 0.5f, center = moonC, alpha = 0.9f)
        val sw = 1.2.dp.toPx()
        wisp(w * 0.02f, h * 0.92f, h * 0.9f, GoldMid.copy(alpha = 0.5f), sw)
        wisp(w * 0.42f, h * 0.2f, h * 0.7f, GoldMid.copy(alpha = 0.3f), sw)
        wisp(w * 0.66f, h * 0.95f, h * 0.8f, GoldMid.copy(alpha = 0.4f), sw)
        val r = 2.2.dp.toPx()
        petal(w * 0.05f, h * 0.2f, r, 0.9f)
        petal(w * 0.11f, h * 0.55f, r * 0.8f, 0.8f)
        petal(w * 0.3f, h * 0.12f, r * 0.7f, 0.7f)
        petal(w * 0.52f, h * 0.7f, r * 0.8f, 0.6f)
        // keep the action icons readable over the moon
        drawRect(
            Brush.horizontalGradient(
                listOf(Color.Transparent, Color(0x99060914)),
                startX = w * 0.55f,
                endX = w,
            ),
        )
    }
    drawLine(
        Brush.horizontalGradient(listOf(Color.Transparent, GoldMid, Color.Transparent)),
        Offset(0f, h - 1f),
        Offset(w, h - 1f),
        strokeWidth = 1.dp.toPx(),
    )
}

/**
 * Thin gold frame plus corner brackets drawn on the card container.
 * Drawn after content, but only along the card edge: it never fills or
 * recolors the real cover.
 */
fun Modifier.xianxiaCardFrame(): Modifier = drawWithContent {
    drawContent()
    val inset = 1.5.dp.toPx()
    val radius = 13.dp.toPx()
    val frame = Brush.linearGradient(listOf(GoldLight, GoldDark, GoldLight))
    drawRoundRect(
        brush = frame,
        topLeft = Offset(inset, inset),
        size = Size(size.width - inset * 2, size.height - inset * 2),
        cornerRadius = CornerRadius(radius, radius),
        style = Stroke(width = 1.2.dp.toPx()),
    )
    val pad = 5.dp.toPx()
    val len = 14.dp.toPx()
    val sw = 1.3.dp.toPx()
    cornerBracket(pad, pad, 1f, 1f, len, sw)
    cornerBracket(size.width - pad, pad, -1f, 1f, len, sw)
    cornerBracket(pad, size.height - pad, 1f, -1f, len, sw)
    cornerBracket(size.width - pad, size.height - pad, -1f, -1f, len, sw)
    wisp(size.width - 30.dp.toPx(), size.height - 6.dp.toPx(), 22.dp.toPx(), GoldMid.copy(alpha = 0.7f), 1.dp.toPx())
}

/** Category tab: dark inlay with gold hairline; active tab adds brackets and underline. */
fun Modifier.xianxiaTabFrame(active: Boolean): Modifier = drawBehind {
    val radius = CornerRadius(10.dp.toPx(), 10.dp.toPx())
    drawRoundRect(
        brush = Brush.horizontalGradient(
            if (active) listOf(Color(0xFF2A2012), Color(0xFF111A2E)) else listOf(Color(0xFF0C1322), Color(0xFF0A101D)),
        ),
        cornerRadius = radius,
    )
    drawRoundRect(
        color = if (active) GoldLight else GoldDark.copy(alpha = 0.55f),
        cornerRadius = radius,
        style = Stroke(width = if (active) 1.5.dp.toPx() else 1.dp.toPx()),
    )
    if (active) {
        val pad = 3.dp.toPx()
        val len = 9.dp.toPx()
        val sw = 1.2.dp.toPx()
        cornerBracket(pad, pad, 1f, 1f, len, sw)
        cornerBracket(size.width - pad, pad, -1f, 1f, len, sw)
        cornerBracket(pad, size.height - pad, 1f, -1f, len, sw)
        cornerBracket(size.width - pad, size.height - pad, -1f, -1f, len, sw)
        drawLine(
            GoldLight,
            Offset(size.width * 0.22f, size.height - 1.5.dp.toPx()),
            Offset(size.width * 0.78f, size.height - 1.5.dp.toPx()),
            strokeWidth = 2.dp.toPx(),
            cap = StrokeCap.Round,
        )
    }
}

// ---------------------------------------------------------------- composables

@Composable
fun XianxiaPagodaGlyph(tint: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(18.dp)) {
        pagoda(size.width / 2f, size.height, size.height * 0.98f, tint, 3)
    }
}

/** Brush-style "Library" wordmark with letterspaced subtitle, count pill and seal. */
@Composable
fun XianxiaLibraryTitle(title: String, count: Int?) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Column(modifier = Modifier.weight(1f, false)) {
            Text(
                text = title,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = TextStyle(
                    fontFamily = FontFamily.Serif,
                    fontStyle = FontStyle.Italic,
                    fontWeight = FontWeight.Black,
                    fontSize = 30.sp,
                    lineHeight = 32.sp,
                    color = Cream,
                    shadow = Shadow(Color.Black, Offset(2f, 3f), 6f),
                ),
            )
            Text(
                text = "MY MANGA COLLECTION",
                maxLines = 1,
                style = TextStyle(
                    fontFamily = FontFamily.Serif,
                    fontSize = 8.sp,
                    letterSpacing = 2.sp,
                    color = GoldMid,
                ),
            )
        }
        if (count != null) {
            Box(
                modifier = Modifier
                    .border(1.dp, GoldMid, RoundedCornerShape(50))
                    .padding(horizontal = 8.dp, vertical = 2.dp),
            ) {
                Text(text = "$count", fontSize = 13.sp, color = GoldLight, maxLines = 1)
            }
        }
        Box(
            modifier = Modifier
                .size(18.dp)
                .background(Crimson, RoundedCornerShape(3.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Text(text = "漫", fontSize = 11.sp, color = Cream, maxLines = 1)
        }
    }
}

/**
 * Scenery strip above the category pager: layered misty ridges, pagodas, moon
 * glow, cloud scrolls and blossoms. Static; honours the artwork preference.
 */
@Composable
fun XianxiaScenery(modifier: Modifier = Modifier) {
    val artwork = LocalSeluraLibraryAppearance.current?.backgroundArtwork != false
    Canvas(modifier.fillMaxWidth().height(76.dp)) {
        val w = size.width
        val h = size.height
        drawRect(Brush.verticalGradient(listOf(Color(0xFF060914), Color(0xFF0B1426), Color(0xFF070B17))))
        if (artwork) {
            val moonC = Offset(w * 0.78f, h * 0.15f)
            drawCircle(
                Brush.radialGradient(
                    listOf(Color(0x44F7EBD0), Color(0x00F7EBD0)),
                    center = moonC,
                    radius = h * 1.2f,
                ),
                radius = h * 1.2f,
                center = moonC,
            )
            ridge(0.52f, h * 0.22f, false, Color(0xFF111B31))
            pagoda(w * 0.18f, h * 0.62f, h * 0.7f, Color(0xFF0C1427), 4)
            pagoda(w * 0.62f, h * 0.6f, h * 0.55f, Color(0xFF0C1427), 3)
            ridge(0.7f, h * 0.18f, true, Color(0xFF080D1A))
            pagoda(w * 0.86f, h * 0.78f, h * 0.45f, Color(0xFF050811), 3)
            drawRect(
                Brush.verticalGradient(
                    listOf(Color.Transparent, Color(0x66AFC3E8), Color.Transparent),
                    startY = h * 0.5f,
                    endY = h * 0.95f,
                ),
                alpha = 0.18f,
            )
            val sw = 1.dp.toPx()
            wisp(w * 0.36f, h * 0.55f, h * 0.7f, GoldMid.copy(alpha = 0.35f), sw)
            wisp(w * 0.74f, h * 0.88f, h * 0.6f, GoldMid.copy(alpha = 0.3f), sw)
            val r = 2.dp.toPx()
            petal(w * 0.04f, h * 0.25f, r, 0.9f)
            petal(w * 0.09f, h * 0.5f, r * 0.8f, 0.8f)
            petal(w * 0.14f, h * 0.15f, r * 0.7f, 0.7f)
            petal(w * 0.94f, h * 0.4f, r * 0.8f, 0.7f)
        }
        drawLine(
            Brush.horizontalGradient(listOf(Color.Transparent, GoldMid, Color.Transparent)),
            Offset(0f, h - 1f),
            Offset(w, h - 1f),
            strokeWidth = 1.dp.toPx(),
        )
    }
}
