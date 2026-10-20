package eu.kanade.tachiyomi.ui.main

import android.net.Uri
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import eu.kanade.tachiyomi.BuildConfig
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URL
import javax.net.ssl.HttpsURLConnection

// Public read-only metadata from Selura's own gh-pages branch.
// The checked native release workflow writes this after APK signing verification.
// No access tokens or private signing data are bundled into the Android APK.
private const val SELURA_UPDATE_FEED =
    "https://raw.githubusercontent.com/zexaldragneel/selura-reader/gh-pages/updates/latest.json"

internal data class SeluraUpdateOffer(
    val versionCode: Int,
    val versionName: String,
    val notes: String,
    val releaseUrl: String,
    val sha256: String,
)

private object SeluraReleaseFeed {
    fun check(installedVersion: Int): SeluraUpdateOffer? {
        val connection = URL(SELURA_UPDATE_FEED).openConnection() as HttpsURLConnection
        connection.connectTimeout = 4_000
        connection.readTimeout = 5_000
        connection.setRequestProperty("Accept", "application/json")
        return try {
            if (connection.responseCode != 200) return null
            val text = connection.inputStream.bufferedReader().use { reader ->
                val collected = StringBuilder()
                val buffer = CharArray(2048)
                while (collected.length <= 12_000) {
                    val count = reader.read(buffer)
                    if (count == -1) break
                    collected.append(buffer, 0, count)
                }
                collected.toString()
            }
            if (text.length > 12_000) return null
            val json = JSONObject(text)
            val versionCode = json.optInt("versionCode", -1)
            if (json.optString("applicationId") != "com.selura.manga" ||
                versionCode <= installedVersion
            ) {
                return null
            }
            val uri = Uri.parse(json.optString("releaseUrl"))
            val segments = uri.pathSegments
            if (uri.scheme != "https" || uri.host != "github.com" ||
                segments.size != 5 ||
                segments[0] != "zexaldragneel" ||
                segments[1] != "selura-reader" ||
                segments[2] != "releases" ||
                segments[3] != "tag" ||
                !segments[4].matches(Regex("[a-zA-Z0-9._-]{1,100}"))
            ) {
                return null
            }
            val digest = json.optString("sha256")
            if (!digest.matches(Regex("[a-fA-F0-9]{64}"))) return null
            SeluraUpdateOffer(
                versionCode = versionCode,
                versionName = json.optString("versionName")
                    .take(60).ifBlank { "Build $versionCode" },
                notes = json.optString("notes").take(1200),
                releaseUrl = uri.toString(),
                sha256 = digest.lowercase(),
            )
        } finally {
            connection.disconnect()
        }
    }
}

private enum class UpdateStage { OFFER, DOWNLOADING, VERIFYING, READY, ERROR }

/**
 * Shows an update prompt and an in-app download/progress panel.
 * Actual installation is always user-authorized through Android's installer.
 */
@Composable
fun SeluraStartupUpdateCheck() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var offered by remember { mutableStateOf<SeluraUpdateOffer?>(null) }
    var stage by remember { mutableStateOf(UpdateStage.OFFER) }
    var downloadedBytes by remember { mutableStateOf(0L) }
    var totalBytes by remember { mutableStateOf(-1L) }
    var verifiedApk by remember { mutableStateOf<java.io.File?>(null) }
    var errorMessage by remember { mutableStateOf("") }
    var downloadJob by remember { mutableStateOf<Job?>(null) }

    LaunchedEffect(Unit) {
        offered = withContext(Dispatchers.IO) {
            runCatching { SeluraReleaseFeed.check(BuildConfig.VERSION_CODE) }.getOrNull()
        }
    }

    val update = offered ?: return
    val downloadUpdate: () -> Unit = {
        if (downloadJob?.isActive != true) {
            stage = UpdateStage.DOWNLOADING
            downloadedBytes = 0L
            totalBytes = -1L
            errorMessage = ""
            downloadJob = scope.launch {
                try {
                    val file = SeluraApkInstaller.download(
                        context.applicationContext,
                        update,
                        onProgress = { received, total ->
                            withContext(Dispatchers.Main) {
                                downloadedBytes = received
                                totalBytes = total
                            }
                        },
                        onVerify = {
                            withContext(Dispatchers.Main) {
                                stage = UpdateStage.VERIFYING
                            }
                        },
                    )
                    verifiedApk = file
                    stage = UpdateStage.READY
                    errorMessage = if (SeluraApkInstaller.openInstaller(context, file)) {
                        "Confirm the update in Android's installer."
                    } else {
                        "Allow installs from Selura in Android Settings, then return and tap Install."
                    }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    errorMessage = e.message?.take(220)
                        ?: "Unable to download the update. Please retry."
                    stage = UpdateStage.ERROR
                }
            }
        }
    }

    val downloading = stage == UpdateStage.DOWNLOADING || stage == UpdateStage.VERIFYING
    AlertDialog(
        onDismissRequest = { if (!downloading) offered = null },
        title = { Text("Selura Manga update available") },
        text = {
            Column {
                Text("New version: " + update.versionName)
                if (stage == UpdateStage.OFFER && update.notes.isNotBlank()) {
                    Text(
                        text = update.notes,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(top = 12.dp),
                    )
                }
                when (stage) {
                    UpdateStage.OFFER -> Text(
                        text = "Download and verify the APK inside Selura. " +
                            "Android will ask you to approve the installation. " +
                            "Your manga library, downloads, and reading history remain in place.",
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 12.dp),
                    )
                    UpdateStage.DOWNLOADING -> {
                        Text(
                            text = if (totalBytes > 0) {
                                "Downloading: " +
                                    (downloadedBytes * 100 / totalBytes).coerceIn(0, 100) + "%"
                            } else {
                                "Downloading: " + downloadedBytes / (1024 * 1024) + " MB"
                            },
                            modifier = Modifier.padding(top = 12.dp),
                        )
                        if (totalBytes > 0) {
                            LinearProgressIndicator(
                                progress = {
                                    (downloadedBytes.toFloat() / totalBytes).coerceIn(0f, 1f)
                                },
                                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                            )
                        } else {
                            LinearProgressIndicator(
                                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                            )
                        }
                    }
                    UpdateStage.VERIFYING -> {
                        Text(
                            "Verifying APK checksum, package ID and signature…",
                            modifier = Modifier.padding(top = 12.dp),
                        )
                        LinearProgressIndicator(
                            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                        )
                    }
                    UpdateStage.READY, UpdateStage.ERROR -> Text(
                        text = errorMessage,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 12.dp),
                    )
                }
            }
        },
        confirmButton = {
            when (stage) {
                UpdateStage.OFFER -> TextButton(onClick = downloadUpdate) {
                    Text("Download update")
                }
                UpdateStage.DOWNLOADING, UpdateStage.VERIFYING -> Unit
                UpdateStage.ERROR -> TextButton(onClick = downloadUpdate) {
                    Text("Retry")
                }
                UpdateStage.READY -> TextButton(
                    onClick = {
                        val file = verifiedApk ?: return@TextButton
                        try {
                            errorMessage = if (SeluraApkInstaller.openInstaller(context, file)) {
                                "Confirm the update in Android's installer."
                            } else {
                                "Allow installs from Selura in Settings, then return and tap Install."
                            }
                        } catch (e: Exception) {
                            errorMessage = e.message ?: "Android could not launch the installer."
                        }
                    },
                ) {
                    Text("Install")
                }
            }
        },
        dismissButton = {
            TextButton(
                onClick = {
                    downloadJob?.cancel()
                    offered = null
                },
            ) {
                Text(if (downloading) "Cancel download" else "Later")
            }
        },
    )
}
