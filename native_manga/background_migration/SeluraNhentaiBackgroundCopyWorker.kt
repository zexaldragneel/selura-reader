package mihon.feature.migration.background

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.ForegroundInfo
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import dev.zacsweers.metro.Inject
import eu.kanade.domain.manga.interactor.UpdateManga
import eu.kanade.tachiyomi.util.system.notify
import eu.kanade.tachiyomi.util.system.setForegroundSafely
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.first
import logcat.LogPriority
import mihon.app.di.AppGraph
import mihon.core.metro.metroGraph
import mihon.domain.manga.model.toDomainManga
import mihon.domain.migration.usecases.MigrateMangaUseCase
import tachiyomi.core.common.util.system.logcat
import tachiyomi.domain.category.interactor.GetCategories
import tachiyomi.domain.chapter.interactor.GetChaptersByMangaId
import tachiyomi.domain.manga.interactor.GetFavorites
import tachiyomi.domain.manga.interactor.GetManga
import tachiyomi.domain.manga.interactor.NetworkToLocalManga
import tachiyomi.domain.manga.model.MangaUpdate
import tachiyomi.domain.source.service.SourceManager

/**
 * Serialized, resumable NHentai library migration.
 * Transfers metadata to a verified exact gallery match, then unfavorites the
 * original entry. Original database rows and source downloads remain on disk.
 * Older queued Copy requests are rejected rather than silently becoming Moves.
 * The worker is independent from the migration screen and can run while reading.
 */
class SeluraNhentaiBackgroundCopyWorker(
    private val context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    @Inject private lateinit var sourceManager: SourceManager
    @Inject private lateinit var getFavorites: GetFavorites
    @Inject private lateinit var getManga: GetManga
    @Inject private lateinit var networkToLocalManga: NetworkToLocalManga
    @Inject private lateinit var migrateManga: MigrateMangaUseCase
    @Inject private lateinit var updateManga: UpdateManga
    @Inject private lateinit var getCategories: GetCategories
    @Inject private lateinit var getChaptersByMangaId: GetChaptersByMangaId

    private var processedCount = 0
    private var totalCount = 0
    private var failedCount = 0

    override suspend fun doWork(): Result {
        // Existing WorkManager records from the old Copy APK do not contain
        // this opt-in. Never turn a previously approved copy into a move.
        if (inputData.getString(MODE) != MOVE_MODE) {
            return setupFailure("Old Copy job stopped. Select Move NHentai in background.")
        }
        val sourceId = inputData.getLong(SOURCE_ID, -1)
        if (sourceId <= 0L) return setupFailure("Invalid source selection")

        val graph: AppGraph = context.metroGraph()
        graph.inject(this)
        val source = sourceManager.get(sourceId) ?: return setupFailure("Original source is not installed")
        if (!source.name.contains("nhentai", ignoreCase = true) ||
            (source.name == "Selura NHentai" && source.lang == "all")
        ) {
            return setupFailure("Select the original NHentai source, not Selura NHentai ALL")
        }

        // This is our separately signed extension, not the old Yuzono source.
        // Prefer ALL: it retains the exact source identity used for prior copies.
        val candidates = sourceManager.getOnlineSources().filter {
            it.name == "Selura NHentai" && it.lang == "all" && it.id != sourceId
        }
        val target = candidates.singleOrNull()
            ?: return setupFailure("Install exactly one Selura NHentai ALL source before copying")

        val favorites = getFavorites.subscribe(sourceId).first()
            .filter { GALLERY_URL.matches(it.url) }
            .sortedBy { it.id }
        totalCount = favorites.size
        ensureNotificationChannel()
        setForegroundSafely()

        val prefs = context.getSharedPreferences(CHECKPOINT_PREFS, Context.MODE_PRIVATE)
        // Separate Move checkpoints from earlier Copy checkpoints. All old
        // favorites, including already-copied duplicates, must be reconciled.
        val cursorKey = "last_moved_manga_" + sourceId + "_" + target.id
        val failuresKey = "failed_move_manga_" + sourceId + "_" + target.id
        val validIds = favorites.mapTo(mutableSetOf()) { it.id }
        val failedIds = prefs.getStringSet(failuresKey, emptySet()).orEmpty()
            .mapNotNull { it.toLongOrNull() }
            .filterTo(mutableSetOf()) { it in validIds }
        // Original favorites are the durable queue: successful moves no longer
        // appear here, regardless of crash timing or checkpoint state.
        val existingTargets = getFavorites.subscribe(target.id).first()
            .associateBy { it.url.trimEnd('/') }
        processedCount = 0
        failedCount = failedIds.size
        var attemptedInRun = 0
        publishProgress()

        try {
            for (manga in favorites) {
                currentCoroutineContext().ensureActive()

                try {
                    // Reuse the favorite created by the previous Copy build,
                    // otherwise find the exact numeric gallery. Never fuzzy match.
                    val canonicalUrl = manga.url.trimEnd('/')
                    val existing = existingTargets[canonicalUrl]
                        ?: getManga.subscribe(manga.url, target.id).first()
                    val targetManga = existing ?: run {
                        val galleryId = manga.url.removePrefix("/g/").trimEnd('/')
                        val matching = target.getSearchManga(
                            1,
                            galleryId,
                            target.getFilterList(),
                        ).mangas.singleOrNull { it.url.trimEnd('/') == canonicalUrl }
                            ?: error("No exact gallery match")
                        networkToLocalManga(matching.toDomainManga(target.id))
                    }
                    check(targetManga.url.trimEnd('/') == canonicalUrl &&
                        targetManga.source == target.id && targetManga.id != manga.id
                    ) { "Target gallery identity mismatch" }

                    // Stage target-side metadata first. Strict mode propagates
                    // errors rather than swallowing them. This NEVER deletes
                    // original downloads or un-favorites the original entry.
                    migrateManga(
                        current = manga,
                        target = targetManga,
                        replace = false,
                        strict = true,
                    )
                    val updatedTarget = getManga.await(targetManga.id)
                    check(updatedTarget?.favorite == true &&
                        updatedTarget.url.trimEnd('/') == canonicalUrl
                    ) { "Target verification failed; original retained" }

                    val originalCategories = getCategories.await(manga.id).map { it.id }.toSet()
                    val targetCategories = getCategories.await(targetManga.id).map { it.id }.toSet()
                    check(targetCategories.containsAll(originalCategories)) {
                        "Categories did not transfer; original retained"
                    }
                    val originalChapters = getChaptersByMangaId.await(manga.id)
                    val targetChapters = getChaptersByMangaId.await(targetManga.id)
                    if (originalChapters.isNotEmpty()) {
                        check(originalChapters.size == 1 && targetChapters.size == 1 &&
                            originalChapters.single().url.trimEnd('/') ==
                                targetChapters.single().url.trimEnd('/')
                        ) { "Chapter mapping ambiguous; original retained" }
                        val oldChapter = originalChapters.single()
                        val newChapter = targetChapters.single()
                        check(
                            (!oldChapter.read || newChapter.read) &&
                                (!oldChapter.bookmark || newChapter.bookmark) &&
                                newChapter.lastPageRead >= oldChapter.lastPageRead
                        ) { "Reading position or bookmark did not transfer; original retained" }
                    }
                    check(updatedTarget.notes == manga.notes || manga.notes.isEmpty()) {
                        "Notes did not transfer; original retained"
                    }
                    // Only after all checks: remove ORIGINAL FAVORITE from
                    // Library. The old manga database row and download files
                    // remain untouched for rollback/recovery.
                    check(getManga.await(manga.id)?.favorite == true) {
                        "Original changed during migration; refusing to overwrite"
                    }
                    updateManga.awaitAll(listOf(MangaUpdate(manga.id) { favoriteAt = null }))
                    check(getManga.await(manga.id)?.favorite == false) {
                        "Original is still favorited; migration not finished"
                    }
                    failedIds.remove(manga.id)
                    processedCount++
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    failedIds.add(manga.id)
                    logcat(LogPriority.WARN, e)
                }

                // Persist failures after each item. The original favorites
                // themselves are the queue, so a power loss between DB and
                // SharedPreferences commits cannot permanently skip a title.
                failedCount = failedIds.size
                if (!prefs.edit()
                        .putLong(cursorKey, manga.id)
                        .putStringSet(failuresKey, failedIds.mapTo(mutableSetOf()) { it.toString() })
                        .commit()
                ) {
                    error("Unable to persist migration checkpoint and failed galleries")
                }
                attemptedInRun++
                if (attemptedInRun % 5 == 0 || attemptedInRun == totalCount) {
                    publishProgress()
                    setForegroundSafely()
                }
                // Avoid saturating NHentai and keep pages/reader responsive.
                delay(350)
            }
        } catch (e: CancellationException) {
            throw e // Cancel notification action keeps the checkpoint for resume.
        } catch (e: Exception) {
            logcat(LogPriority.WARN, e)
            return Result.retry()
        }

        // An interrupted move resumes from the remaining source favorites.
        // Failed originals remain in Library, so no gallery is silently lost.
        publishProgress()
        context.notify(
            FINISHED_NOTIFICATION_ID,
            completionNotification(),
        )
        return Result.success(workDataOf("processed" to processedCount, "failed" to failedCount))
    }

    private suspend fun publishProgress() {
        setProgress(
            workDataOf(
                "processed" to processedCount,
                "total" to totalCount,
                "failed" to failedCount,
            ),
        )
    }

    private fun ensureNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val service = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            service.createNotificationChannel(
                NotificationChannel(
                    NOTIFICATION_CHANNEL,
                    "Selura background migration",
                    NotificationManager.IMPORTANCE_LOW,
                ),
            )
        }
    }

    private fun completionNotification() = NotificationCompat.Builder(context, NOTIFICATION_CHANNEL)
        .setSmallIcon(android.R.drawable.stat_sys_download_done)
        .setContentTitle("Selura NHentai migration finished")
        .setContentText(
            "Moved " + processedCount + " / " + totalCount + " galleries; " + failedCount + " need retry",
        )
        .setAutoCancel(true)
        .build()

    private fun setupFailure(message: String): Result {
        ensureNotificationChannel()
        context.notify(
            FINISHED_NOTIFICATION_ID,
            NotificationCompat.Builder(context, NOTIFICATION_CHANNEL)
                .setSmallIcon(android.R.drawable.stat_notify_error)
                .setContentTitle("Selura NHentai copy could not start")
                .setContentText(message)
                .setAutoCancel(true)
                .build(),
        )
        return Result.failure(workDataOf("reason" to message))
    }

    override suspend fun getForegroundInfo(): ForegroundInfo {
        ensureNotificationChannel()
        val notification = NotificationCompat.Builder(context, NOTIFICATION_CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle("Migrating NHentai library in background")
            .setContentText(
                "Moved " + processedCount + " / " + totalCount +
                    " · " + failedCount + " need retry; keep reading",
            )
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setProgress(totalCount.coerceAtLeast(1), processedCount, totalCount == 0)
            .addAction(
                android.R.drawable.ic_menu_close_clear_cancel,
                "Stop",
                WorkManager.getInstance(context).createCancelPendingIntent(id),
            )
            .build()
        return ForegroundInfo(
            PROGRESS_NOTIFICATION_ID,
            notification,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            } else {
                0
            },
        )
    }

    companion object {
        private const val SOURCE_ID = "source_id"
        private const val MODE = "selura_nhentai_mode"
        private const val MOVE_MODE = "move_v1"
        private const val UNIQUE_WORK = "selura_nhentai_background_move"
        private const val LEGACY_COPY_WORK = "selura_nhentai_background_copy"
        private const val NOTIFICATION_CHANNEL = "selura_background_migration"
        private const val PROGRESS_NOTIFICATION_ID = 18341
        private const val FINISHED_NOTIFICATION_ID = 18342
        private const val CHECKPOINT_PREFS = "selura_nhentai_copy_checkpoints"
        private val GALLERY_URL = Regex("^/g/[0-9]+/?$")

        /** KEEP prevents starting parallel migrations of 3,000+ titles. */
        fun start(context: Context, sourceId: Long) {
            val manager = WorkManager.getInstance(context)
            manager.cancelUniqueWork(LEGACY_COPY_WORK)
            val request = OneTimeWorkRequestBuilder<SeluraNhentaiBackgroundCopyWorker>()
                .setInputData(workDataOf(SOURCE_ID to sourceId, MODE to MOVE_MODE))
                .setConstraints(
                    Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build(),
                )
                .addTag(UNIQUE_WORK)
                .build()
            manager.enqueueUniqueWork(
                UNIQUE_WORK,
                ExistingWorkPolicy.KEEP,
                request,
            )
        }
    }
}
