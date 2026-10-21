package eu.kanade.presentation.theme

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
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
 *
 * v3.1: if an asset cannot be decoded at runtime, every entry point falls
 * back to the v2 vector drawing (or draws nothing for the nav ornaments).
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
private fun cachedHeader(): ImageBitmap? {
    val res = LocalContext.current.resources
    return XianxiaArtCache.header
        ?: runCatching { ImageBitmap.imageResource(res, R.drawable.xianxia_header) }
            .getOrNull()
            ?.also { XianxiaArtCache.header = it }
}

@Composable
private fun cachedCorners(): ImageBitmap? {
    val res = LocalContext.current.resources
    return XianxiaArtCache.corners
        ?: runCatching { ImageBitmap.imageResource(res, R.drawable.xianxia_card_corners) }
            .getOrNull()
            ?.also { XianxiaArtCache.corners = it }
}

@Composable
private fun cachedNavFrame(): ImageBitmap? {
    val res = LocalContext.current.resources
    return XianxiaArtCache.navFrame
        ?: runCatching { ImageBitmap.imageResource(res, R.drawable.xianxia_nav_frame) }
            .getOrNull()
            ?.also { XianxiaArtCache.navFrame = it }
}

/** Illustrated header painted behind the toolbar; falls back to the v2 vector backdrop. */
@Composable
fun Modifier.xianxiaToolbarArt(artwork: Boolean): Modifier {
    val header = if (artwork) cachedHeader() else null
    if (header == null) return xianxiaToolbarBackdrop(artwork)
    return drawBehind {
        val w = size.width
        val h = size.height
        drawRect(Brush.verticalGradient(listOf(Color(0xFF05070F), ArtInk)))
        // only the painted band of the asset is used; its lower part is empty mist
        val srcH = minOf(header.height, PaintedBandPx)
        val scale = maxOf(w / header.width, h / srcH)
        val dw = (header.width * scale).roundToInt()
        val dh = (srcH * scale).roundToInt()
        clipRect(0f, 0f, w, h) {
            drawImage(
                header,
                srcOffset = IntOffset.Zero,
                srcSize = IntSize(header.width, srcH),
                dstOffset = IntOffset(((w - dw) / 2f).roundToInt(), 0),
                dstSize = IntSize(dw, dh),
                filterQuality = FilterQuality.Medium,
            )
        }
        // status-bar legibility over the moon
        drawRect(
            Brush.verticalGradient(
                listOf(Color(0x99000000), Color.Transparent),
                startY = 0f,
                endY = h * 0.32f,
            ),
        )
        // title legibility
        drawRect(
            Brush.horizontalGradient(
                listOf(Color(0xA6060914), Color(0x00060914)),
                startX = 0f,
                endX = w * 0.52f,
            ),
        )
        // action icon legibility
        drawRect(
            Brush.horizontalGradient(
                listOf(Color(0x00060914), Color(0x70060914)),
                startX = w * 0.62f,
                endX = w,
            ),
        )
        // short melt into the tab area so the painting stays visible
        drawRect(
            Brush.verticalGradient(
                listOf(Color.Transparent, ArtInk),
                startY = h * 0.8f,
                endY = h,
            ),
        )
    }
}

/** Slim divider between the illustrated header and the category tabs. */
@Composable
fun XianxiaArtStrip(modifier: Modifier = Modifier) {
    val artwork = LocalSeluraLibraryAppearance.current?.backgroundArtwork != false
    if (artwork && cachedHeader() == null) {
        XianxiaScenery(modifier)
        return
    }
    Canvas(modifier.fillMaxWidth().height(14.dp)) {
        val w = size.width
        val h = size.height
        drawRect(Brush.verticalGradient(listOf(ArtInk, ArtInkLow)))
        val cx = w / 2f
        val cy = h - 3.dp.toPx()
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
 * Card frame: hairline gold border plus a compact corner flourish mirrored
 * into all four corners. Drawn only on the container edge, so the real manga
 * cover is never replaced or recoloured. Falls back to the v2 frame.
 */
@Composable
fun Modifier.xianxiaCardArtFrame(): Modifier {
    val corners = cachedCorners() ?: return xianxiaCardFrame()
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
        val c = 26.dp.toPx().roundToInt()
        val shift = 1.5.dp.toPx().roundToInt()
        val dst = IntSize(c, c)
        val at = IntOffset(-shift, -shift)
        drawImage(corners, dstOffset = at, dstSize = dst, filterQuality = FilterQuality.High)
        scale(-1f, 1f, Offset(size.width / 2f, 0f)) {
            drawImage(corners, dstOffset = at, dstSize = dst, filterQuality = FilterQuality.High)
        }
        scale(1f, -1f, Offset(0f, size.height / 2f)) {
            drawImage(corners, dstOffset = at, dstSize = dst, filterQuality = FilterQuality.High)
        }
        scale(-1f, -1f, Offset(size.width / 2f, size.height / 2f)) {
            drawImage(corners, dstOffset = at, dstSize = dst, filterQuality = FilterQuality.High)
        }
    }
}

/**
 * Ornamental end caps perched on the top corners of the bottom navigation bar.
 * They sit entirely above the bar's item row, so icons and labels are never
 * covered, and they never intercept touches. Draws nothing if the asset is
 * unavailable.
 */
@Composable
fun XianxiaNavFrame(modifier: Modifier = Modifier) {
    val frame = cachedNavFrame() ?: return
    Canvas(
        modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(bottom = NavBarHeight - 2.dp)
            .height(NavCapHeight),
    ) {
        val w = size.width
        val h = size.height
        val dstH = h.roundToInt()
        val srcW = minOf(NavCapSrcPx, frame.width / 2)
        val dstW = (srcW * dstH / frame.height.toFloat()).roundToInt()
        drawImage(
            frame,
            srcOffset = IntOffset.Zero,
            srcSize = IntSize(srcW, frame.height),
            dstSize = IntSize(dstW, dstH),
            filterQuality = FilterQuality.High,
        )
        drawImage(
            frame,
            srcOffset = IntOffset(frame.width - srcW, 0),
            srcSize = IntSize(srcW, frame.height),
            dstOffset = IntOffset(w.roundToInt() - dstW, 0),
            dstSize = IntSize(dstW, dstH),
            filterQuality = FilterQuality.High,
        )
        drawLine(
            Brush.horizontalGradient(listOf(Color.Transparent, ArtGoldMid, Color.Transparent)),
            Offset(0f, h - 0.5.dp.toPx()),
            Offset(w, h - 0.5.dp.toPx()),
            strokeWidth = 1.dp.toPx(),
        )
    }
}

private const val PaintedBandPx = 330
private const val NavCapSrcPx = 300
private val NavBarHeight = 80.dp
private val NavCapHeight = 40.dp
