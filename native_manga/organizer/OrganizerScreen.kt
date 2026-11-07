package eu.kanade.tachiyomi.ui.organizer

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import cafe.adriel.voyager.navigator.LocalNavigator
import cafe.adriel.voyager.navigator.currentOrThrow
import dev.zacsweers.metrox.viewmodel.metroViewModel
import eu.kanade.presentation.util.Screen
import eu.kanade.tachiyomi.R
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.ui.manga.MangaScreen

class OrganizerScreen : Screen() {
    @Composable
    override fun Content() {
        val model = metroViewModel<OrganizerViewModel>()
        val state by model.state.collectAsStateWithLifecycle()
        val saveError by model.saveError.collectAsStateWithLifecycle()
        val navigator = LocalNavigator.currentOrThrow
        var queueMode by rememberSaveable { mutableStateOf(false) }
        var selected by rememberSaveable { mutableStateOf(0) }
        var query by rememberSaveable { mutableStateOf("") }
        var creating by rememberSaveable { mutableStateOf(false) }
        val defaults = listOf(
            CollectionRule(stringResource(R.string.organizer_all)),
            CollectionRule(stringResource(R.string.organizer_unread_downloaded), unread = true, downloaded = true),
            CollectionRule(stringResource(R.string.organizer_completed), completed = true),
        )
        val rules = defaults + state.rules
        val rule = rules.getOrElse(selected) { defaults.first() }
        val matches = remember(state.library, state.downloads, rule, query) {
            state.library.filter {
                rule.matches(it.unreadCount, state.downloads[it.id] ?: 0, it.manga.status == SManga.COMPLETED.toLong()) &&
                    it.manga.title.contains(query, ignoreCase = true)
            }.sortedBy { it.manga.title.lowercase() }
        }
        val byId = remember(state.library) { state.library.associateBy { it.id } }
        Scaffold { padding ->
            LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                item {
                    TextButton(onClick = { navigator.pop() }) { Text(stringResource(R.string.organizer_back)) }
                    Text(stringResource(R.string.organizer_title), style = MaterialTheme.typography.headlineSmall)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(!queueMode, { queueMode = false }, label = { Text(stringResource(R.string.organizer_collections)) })
                        FilterChip(queueMode, { queueMode = true }, label = { Text(stringResource(R.string.organizer_queue_count, state.queue.size)) })
                    }
                }
                if (state.loading) item { CircularProgressIndicator() }
                if (state.error || saveError) item { Text(stringResource(R.string.organizer_error), color = MaterialTheme.colorScheme.error) }
                if (queueMode) {
                    item { Text(stringResource(R.string.organizer_queue_help)) }
                    if (!state.loading && state.queue.isEmpty()) item { Text(stringResource(R.string.organizer_queue_empty)) }
                    items(state.queue, key = { it }) { id ->
                        val manga = byId[id]
                        val position = state.queue.indexOf(id)
                        OutlinedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp)) {
                                Text("${position + 1}. ${manga?.manga?.title ?: stringResource(R.string.organizer_unavailable)}",
                                    modifier = Modifier.fillMaxWidth().clickable(enabled = manga != null) { navigator.push(MangaScreen(id)) },
                                    style = MaterialTheme.typography.titleMedium)
                                FlowRow {
                                    TextButton({ model.move(id, -1) }, enabled = position > 0) { Text(stringResource(R.string.organizer_up)) }
                                    TextButton({ model.move(id, 1) }, enabled = position < state.queue.lastIndex) { Text(stringResource(R.string.organizer_down)) }
                                    TextButton({ model.remove(id) }) { Text(stringResource(R.string.organizer_remove)) }
                                }
                            }
                        }
                    }
                } else {
                    item {
                        Text(stringResource(R.string.organizer_rules_help))
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            rules.forEachIndexed { index, item ->
                                FilterChip(selected == index, { selected = index }, label = { Text(item.name) })
                            }
                        }
                        FlowRow {
                            TextButton({ creating = true }) { Text(stringResource(R.string.organizer_create)) }
                            if (selected >= defaults.size && selected < rules.size) TextButton({ model.removeRule(rule.name); selected = 0 }) { Text(stringResource(R.string.organizer_delete_rule)) }
                        }
                        OutlinedTextField(query, { query = it }, label = { Text(stringResource(R.string.organizer_search)) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                    }
                    if (!state.loading && matches.isEmpty()) item { Text(stringResource(R.string.organizer_empty)) }
                    items(matches, key = { it.id }) { entry ->
                        OutlinedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp)) {
                                Text(entry.manga.title, style = MaterialTheme.typography.titleMedium,
                                    modifier = Modifier.fillMaxWidth().clickable { navigator.push(MangaScreen(entry.id)) })
                                Text(stringResource(R.string.organizer_counts, entry.unreadCount, state.downloads[entry.id] ?: 0))
                                TextButton({ model.add(entry.id) }, enabled = entry.id !in state.queue) {
                                    Text(stringResource(if (entry.id in state.queue) R.string.organizer_queued else R.string.organizer_add))
                                }
                            }
                        }
                    }
                }
            }
        }
        if (creating) {
            var name by rememberSaveable { mutableStateOf("") }
            var unread by rememberSaveable { mutableStateOf(false) }
            var downloaded by rememberSaveable { mutableStateOf(false) }
            var completed by rememberSaveable { mutableStateOf(false) }
            AlertDialog(
                onDismissRequest = { creating = false },
                title = { Text(stringResource(R.string.organizer_create)) },
                text = {
                    Column {
                        OutlinedTextField(name, { name = it.take(60) }, label = { Text(stringResource(R.string.organizer_name)) }, singleLine = true)
                        RuleCheck(stringResource(R.string.organizer_unread), unread) { unread = it }
                        RuleCheck(stringResource(R.string.organizer_downloaded), downloaded) { downloaded = it }
                        RuleCheck(stringResource(R.string.organizer_completed), completed) { completed = it }
                    }
                },
                confirmButton = {
                    TextButton({ model.addRule(CollectionRule(name, unread, downloaded, completed)); creating = false },
                        enabled = name.isNotBlank() && (unread || downloaded || completed) && rules.none { it.name.equals(name.trim(), true) }) {
                        Text(stringResource(R.string.organizer_save))
                    }
                },
                dismissButton = { TextButton({ creating = false }) { Text(stringResource(R.string.organizer_cancel)) } },
            )
        }
    }
}

@Composable
private fun RuleCheck(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
        Checkbox(checked, onChange)
        Text(label, Modifier.clickable { onChange(!checked) })
    }
}

