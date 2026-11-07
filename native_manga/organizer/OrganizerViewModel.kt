package eu.kanade.tachiyomi.ui.organizer

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dev.zacsweers.metro.AppScope
import dev.zacsweers.metro.ContributesIntoMap
import dev.zacsweers.metro.Inject
import dev.zacsweers.metro.binding
import dev.zacsweers.metrox.viewmodel.ViewModelKey
import eu.kanade.tachiyomi.data.download.DownloadCache
import eu.kanade.tachiyomi.data.download.DownloadManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject
import tachiyomi.domain.library.model.LibraryManga
import tachiyomi.domain.manga.interactor.GetLibraryManga

@Inject
@ViewModelKey
@ContributesIntoMap(AppScope::class, binding = binding<ViewModel>())
class OrganizerViewModel(
    context: Context,
    getLibraryManga: GetLibraryManga,
    downloadCache: DownloadCache,
    downloadManager: DownloadManager,
) : ViewModel() {
    private val prefs = context.getSharedPreferences("seiryn_organizer_v1", Context.MODE_PRIVATE)
    private val mutex = Mutex()
    private val saved = MutableStateFlow(Saved())
    val saveError = MutableStateFlow(false)
    private var loaded = false

    init {
        viewModelScope.launch(Dispatchers.IO) {
            mutex.withLock {
                try {
                    val json = JSONObject(prefs.getString("state", "{}") ?: "{}")
                    val queue = json.optJSONArray("queue") ?: JSONArray()
                    val rules = json.optJSONArray("rules") ?: JSONArray()
                    saved.value = Saved(
                        queue = (0 until queue.length()).map { queue.getLong(it) }.distinct(),
                        rules = (0 until rules.length()).map {
                            val rule = rules.getJSONObject(it)
                            CollectionRule(rule.getString("name"), rule.optBoolean("unread"), rule.optBoolean("downloaded"), rule.optBoolean("completed"))
                        },
                    )
                    loaded = true
                } catch (_: Exception) { saveError.value = true }
            }
        }
    }

    internal val state = combine(
        getLibraryManga.subscribe(), downloadCache.changes, saved,
    ) { library, _, saved ->
        State(library, downloadManager.getDownloadCounts(library.map { it.manga }), saved.queue, saved.rules, false)
    }.flowOn(Dispatchers.IO)
        .catch { emit(State(loading = false, error = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), State())

    private fun update(change: (Saved) -> Saved) {
        viewModelScope.launch(Dispatchers.IO) {
            mutex.withLock {
                if (!loaded) { saveError.value = true; return@withLock }
                val next = change(saved.value)
                val json = JSONObject().put("queue", JSONArray(next.queue)).put("rules", JSONArray().apply {
                    next.rules.forEach { rule -> put(JSONObject().put("name", rule.name).put("unread", rule.unread).put("downloaded", rule.downloaded).put("completed", rule.completed)) }
                })
                if (prefs.edit().putString("state", json.toString()).commit()) {
                    saved.value = next
                    saveError.value = false
                } else saveError.value = true
            }
        }
    }

    fun add(id: Long) = update { it.copy(queue = addToQueue(it.queue, id)) }
    fun remove(id: Long) = update { it.copy(queue = it.queue - id) }
    fun move(id: Long, offset: Int) = update { it.copy(queue = moveInQueue(it.queue, id, offset)) }
    internal fun addRule(rule: CollectionRule) = update { data ->
        if (rule.name.isBlank() || data.rules.any { it.name.equals(rule.name.trim(), true) }) data
        else data.copy(rules = data.rules + rule.copy(name = rule.name.trim().take(60)))
    }
    fun removeRule(name: String) = update { it.copy(rules = it.rules.filterNot { rule -> rule.name == name }) }

    private data class Saved(val queue: List<Long> = emptyList(), val rules: List<CollectionRule> = emptyList())
    internal data class State(
        val library: List<LibraryManga> = emptyList(),
        val downloads: Map<Long, Int> = emptyMap(),
        val queue: List<Long> = emptyList(),
        val rules: List<CollectionRule> = emptyList(),
        val loading: Boolean = true,
        val error: Boolean = false,
    )
}

