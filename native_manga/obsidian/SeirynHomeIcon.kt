package eu.kanade.tachiyomi.ui.home

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.PathFillType
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.path
import androidx.compose.ui.unit.dp

/** Original reading-room mark; no dependency on an unbundled symbol. */
val SeirynHomeIcon: ImageVector = ImageVector.Builder(
    name = "SeirynReadingRoom", defaultWidth = 24.dp, defaultHeight = 24.dp,
    viewportWidth = 24f, viewportHeight = 24f,
).apply {
    path(fill = SolidColor(Color.Black), pathFillType = PathFillType.EvenOdd) {
        moveTo(12f, 2f); lineTo(1f, 11f); lineTo(3f, 13f)
        lineTo(4f, 12f); lineTo(4f, 22f); lineTo(20f, 22f)
        lineTo(20f, 12f); lineTo(21f, 13f); lineTo(23f, 11f)
        close()
        moveTo(7f, 12f); lineTo(11f, 13f); lineTo(11f, 19f)
        lineTo(7f, 18f); close()
        moveTo(13f, 13f); lineTo(17f, 12f); lineTo(17f, 18f)
        lineTo(13f, 19f); close()
    }
}.build()
