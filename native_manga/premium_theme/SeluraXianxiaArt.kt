package eu.kanade.presentation.theme

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.imageResource
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import eu.kanade.tachiyomi.R
import kotlin.math.roundToInt

/**
 * Celestial Xianxia v3: displays the bundled illustrated assets
 * (xianxia_header, xianxia_card_corners, xianxia_nav_frame).
 *
 * Each bitmap is decoded once per process and shared, so scrolling the
 * library never decodes artwork per card. Nothing here reads manga data,
 * cover models or progress; it only paints theme chrome.
 */
private val ArtGoldLight = Color(0xFFF6D79D)
private val ArtGoldMid = Color(0xFFD6A85E)
private val ArtGoldDark = Color(0xFF8E6938)
private val ArtInk = Color(0xFF070B17)
private val ArtInkLow = Color(0xFF0A1226)

private object XianxiaArtCache {
    var header: ImageBitmap? = null
    var corners: ImageBitmap? = null
    var navFrame: ImageBitmap? = null
}

@Composable
private fun cachedHeader(): ImageBitmap {
    val res = LocalContext.current.resources
    return XianxiaArtCache.header
        ?: ImageBitmap.imageResource(res, R.drawable.xianxia_header).also { XianxiaArtCache.header = it }
}

@Composable
private fun cachedCorners(): ImageBitmap {
    val res = LocalContext.current.resources
    return XianxiaArtCache.corners
        ?: ImageBitmap.imageResource(res, R.drawable.xianxia_card_corners).also { XianxiaArtCache.corners = it }
}

@Composable
private fun cachedNavFrame(): ImageBitmap {
    val res = LocalContext.current.resources
    return XianxiaArtCache.navFrame
        ?: ImageBitmap.imageResource(res, R.drawable.xianxia_nav_frame).also { XianxiaArtCache.navFrame = it }
}

/** Illustrated header painted behind the toolbar, top-aligned and cropped to fit. */
@Composable
fun Modifier.xianxiaToolbarArt(artwork: Boolean): Modifier {
    val header = if (artwork) cachedHeader() else null
    return drawBehind {
        val w = size.width
        val h = size.height
        drawRect(Brush.verticalGradient(listOf(Color(0xFF05070F), ArtInk)))
        if (header != null) {
            val scale = maxOf(w / header.width, h / header.height)
            val dw = (header.width * scale).roundToInt()
            val dh = (header.height * scale).roundToInt()
            clipRect(0f, 0f, w, h) {
                drawImage(
                    header,
                    dstOffset = IntOffset(((w - dw) / 2f).roundToInt(), 0),
                    dstSize = IntSize(dw, dh),
                    filterQuality = FilterQuality.Medium,
                )
            }
            // status-bar legibility over the moon
            drawRect(
                Brush.verticalGradient(
                    listOf(Color(0xB3000000), Color.Transparent),
                    startY = 0f,
                    endY = h * 0.4f,
                ),
            )
            // title legibility
            drawRect(
                Brush.horizontalGradient(
                    listOf(Color(0xB8060914), Color(0x00060914)),
                    startX = 0f,
                    endX = w * 0.62f,
                ),
            )
            // action icon legibility
            drawRect(
                Brush.horizontalGradient(
                    listOf(Color(0x00060914), Color(0x80060914)),
                    startX = w * 0.6f,
                    endX = w,
                ),
            )
            // melt the painting into the strip below
            drawRect(
                Brush.verticalGradient(
                    listOf(Color.Transparent, ArtInk),
                    startY = h * 0.6f,
                    endY = h,
                ),
            )
        }
    }
}

/** Short dark mist strip between the illustrated header and the category tabs. */
@Composable
fun XianxiaArtStrip(modifier: Modifier = Modifier) {
    val artwork = LocalSeluraLibraryAppearance.current?.backgroundArtwork != false
    val header = if (artwork) cachedHeader() else null
    Canvas(modifier.fillMaxWidth().height(34.dp)) {
        val w = size.width
        val h = size.height
        drawRect(Brush.verticalGradient(listOf(ArtInk, ArtInkLow)))
        if (header != null) {
            // the dark, softly coloured lower band of the same illustration
            drawImage(
                header,
                srcOffset = IntOffset(0, 380),
                srcSize = IntSize(header.width, header.height - 380),
                dstSize = IntSize(w.roundToInt(), h.roundToInt()),
                alpha = 0.55f,
                filterQuality = FilterQuality.Low,
            )
            drawRect(Brush.verticalGradient(listOf(ArtInk, Color.Transparent), startY = 0f, endY = h * 0.6f))
        }
        val cx = w / 2f
        val cy = h - 1.5.dp.toPx()
        val d = 3.5.dp.toPx()
        drawLine(
            Brush.horizontalGradient(listOf(Color.Transparent, ArtGoldMid, Color.Transparent)),
            Offset(0f, cy),
            Offset(w, cy),
            strokeWidth = 1.dp.toPx(),
        )
        val diamond = Path().apply {
            moveTo(cx, cy - d)
            lineTo(cx + d, cy)
            lineTo(cx, cy + d)
            lineTo(cx - d, cy)
            close()
        }
        drawPath(diamond, ArtGoldLight)
    }
}

/**
 * Card frame: hairline gold border plus the illustrated corner flourish
 * mirrored into all four corners. Drawn only on the container edge, so the
 * real manga cover is never replaced, recoloured or covered beyond the
 * corner ornaments.
 */
@Composable
fun Modifier.xianxiaCardArtFrame(): Modifier {
    val corners = cachedCorners()
    return drawWithContent {
        drawContent()
        val inset = 1.5.dp.toPx()
        val radius = 13.dp.toPx()
        drawRoundRect(
            brush = Brush.linearGradient(listOf(ArtGoldLight, ArtGoldDark, ArtGoldLight)),
            topLeft = Offset(inset, inset),
            size = Size(size.width - inset * 2, size.height - inset * 2),
            cornerRadius = CornerRadius(radius, radius),
            style = Stroke(width = 1.2.dp.toPx()),
        )
        val c = 36.dp.toPx().roundToInt()
        val dst = IntSize(c, c)
        drawImage(corners, dstSize = dst, filterQuality = FilterQuality.High)
        scale(-1f, 1f, Offset(size.width / 2f, 0f)) {
            drawImage(corners, dstSize = dst, filterQuality = FilterQuality.High)
        }
        scale(1f, -1f, Offset(0f, size.height / 2f)) {
            drawImage(corners, dstSize = dst, filterQuality = FilterQuality.High)
        }
        scale(-1f, -1f, Offset(size.width / 2f, size.height / 2f)) {
            drawImage(corners, dstSize = dst, filterQuality = FilterQuality.High)
        }
    }
}

/** Gold ornamental frame laid over the bottom navigation bar; never intercepts touches. */
@Composable
fun XianxiaNavFrame(modifier: Modifier = Modifier) {
    Image(
        bitmap = cachedNavFrame(),
        contentDescription = null,
        modifier = modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .height(80.dp),
        contentScale = ContentScale.FillWidth,
    )
}
