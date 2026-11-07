package eu.kanade.tachiyomi.ui.organizer

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import eu.kanade.presentation.more.settings.widget.TextPreferenceWidget
import eu.kanade.tachiyomi.BuildConfig
import eu.kanade.tachiyomi.R
import mihon.icons.materialsymbols.MaterialSymbols
import mihon.icons.materialsymbols.rounded.Info

/** Installed APK constants, never the update feed or the pinned engine commit. */
@Composable
fun SeirynBuildVersion() {
    var showDetails by rememberSaveable { mutableStateOf(false) }
    val context = LocalContext.current
    val title = stringResource(R.string.organizer_build_version)
    // The native signing workflow assigns versionCode = 1000 + GitHub run_number.
    val build = stringResource(R.string.organizer_build_number, BuildConfig.VERSION_CODE - 1000)
    val details = stringResource(
        R.string.organizer_build_details,
        build, BuildConfig.VERSION_NAME, BuildConfig.VERSION_CODE, BuildConfig.APPLICATION_ID,
    )
    TextPreferenceWidget(
        title = title,
        subtitle = build,
        icon = MaterialSymbols.Rounded.Info,
        onPreferenceClick = { showDetails = true },
    )
    if (showDetails) AlertDialog(
        onDismissRequest = { showDetails = false },
        title = { Text(title) },
        text = { Text(details) },
        confirmButton = {
            TextButton(onClick = { showDetails = false }) { Text(stringResource(R.string.organizer_close)) }
        },
        dismissButton = {
            TextButton(onClick = {
                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText(title, details))
            }) { Text(stringResource(R.string.organizer_copy_version)) }
        },
    )
}

