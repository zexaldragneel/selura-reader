package eu.kanade.tachiyomi.ui.home

import androidx.activity.compose.ReportDrawnWhen
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import cafe.adriel.voyager.navigator.LocalNavigator
import cafe.adriel.voyager.navigator.currentOrThrow
import cafe.adriel.voyager.navigator.tab.LocalTabNavigator
import cafe.adriel.voyager.navigator.tab.TabOptions
import dev.zacsweers.metrox.viewmodel.metroViewModel
import eu.kanade.presentation.manga.components.MangaCover
import eu.kanade.presentation.util.Tab
import eu.kanade.tachiyomi.R
import eu.kanade.tachiyomi.ui.browse.BrowseTab
import eu.kanade.tachiyomi.ui.download.DownloadQueueScreen
import eu.kanade.tachiyomi.ui.history.HistoryTab
import eu.kanade.tachiyomi.ui.library.LibraryTab
import eu.kanade.tachiyomi.ui.main.MainActivity
import eu.kanade.tachiyomi.ui.manga.MangaScreen
import eu.kanade.tachiyomi.ui.reader.ReaderActivity
import eu.kanade.tachiyomi.ui.updates.UpdatesTab
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import tachiyomi.domain.library.model.LibraryManga

data object SeirynHomeTab : Tab {
    override val options: TabOptions
        @Composable get() = TabOptions(
            index = 5u,
            title = stringResource(R.string.seiryn_home),
            icon = rememberVectorPainter(SeirynHomeIcon),
        )

    @Composable
    override fun Content() {
        val model = metroViewModel<SeirynHomeViewModel>()
        val state by model.state.collectAsStateWithLifecycle()
        val context = LocalContext.current
        val navigator = LocalNavigator.currentOrThrow
        val tabs = LocalTabNavigator.current
        val scope = rememberCoroutineScope()
        val snackbar = remember { SnackbarHostState() }
        var opening by remember { mutableStateOf(false) }
        val noChapter = stringResource(R.string.seiryn_no_resume)
        val openError = stringResource(R.string.seiryn_open_error)
        LaunchedEffect(state.loading) {
            if (!state.loading) (context as? MainActivity)?.ready = true
        }
        ReportDrawnWhen { !state.loading }
        Scaffold(
            snackbarHost = { SnackbarHost(snackbar) },
            containerColor = MaterialTheme.colorScheme.background,
        ) { padding ->
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(
                    top = padding.calculateTopPadding() + 20.dp,
                    bottom = padding.calculateBottomPadding() + 24.dp,
                ),
                verticalArrangement = Arrangement.spacedBy(20.dp),
            ) {
                item {
                    Column(Modifier.padding(horizontal = 24.dp)) {
                        Text("S E I R Y N", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelLarge)
                        Text(stringResource(R.string.seiryn_home_heading), style = MaterialTheme.typography.headlineLarge, fontFamily = FontFamily.Serif)
                        Text(stringResource(R.string.seiryn_home_subtitle), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                item {
                    Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        DeskStat(state.library.size.toString(), stringResource(R.string.seiryn_titles), Modifier.weight(1f))
                        DeskStat(state.library.sumOf { it.unreadCount.coerceAtLeast(0) }.toString(), stringResource(R.string.seiryn_unread), Modifier.weight(1f))
                        DeskStat(state.library.count { it.lastRead != null }.toString(), stringResource(R.string.seiryn_started), Modifier.weight(1f))
                    }
                }
                if (state.loading) item { Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) { CircularProgressIndicator() } }
                if (state.error) item { Text(stringResource(R.string.seiryn_home_error), Modifier.padding(horizontal = 24.dp)) }
                item { SectionHeading(stringResource(R.string.seiryn_continue)) { tabs.current = HistoryTab } }
                if (!state.loading && state.history.isEmpty()) item {
                    Text(stringResource(R.string.seiryn_history_empty), Modifier.padding(horizontal = 24.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                items(state.history.take(3), key = { "resume-${it.mangaId}" }) { history ->
                    Surface(
                        modifier = Modifier.padding(horizontal = 20.dp).fillMaxWidth(),
                        shape = RoundedCornerShape(24.dp),
                        color = MaterialTheme.colorScheme.surfaceContainerLow,
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    ) {
                        Row(Modifier.padding(14.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
                            MangaCover.Book(data = history.coverData, modifier = Modifier.width(78.dp), contentDescription = history.title, onClick = { navigator.push(MangaScreen(history.mangaId)) })
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text(history.title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis,
                                    modifier = Modifier.clickable { navigator.push(MangaScreen(history.mangaId)) })
                                Button(enabled = !opening, onClick = {
                                    opening = true
                                    scope.launch {
                                        try {
                                            val chapter = model.resume(history)
                                            if (chapter == null) snackbar.showSnackbar(noChapter)
                                            else context.startActivity(ReaderActivity.newIntent(context, chapter.mangaId, chapter.id))
                                        } catch (e: CancellationException) { throw e }
                                        catch (_: Exception) { snackbar.showSnackbar(openError) }
                                        finally { opening = false }
                                    }
                                }) { Text(stringResource(R.string.seiryn_resume)) }
                            }
                        }
                    }
                }
                item {
                    FlowRow(Modifier.padding(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { tabs.current = LibraryTab }) { Text(stringResource(R.string.seiryn_library)) }
                        OutlinedButton(onClick = { tabs.current = UpdatesTab }) { Text(stringResource(R.string.seiryn_updates)) }
                        OutlinedButton(onClick = { navigator.push(DownloadQueueScreen) }) { Text(stringResource(R.string.seiryn_downloads)) }
                    }
                }
                item { SectionHeading(stringResource(R.string.seiryn_recent)) { tabs.current = UpdatesTab } }
                item {
                    val recent = remember(state.library) { state.library.filter { it.chapterFetchedAt != null }.sortedByDescending { it.chapterFetchedAt }.take(12) }
                    Shelf(recent) { navigator.push(MangaScreen(it)) }
                }
                item {
                    val recommendations = remember(state.library, state.history) {
                        recommendFromLibrary(state.library, state.history)
                    }
                    if (recommendations.isNotEmpty()) {
                        SectionHeading(stringResource(R.string.seiryn_picked_for_you)) { tabs.current = LibraryTab }
                        Text(
                            stringResource(R.string.seiryn_inspired_by, state.history.first().title),
                            Modifier.padding(horizontal = 24.dp),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Shelf(recommendations.map { it.entry }) { navigator.push(MangaScreen(it)) }
                    }
                }
                item { SectionHeading(stringResource(R.string.seiryn_rediscover)) { tabs.current = LibraryTab } }
                item {
                    val unread = remember(state.library) { state.library.filter { it.lastRead == null && it.unreadCount > 0 }.sortedBy { it.manga.title }.take(12) }
                    Shelf(unread) { navigator.push(MangaScreen(it)) }
                }
                if (!state.loading && state.library.isEmpty()) item {
                    Column(Modifier.padding(horizontal = 24.dp)) {
                        Text(stringResource(R.string.seiryn_library_empty))
                        Button(onClick = { tabs.current = BrowseTab }) { Text(stringResource(R.string.seiryn_browse)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun DeskStat(value: String, label: String, modifier: Modifier) {
    Surface(modifier, shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surfaceContainer) {
        Column(Modifier.padding(12.dp)) {
            Text(value, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
            Text(label, style = MaterialTheme.typography.labelSmall, maxLines = 2)
        }
    }
}

@Composable
private fun SectionHeading(title: String, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().padding(horizontal = 24.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(title, Modifier.weight(1f), style = MaterialTheme.typography.titleLarge, fontFamily = FontFamily.Serif)
        TextButton(onClick = onClick) { Text(stringResource(R.string.seiryn_view_all)) }
    }
}

@Composable
private fun Shelf(manga: List<LibraryManga>, onClick: (Long) -> Unit) {
    if (manga.isEmpty()) {
        Text(stringResource(R.string.seiryn_shelf_empty), Modifier.padding(horizontal = 24.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)
        return
    }
    LazyRow(contentPadding = PaddingValues(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        items(manga, key = { it.id }) { entry ->
            Column(Modifier.width(120.dp).clickable { onClick(entry.id) }, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                MangaCover.Book(data = entry.manga, contentDescription = entry.manga.title, shape = RoundedCornerShape(14.dp))
                Text(entry.manga.title, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}
