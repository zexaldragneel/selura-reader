package eu.kanade.presentation.manga.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
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
) {
    if (LocalSeluraLibraryAppearance.current?.theme != SeluraLibraryTheme.SEIRYN_OBSIDIAN) return
    val read = chapters.count { it.chapter.read }
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
        shape = RoundedCornerShape(24.dp),
        color = MaterialTheme.colorScheme.surfaceContainerLow,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(stringResource(R.string.seiryn_chapter_progress, read, chapters.size), style = MaterialTheme.typography.labelLarge)
            if (chapters.isNotEmpty()) LinearProgressIndicator(
                progress = { read.toFloat() / chapters.size },
                modifier = Modifier.fillMaxWidth(),
            )
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onContinue, enabled = chapters.any { !it.chapter.read }) {
                    Text(stringResource(if (read > 0) R.string.seiryn_resume else R.string.seiryn_start))
                }
                OutlinedButton(onClick = onFilter) { Text(stringResource(R.string.seiryn_chapter_controls)) }
            }
        }
    }
}
