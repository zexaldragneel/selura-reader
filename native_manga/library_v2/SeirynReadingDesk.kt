package eu.kanade.presentation.library.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import eu.kanade.tachiyomi.R
import eu.kanade.tachiyomi.ui.library.LibraryItem
import tachiyomi.domain.library.model.LibraryManga

/**
 * Pure, one-pass summary of the current visible category, using already-loaded
 * Mihon library data. Never queries chapters, images, sources or the database.
 */
internal data class SeirynReadingDeskSnapshot(
    val titles: Int,
    val unreadChapters: Long,
    val inProgress: Int,
    val resume: LibraryManga?,
)

internal fun summarizeSeirynReadingDesk(items: List<LibraryItem>): SeirynReadingDeskSnapshot {
    var unread = 0L
    var inProgress = 0
    var resume: LibraryManga? = null
    for (item in items) {
        val manga = item.libraryManga
        unread += item.unreadCount.coerceAtLeast(0L)
        if (manga.hasStarted && manga.unreadCount > 0L) {
            inProgress++
            val lastRead = manga.lastRead
            val previousRead = resume?.lastRead
            if (resume == null || (lastRead != null &&
                    (previousRead == null || lastRead > previousRead))
            ) {
                resume = manga
            }
        }
    }
    return SeirynReadingDeskSnapshot(
        titles = items.size,
        unreadChapters = unread,
        inProgress = inProgress,
        resume = resume,
    )
}

/**
 * Premium Library 2.0: a compact, accessible reading desk.
 *
 * This never introduces fake covers or cover progress bars. The button reuses
 * LibraryTab's existing next-unread-chapter navigation and respects the user's
 * "show continue reading" setting (null callback hides the button).
 */
@Composable
internal fun SeirynReadingDesk(
    items: List<LibraryItem>,
    onContinueReading: ((LibraryManga) -> Unit)?,
) {
    val snapshot = remember(items) { summarizeSeirynReadingDesk(items) }
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 5.dp),
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceContainerLow,
        tonalElevation = 2.dp,
        border = BorderStroke(
            width = 1.dp,
            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.36f),
        ),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(3.dp),
        ) {
            Text(
                text = stringResource(R.string.seiryn_library_v2_heading),
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = stringResource(
                    R.string.seiryn_library_v2_summary,
                    snapshot.titles,
                    snapshot.unreadChapters,
                    snapshot.inProgress,
                ),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
            )
            val toResume = snapshot.resume
            if (onContinueReading != null && toResume != null) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = toResume.manga.title,
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.bodyMedium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    FilledTonalButton(onClick = { onContinueReading(toResume) }) {
                        Text(stringResource(R.string.seiryn_library_v2_resume))
                    }
                }
            }
        }
    }
}
