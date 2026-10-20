package mihon.feature.migration.background

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.ForegroundInfo
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
        if (sourceId <= 0L) return Result.failure()

        val graph: AppGraph = context.metroGraph()
        graph.inject(this)
        val source = sourceManager.get(sourceId) ?: return Result.failure()
        if (!source.name.contains("nhentai", ignoreCase = true)) return Result.failure()

        // This is our separately signed extension, not the old Yuzono source.
        // Prefer ALL: it retains the exact source identity used for prior copies.
        val candidates = sourceManager.getOnlineSources().filter {
            it.name == "Selura NHentai" && it.lang == "all" && it.id != sourceId
        }
        val target = candidates.singleOrNull() ?: return Result.failure()

        val favorites = getFavorites.subscribe(sourceId).first()
            .filter { GALLERY_URL.matches(it.url) }
            .sortedBy { it.id }
        totalCount = favorites.size
        ensureNotificationChannel()
        setForegroundSafely()

        val prefs = context.getSharedPreferences(CHECKPOINT_PREFS, Context.MODE_PRIVATE)
        val cursorKey = "last_manga_" + sourceId + "_" + target.id
        var lastProcessedId = prefs.getLong(cursorKey, 0L)
        processedCount = favorites.count { it.id <= lastProcessedId }
        publishProgress()

        try {
            for (manga in favorites) {
                if (manga.id <= lastProcessedId) continue
                currentCoroutineContext().ensureActive()

                try {
                    // Skip copies that already exist, including copies made in
                    // foreground batches or before a process restart.
                    val existing = getManga.subscribe(manga.url, target.id).first()
                    if (existing?.favorite != true) {
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
                    }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    failedCount++
                    logcat(LogPriority.WARN, e)
                }

                // Commit after each gallery. A killed/restarted worker resumes
                // from the last checkpoint, without deleting original entries.
                if (!prefs.edit().putLong(cursorKey, manga.id).commit()) {
                    error("Unable to persist migration checkpoint")
                }
                lastProcessedId = manga.id
                processedCount++
                if (processedCount % 5 == 0 || processedCount == totalCount) {
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

        // A subsequent "Copy in background" can retry previously failed items;
        // existing target favorites are skipped without doing a network request.
        prefs.edit().remove(cursorKey).apply()
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
            "Processed " + processedCount + " galleries; " + failedCount + " need retry",
        )
        .setAutoCancel(true)
        .build()

    override suspend fun getForegroundInfo(): ForegroundInfo {
        ensureNotificationChannel()
        val notification = NotificationCompat.Builder(context, NOTIFICATION_CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle("Copying NHentai library in background")
            .setContentText(
                "Processed " + processedCount + " / " + totalCount +
                    " · " + failedCount + " unmatched; you can keep reading",
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
