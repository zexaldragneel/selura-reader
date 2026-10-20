package eu.kanade.tachiyomi.ui.main

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import eu.kanade.tachiyomi.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.File
import java.net.URL
import java.security.MessageDigest
import java.util.Locale
import javax.net.ssl.HttpsURLConnection

/**
 * Downloads verified release bytes directly to Selura's private cache and
 * hands the APK to Android's user-confirmed package installer.
 */
internal object SeluraApkInstaller {
    private const val PACKAGE_NAME = "com.selura.manga"
    private const val MAX_BYTES = 256L * 1024 * 1024

    private fun approvedHost(url: URL): Boolean {
        val host = url.host.lowercase(Locale.ROOT)
        return url.protocol == "https" &&
            (host == "github.com" || host.endsWith(".githubusercontent.com"))
    }

    private fun archiveIsSafe(context: Context, file: File, offer: SeluraUpdateOffer) {
        val pm = context.packageManager
        @Suppress("DEPRECATION")
        val archive = pm.getPackageArchiveInfo(file.absolutePath, PackageManager.GET_SIGNING_CERTIFICATES)
            ?: error("The downloaded file is not a valid APK")
        check(context.packageName == PACKAGE_NAME && archive.packageName == PACKAGE_NAME) {
            "The update is for a different Android application"
        }
        val version = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            archive.longVersionCode
        } else {
            @Suppress("DEPRECATION")
            archive.versionCode.toLong()
        }
        check(version == offer.versionCode.toLong() && version > BuildConfig.VERSION_CODE) {
            "APK version does not match the update feed"
        }

        @Suppress("DEPRECATION")
        val installed = pm.getPackageInfo(context.packageName, PackageManager.GET_SIGNING_CERTIFICATES)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val original = installed.signingInfo?.apkContentsSigners
                ?: error("Installed APK certificate unavailable")
            val downloaded = archive.signingInfo?.apkContentsSigners
                ?: error("Downloaded APK certificate unavailable")
            check(original.isNotEmpty() && original.size == downloaded.size &&
                original.all { old ->
                    downloaded.any { candidate ->
                        old.toByteArray().contentEquals(candidate.toByteArray())
                    }
                }
            ) { "The update's signing certificate does not match Selura" }
        } else {
            @Suppress("DEPRECATION")
            val original = installed.signatures.orEmpty()
            @Suppress("DEPRECATION")
            val downloaded = archive.signatures.orEmpty()
            check(original.isNotEmpty() && original.size == downloaded.size &&
                original.all { old -> downloaded.any { it == old } }
            ) { "The update's signing certificate does not match Selura" }
        }
    }

    suspend fun download(
        context: Context,
        offer: SeluraUpdateOffer,
        onProgress: suspend (received: Long, total: Long) -> Unit,
        onVerify: suspend () -> Unit,
    ): File = withContext(Dispatchers.IO) {
        val directory = File(context.cacheDir, "selura-apk-updates")
        check(directory.isDirectory || directory.mkdirs()) { "Cannot create update cache" }
        val partial = File.createTempFile("selura-", ".apk", directory)
        try {
            val digest = MessageDigest.getInstance("SHA-256")
            val tag = Uri.parse(offer.releaseUrl).lastPathSegment ?: error("No release tag")
            check(tag.matches(Regex("[a-zA-Z0-9._-]{1,100}"))) { "Invalid release tag" }
            var address = URL(
                "https://github.com/zexaldragneel/selura-reader/releases/download/" +
                    tag + "/selura-manga.apk",
            )
            var complete = false
            for (redirect in 0..5) {
                currentCoroutineContext().ensureActive()
                check(approvedHost(address)) { "Untrusted update download server" }
                val connection = address.openConnection() as HttpsURLConnection
                connection.instanceFollowRedirects = false
                connection.connectTimeout = 15_000
                connection.readTimeout = 20_000
                try {
                    when (connection.responseCode) {
                        301, 302, 303, 307, 308 -> {
                            val location = connection.getHeaderField("Location")
                                ?: error("GitHub release redirect missing")
                            val next = URL(address, location)
                            check(approvedHost(next)) { "Unexpected update redirect server" }
                            address = next
                            continue
                        }
                        200 -> Unit
                        else -> error("Update download failed: HTTP " + connection.responseCode)
                    }
                    val total = connection.contentLengthLong
                    check(total <= MAX_BYTES) { "Update download too large" }
                    var received = 0L
                    var lastProgress = -1L
                    connection.inputStream.use { input ->
                        partial.outputStream().buffered().use { output ->
                            val buffer = ByteArray(64 * 1024)
                            while (true) {
                                currentCoroutineContext().ensureActive()
                                val count = input.read(buffer)
                                if (count < 0) break
                                if (count == 0) continue
                                received += count
                                check(received <= MAX_BYTES) { "Update download too large" }
                                digest.update(buffer, 0, count)
                                output.write(buffer, 0, count)
                                val progressUnit = if (total > 0) {
                                    received * 100 / total
                                } else {
                                    received / (1024 * 1024)
                                }
                                if (progressUnit != lastProgress) {
                                    lastProgress = progressUnit
                                    onProgress(received, total)
                                }
                            }
                        }
                    }
                    check(received > 100_000 && (total <= 0 || received == total)) {
                        "Update download incomplete"
                    }
                    complete = true
                    break
                } finally {
                    connection.disconnect()
                }
            }
            check(complete) { "Too many GitHub download redirects" }
            onVerify()
            val actualHash = digest.digest().joinToString("") {
                (it.toInt() and 255).toString(16).padStart(2, '0')
            }
            check(actualHash.equals(offer.sha256, ignoreCase = true)) {
                "APK checksum does not match the verified GitHub release"
            }
            archiveIsSafe(context, partial, offer)
            currentCoroutineContext().ensureActive()
            val completed = File(directory, "selura-manga.apk")
            check(!completed.exists() || completed.delete()) { "Old APK cache cannot be cleared" }
            check(partial.renameTo(completed)) { "Cannot finalize verified update" }
            completed
        } finally {
            partial.delete()
        }
    }

    /** Returns false only when Android's 'install unknown apps' setting is needed. */
    fun openInstaller(context: Context, apk: File): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
            !context.packageManager.canRequestPackageInstalls()
        ) {
            context.startActivity(
                Intent(
                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:" + context.packageName),
                ),
            )
            return false
        }
        val uri = FileProvider.getUriForFile(context, context.packageName + ".provider", apk)
        val request = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            clipData = ClipData.newRawUri("Verified Selura update", uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(request)
        return true
    }
}
