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
import tachiyomi.domain.manga.interactor.GetFavorites
import tachiyomi.domain.manga.interactor.GetManga
import tachiyomi.domain.manga.interactor.NetworkToLocalManga
import tachiyomi.domain.source.service.SourceManager

/**
 * A serialized, resumable, non-destructive NHentai copy.
 * The WorkManager job is independent from the migration screen/ViewModel:
 * it continues when the user reads manga, changes screens or backgrounds Selura.
 *
 * Only exact numeric gallery URLs are accepted. We never fuzzy-match titles,
 * replace original favorites, or remove any original downloads.
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

    private var processedCount = 0
    private var totalCount = 0
    private var failedCount = 0

    override suspend fun doWork(): Result {
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
        val cursorKey = "last_manga_" + sourceId + "_" + target.id
        val failuresKey = "failed_manga_" + sourceId + "_" + target.id
        var lastProcessedId = prefs.getLong(cursorKey, 0L)
        // Persist failures alongside the cursor. A resumed pass handles only
        // failed or not-yet-attempted galleries, not all 3,000 originals.
        val validIds = favorites.mapTo(mutableSetOf()) { it.id }
        val failedIds = prefs.getStringSet(failuresKey, emptySet()).orEmpty()
            .mapNotNull { it.toLongOrNull() }
            .filterTo(mutableSetOf()) { it in validIds }
        val existingTargetUrls = getFavorites.subscribe(target.id).first()
            .mapTo(mutableSetOf()) { it.url.trimEnd('/') }
        processedCount = favorites.count { it.id <= lastProcessedId && it.id !in failedIds }
        failedCount = failedIds.size
        val pendingCount = favorites.count { it.id > lastProcessedId || it.id in failedIds }
        var attemptedInRun = 0
        publishProgress()

        try {
            for (manga in favorites) {
                if (manga.id <= lastProcessedId && manga.id !in failedIds) continue
                currentCoroutineContext().ensureActive()

                try {
                    // Skip copies that already exist, including copies made in
                    // foreground batches or before a process restart.
                    val canonicalUrl = manga.url.trimEnd('/')
                    if (canonicalUrl !in existingTargetUrls) {
                        val existing = getManga.subscribe(manga.url, target.id).first()
                        val targetManga = existing ?: run {
                            val galleryId = manga.url.removePrefix("/g/").trimEnd('/')
                            val matching = target.getSearchManga(
                                1,
                                galleryId,
                                target.getFilterList(),
                            ).mangas.singleOrNull { it.url.trimEnd('/') == manga.url.trimEnd('/') }
                                ?: error("No exact gallery match")
                            networkToLocalManga(matching.toDomainManga(target.id))
                        }
                        migrateManga(current = manga, target = targetManga, replace = false)
                        check(getManga.await(targetManga.id)?.favorite == true) {
                            "Target was not added to the library"
                        }
                        existingTargetUrls.add(canonicalUrl)
                    }
                    failedIds.remove(manga.id)
                    processedCount++
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    failedIds.add(manga.id)
                    logcat(LogPriority.WARN, e)
                }

                // Checkpoint and failure set are one atomic SharedPreferences
                // commit: no failed gallery is silently abandoned on restart.
                failedCount = failedIds.size
                val nextCursor = maxOf(lastProcessedId, manga.id)
                if (!prefs.edit()
                        .putLong(cursorKey, nextCursor)
                        .putStringSet(failuresKey, failedIds.mapTo(mutableSetOf()) { it.toString() })
                        .commit()
                ) {
                    error("Unable to persist migration checkpoint and failed galleries")
                }
                lastProcessedId = nextCursor
                attemptedInRun++
                if (attemptedInRun % 5 == 0 || attemptedInRun == pendingCount) {
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

        // Retain the cursor and failed IDs after completion. Later runs retry
        // only unresolved galleries and newly added entries, never re-copying
        // the entire original library.
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
        .setContentTitle("Selura NHentai background copy finished")
        .setContentText(
            "Completed " + processedCount + " / " + totalCount + " galleries; " + failedCount + " need retry",
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
            .setContentTitle("Copying NHentai library in background")
            .setContentText(
                "Completed " + processedCount + " / " + totalCount +
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
        private const val UNIQUE_WORK = "selura_nhentai_background_copy"
        private const val NOTIFICATION_CHANNEL = "selura_background_migration"
        private const val PROGRESS_NOTIFICATION_ID = 18341
        private const val FINISHED_NOTIFICATION_ID = 18342
        private const val CHECKPOINT_PREFS = "selura_nhentai_copy_checkpoints"
        private val GALLERY_URL = Regex("^/g/[0-9]+/?$")

        /** KEEP prevents accidentally starting parallel copies of 3,000+ titles. */
        fun start(context: Context, sourceId: Long) {
            val request = OneTimeWorkRequestBuilder<SeluraNhentaiBackgroundCopyWorker>()
                .setInputData(workDataOf(SOURCE_ID to sourceId))
                .setConstraints(
                    Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build(),
                )
                .addTag(UNIQUE_WORK)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_WORK,
                ExistingWorkPolicy.KEEP,
                request,
            )
        }
    }
}
