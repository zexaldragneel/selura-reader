package eu.kanade.presentation.library.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import eu.kanade.tachiyomi.ui.library.LibraryItem
import tachiyomi.domain.library.model.LibraryManga

/** A real-data cover shelf that keeps Mihon's selection and reader callbacks. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
internal fun SeirynLibraryGrid(
    items: List<LibraryItem>,
    contentPadding: PaddingValues,
    selection: Set<Long>,
    onClick: (LibraryManga) -> Unit,
    onLongClick: (LibraryManga) -> Unit,
    onContinueReading: ((LibraryManga) -> Unit)?,
    searchQuery: String?,
    onGlobalSearch: () -> Unit,
) {
    LazyVerticalGrid(
        columns = GridCells.Adaptive(minSize = 156.dp),
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(
            start = 14.dp + contentPadding.calculateStartPadding(androidx.compose.ui.platform.LocalLayoutDirection.current),
            end = 14.dp + contentPadding.calculateEndPadding(androidx.compose.ui.platform.LocalLayoutDirection.current),
            top = 12.dp,
            bottom = contentPadding.calculateBottomPadding() + 20.dp,
        ),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        globalSearchItem(searchQuery, onGlobalSearch)
        items(items, key = { it.id }, contentType = { "seiryn_library_card" }) { item ->
            val entry = item.libraryManga
            val selected = entry.id in selection
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .combinedClickable(
                        onClick = { onClick(entry) },
                        onLongClick = { onLongClick(entry) },
                    ),
                shape = RoundedCornerShape(20.dp),
                color = if (selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerLow,
                border = BorderStroke(
                    if (selected) 2.dp else 1.dp,
                    if (selected) MaterialTheme.colorScheme.primary
                    else Brush.linearGradient(listOf(
                        MaterialTheme.colorScheme.outlineVariant,
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.32f),
                    )),
                ),
            ) {
                Column(Modifier.padding(9.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box {
                        MangaCover.Book(
                            data = entry.manga,
                            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)),
                            contentDescription = entry.manga.title,
                        )
                        Row(
                            Modifier.align(Alignment.TopStart).padding(7.dp),
                            horizontalArrangement = Arrangement.spacedBy(5.dp),
                        ) {
                            if (item.unreadCount > 0) {
                                Surface(shape = RoundedCornerShape(30.dp), color = MaterialTheme.colorScheme.primary) {
                                    Text("${item.unreadCount} NEW", Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                        style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimary)
                                }
                            }
                            if (item.downloadCount > 0) {
                                Surface(shape = RoundedCornerShape(30.dp), color = MaterialTheme.colorScheme.surface.copy(alpha = 0.94f)) {
                                    Text("${item.downloadCount} OFFLINE", Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                        style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurface)
                                }
                            }
                        }
                    }
                    Text(
                        entry.manga.title,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 2,
                        minLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    val total = entry.totalChapters
                    if (total > 0L) {
                        val progress = (entry.readCount.toFloat() / total).coerceIn(0f, 1f)
                        LinearProgressIndicator(
                            progress = { progress },
                            modifier = Modifier.fillMaxWidth().height(4.dp),
                            color = MaterialTheme.colorScheme.primary,
                            trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
                        )
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${(progress * 100).toInt()}%", style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary)
                            if (entry.bookmarkCount > 0) Text("▮ ${entry.bookmarkCount}", style = MaterialTheme.typography.labelSmall)
                        }
                    }
                    if (onContinueReading != null && item.unreadCount > 0L) {
                        FilledTonalButton(
                            modifier = Modifier.fillMaxWidth(),
                            onClick = { onContinueReading(entry) },
                            contentPadding = PaddingValues(vertical = 7.dp),
                        ) { Text(if (entry.hasStarted) "CONTINUE" else "START READING", style = MaterialTheme.typography.labelMedium) }
                    }
                }
            }
        }
    }
}
