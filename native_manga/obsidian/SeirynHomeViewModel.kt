package eu.kanade.tachiyomi.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dev.zacsweers.metro.AppScope
import dev.zacsweers.metro.ContributesIntoMap
import dev.zacsweers.metro.Inject
import dev.zacsweers.metro.binding
import dev.zacsweers.metrox.viewmodel.ViewModelKey
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import tachiyomi.domain.history.interactor.GetHistory
import tachiyomi.domain.history.interactor.GetNextChapters
import tachiyomi.domain.history.model.HistoryWithRelations
import tachiyomi.domain.library.model.LibraryManga
import tachiyomi.domain.manga.interactor.GetLibraryManga

/** Read-only dashboard; the existing reader owns all chapter and history writes. */
@Inject
@ViewModelKey
@ContributesIntoMap(AppScope::class, binding = binding<ViewModel>())
class SeirynHomeViewModel(
    getLibraryManga: GetLibraryManga,
    getHistory: GetHistory,
    private val getNextChapters: GetNextChapters,
) : ViewModel() {
    private val error = MutableStateFlow(false)
    private val data = combine(getLibraryManga.subscribe(), getHistory.subscribe("")) { library, history ->
        State(library = library, history = history.distinctBy { it.mangaId }.take(12), loading = false)
    }.catch { error.value = true; emit(State(loading = false)) }

    val state = combine(data, error) { data, error -> data.copy(error = error) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), State())

    // Resume a partially read chapter at its saved page, or advance after a completed chapter.
    suspend fun resume(history: HistoryWithRelations) =
        getNextChapters.await(history.mangaId, history.chapterId, onlyUnread = false).firstOrNull()

    data class State(
        val library: List<LibraryManga> = emptyList(),
        val history: List<HistoryWithRelations> = emptyList(),
        val loading: Boolean = true,
        val error: Boolean = false,
    )
}

/** Recommendations use only genre metadata already present in the user's shelf. */
internal data class SeirynRelatedTitle(
    val entry: LibraryManga,
    val sharedGenres: List<String>,
)

internal fun recommendFromLibrary(
    library: List<LibraryManga>,
    history: List<HistoryWithRelations>,
): List<SeirynRelatedTitle> {
    val seed = history.firstOrNull() ?: return emptyList()
    val seedGenres = library.firstOrNull { it.id == seed.mangaId }?.manga?.genre
        .orEmpty()
        .map { it.trim() }
        .filter(String::isNotEmpty)
        .distinctBy { it.lowercase() }
    if (seedGenres.isEmpty()) return emptyList()
    val normalizedSeed = seedGenres.associateBy { it.lowercase() }
    return library.asSequence()
        .filter { it.id != seed.mangaId && it.unreadCount > 0L }
        .mapNotNull { candidate ->
            val shared = candidate.manga.genre.orEmpty()
                .mapNotNull { normalizedSeed[it.trim().lowercase()] }
                .distinctBy { it.lowercase() }
            if (shared.isEmpty()) null else SeirynRelatedTitle(candidate, shared)
        }
        .sortedWith(compareByDescending<SeirynRelatedTitle> { it.sharedGenres.size }.thenBy { it.entry.manga.title.lowercase() })
        .take(8)
        .toList()
}
