package eu.kanade.tachiyomi.ui.main

import android.net.Uri
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import eu.kanade.tachiyomi.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URL
import javax.net.ssl.HttpsURLConnection

// A deliberately public, read-only feed. Selura's repository is private:
// unauthenticated GitHub release APIs will return 404, so DO NOT add a
// personal access token or GitHub credentials to the Android APK.
// Publishing this metadata is explicitly opt-in.
private const val SELURA_UPDATE_FEED =
    "https://raw.githubusercontent.com/zexaldragneel/selura-updates/main/latest.json"

private data class SeluraUpdateOffer(
    val versionCode: Int,
    val versionName: String,
    val notes: String,
    val releaseUrl: String,
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
            )
        } finally {
            connection.disconnect()
        }
    }
}

/**
 * Called once on a fresh launch after the library/database startup gates.
 * Never interrupts offline reading, never silently installs an APK, and never
 * sends GitHub credentials from the Android device.
 */
@Composable
fun SeluraStartupUpdateCheck() {
    val uriHandler = LocalUriHandler.current
    var offered by remember { mutableStateOf<SeluraUpdateOffer?>(null) }

    LaunchedEffect(Unit) {
        offered = withContext(Dispatchers.IO) {
            runCatching { SeluraReleaseFeed.check(BuildConfig.VERSION_CODE) }.getOrNull()
        }
    }

    val update = offered ?: return
    AlertDialog(
        onDismissRequest = { offered = null },
        title = { Text("Selura Manga update available") },
        text = {
            Column {
                Text("A newer version is ready: ${update.versionName}")
                if (update.notes.isNotBlank()) {
                    Text(
                        text = update.notes,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(top = 12.dp),
                    )
                }
                Text(
                    text = "Your manga library and reading progress stay in the app. " +
                        "Install the new APK over your existing Selura Manga.",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 12.dp),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    offered = null
                    uriHandler.openUri(update.releaseUrl)
                },
            ) {
                Text("View update")
            }
        },
        dismissButton = {
            TextButton(onClick = { offered = null }) {
                Text("Later")
            }
        },
    )
}
