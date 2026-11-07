package eu.kanade.presentation.manga.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import mihon.app.di.appGraph
import tachiyomi.presentation.core.util.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance
import eu.kanade.presentation.theme.SeluraLibraryTheme
import eu.kanade.tachiyomi.R
import eu.kanade.tachiyomi.ui.manga.ChapterList

@Composable
fun SeirynDetailActions(
    chapters: List<ChapterList.Item>,
    onContinue: () -> Unit,
    onFilter: () -> Unit,
    sourceUnavailable: Boolean,
    onFindSource: (() -> Unit)?,
) {
    if (LocalSeluraLibraryAppearance.current?.theme != SeluraLibraryTheme.SEIRYN_OBSIDIAN) return
    val context = LocalContext.current
    val wifiPreference = remember { context.appGraph.downloadPreferences.downloadOnlyOverWifi }
    val wifiOnly by wifiPreference.collectAsState()
    val read = chapters.count { it.chapter.read }
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
        shape = RoundedCornerShape(24.dp),
        color = MaterialTheme.colorScheme.surfaceContainerLow,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (sourceUnavailable && onFindSource != null) {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.surfaceContainerHighest,
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                    ) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(stringResource(R.string.seiryn_source_unavailable), style = MaterialTheme.typography.titleSmall)
                            Text(stringResource(R.string.seiryn_source_suggestion), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
            Text(stringResource(R.string.seiryn_chapter_progress, read, chapters.size), style = MaterialTheme.typography.labelLarge)
            if (chapters.isNotEmpty()) LinearProgressIndicator(
                progress = { read.toFloat() / chapters.size },
                modifier = Modifier.fillMaxWidth(),
            )
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                DetailMetric(
                    label = stringResource(R.string.seiryn_unread),
                    value = (chapters.size - read).coerceAtLeast(0),
                )
                DetailMetric(
                    label = stringResource(R.string.seiryn_downloads),
                    value = chapters.count { it.isDownloaded },
                )
                DetailMetric(
                    label = stringResource(R.string.seiryn_bookmarked),
                    value = chapters.count { it.chapter.bookmark },
                )
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onContinue, enabled = chapters.any { !it.chapter.read }) {
                    Text(stringResource(if (read > 0) R.string.seiryn_resume else R.string.seiryn_start))
                }
                OutlinedButton(onClick = onFilter) { Text(stringResource(R.string.seiryn_chapter_controls)) }
                if (onFindSource != null) {
                    OutlinedButton(onClick = onFindSource) {
                        Text(stringResource(R.string.seiryn_find_source))
                    }
                }
                FilterChip(
                    selected = wifiOnly,
                    onClick = { wifiPreference.set(!wifiOnly) },
                    label = {
                        Text(stringResource(
                            if (wifiOnly) R.string.seiryn_wifi_resume_on else R.string.seiryn_wifi_resume_off,
                        ))
                    },
                )
            }
        }
    }
}

@Composable
private fun DetailMetric(label: String, value: Int) {
    Surface(
        shape = RoundedCornerShape(50),
        color = MaterialTheme.colorScheme.surfaceContainerHighest,
    ) {
        Text(
            text = "$value $label",
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
