#!/usr/bin/env python3
"""Remove unnecessary upstream-facing navigation, not the native reader or attribution.

Apply AFTER apply_branding.py on the pinned Mihon checkout. Keep original
Apache-2.0 licenses, embedded library metadata, engine, backups and source IDs.
"""
import argparse
from pathlib import Path

PREFIX="app/src/main/java/"
ABOUT=PREFIX+"eu/kanade/presentation/more/settings/screen/about/AboutScreen.kt"
MORE=PREFIX+"eu/kanade/presentation/more/MoreScreen.kt"
TAB=PREFIX+"eu/kanade/tachiyomi/ui/more/MoreTab.kt"
LOGO=PREFIX+"eu/kanade/presentation/more/LogoHeader.kt"
MAIN=PREFIX+"eu/kanade/tachiyomi/ui/main/MainActivity.kt"

class SeluraUiPatchError(RuntimeError):
    pass

def replace_one(s, before, after, label):
    count=s.count(before)
    if count!=1:
        raise SeluraUiPatchError(f"{label}: expected one audited marker, found {count}")
    return s.replace(before,after,1)

# Keep public version functions used by SettingsMainScreen and native license
# navigation. About must not display the original project's privacy policy:
# Selura does not have its own published privacy policy yet.
ABOUT_PREFIX = """package eu.kanade.presentation.more.settings.screen.about

import android.content.Context
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import cafe.adriel.voyager.navigator.LocalNavigator
import cafe.adriel.voyager.navigator.currentOrThrow
import eu.kanade.domain.ui.UiPreferences
import eu.kanade.presentation.components.AppBar
import eu.kanade.presentation.more.LogoHeader
import eu.kanade.presentation.more.settings.widget.TextPreferenceWidget
import eu.kanade.presentation.util.LocalBackPress
import eu.kanade.presentation.util.Screen
import eu.kanade.tachiyomi.BuildConfig
import eu.kanade.tachiyomi.util.lang.toDateTimestampString
import eu.kanade.tachiyomi.util.system.copyToClipboard
import eu.kanade.tachiyomi.util.system.isFossBuildType
import eu.kanade.tachiyomi.util.system.isNightlyBuildType
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import mihon.app.di.appGraph
import tachiyomi.i18n.MR
import tachiyomi.presentation.core.components.ScrollbarLazyColumn
import tachiyomi.presentation.core.components.material.Scaffold
import tachiyomi.presentation.core.i18n.stringResource
import uy.kohesive.injekt.Injekt
import uy.kohesive.injekt.api.get
import kotlin.time.Instant

object AboutScreen : Screen() {
    private const val SELURA_RELEASES = "https://github.com/zexaldragneel/selura-reader/releases"
    private const val SELURA_REPOSITORY = "https://github.com/zexaldragneel/selura-reader"

    @Composable
    override fun Content() {
        val context = LocalContext.current
        val navigator = LocalNavigator.currentOrThrow
        val uriHandler = LocalUriHandler.current
        val handleBack = LocalBackPress.current
        val crashLogUtil = context.appGraph.crashLogUtil
        Scaffold(
            topBar = { scrollBehavior ->
                AppBar(
                    title = stringResource(MR.strings.pref_category_about),
                    navigateUp = if (handleBack != null) handleBack::invoke else null,
                    scrollBehavior = scrollBehavior,
                )
            },
        ) { contentPadding ->
            ScrollbarLazyColumn(contentPadding = contentPadding) {
                item { LogoHeader(iconPadding = PaddingValues(vertical = 56.dp)) }
                item {
                    TextPreferenceWidget(
                        title = "Selura Manga",
                        subtitle = "Developed by Zexal Dragneel",
                    )
                }
                item {
                    TextPreferenceWidget(
                        title = stringResource(MR.strings.version),
                        subtitle = getVersionName(withBuildDate = true),
                        onPreferenceClick = {
                            context.copyToClipboard("Debug information", crashLogUtil.getDebugInfo())
                        },
                    )
                }
                item {
                    TextPreferenceWidget(
                        title = "Selura releases",
                        subtitle = "Updates and release notes",
                        onPreferenceClick = { uriHandler.openUri(SELURA_RELEASES) },
                    )
                }
                item {
                    TextPreferenceWidget(
                        title = "Source code",
                        subtitle = "zexaldragneel/selura-reader",
                        onPreferenceClick = { uriHandler.openUri(SELURA_REPOSITORY) },
                    )
                }
                // Required upstream and third-party attributions remain accessible.
                item {
                    TextPreferenceWidget(
                        title = stringResource(MR.strings.licenses),
                        onPreferenceClick = { navigator.push(OpenSourceLicensesScreen()) },
                    )
                }
            }
        }
    }

"""
def patch_about(s):
    required=["object AboutScreen : Screen() {","    fun getVersionName(withBuildDate: Boolean): String {",
              "https://mihon.app/privacy/","https://facebook.com/mihonapp",
              "url = Constants.URL_DISCORD","onPreferenceClick = { uriHandler.openUri(RELEASE_URL) }"]
    if any(s.count(v)!=1 for v in required):
        raise SeluraUiPatchError("Pinned About UI changed; refuse cleanup patch")
    footer=s[s.index("    fun getVersionName(withBuildDate: Boolean): String {"):]
    if not footer.rstrip().endswith("}"):
        raise SeluraUiPatchError("About source closure changed")
    return ABOUT_PREFIX+footer

def patch_more(s):
    s=replace_one(s,"import androidx.compose.ui.platform.LocalUriHandler\n","", "old Help link import")
    s=replace_one(s,"import mihon.icons.materialsymbols.automirroredrounded.Help\n","","old Help icon import")
    s=replace_one(s,"import mihon.icons.materialsymbols.roundedfilled.VolunteerActivism\n","","donation icon import")
    s=replace_one(s,"import tachiyomi.core.common.Constants\n","","Mihon help URL import")
    s=replace_one(s,"    onClickSupport: () -> Unit,\n","","support navigation param")
    s=replace_one(s,"    val uriHandler = LocalUriHandler.current\n\n","","upstream URL handler")
    s=replace_one(s,'''            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_support_us),
                    icon = MaterialSymbols.RoundedFilled.VolunteerActivism,
                    onPreferenceClick = onClickSupport,
                )
            }
''',"","legacy donation entry")
    s=replace_one(s,'''            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_help),
                    icon = MaterialSymbols.AutoMirroredRounded.Help,
                    onPreferenceClick = { uriHandler.openUri(Constants.URL_HELP) },
                )
            }
''',"","legacy help entry")
    return s

def patch_tab(s):
    s=replace_one(s,"import mihon.feature.support.SupportUsScreen\n","","legacy support import")
    return replace_one(s,"            onClickSupport = { navigator.push(SupportUsScreen()) },\n","","legacy support navigation")

def patch_logo(s):
    return replace_one(s,"painterResource(R.drawable.ic_mihon)","painterResource(R.drawable.selura_manga_icon)","native Selura logo")

def patch_main(s):
    # Call was left by apply_branding.py as the old upstream donation popup.
    s=replace_one(s,'''                    ShowDonationCampaign()
''',"","startup donation pop-up")
    start=s.find("        // App updates\n")
    end=s.find("        // Extensions updates\n")
    if start<0 or end<=start or s.count("        // App updates\n")!=1 or s.count("        // Extensions updates\n")!=1:
        raise SeluraUiPatchError("MainActivity legacy upstream updater markers changed")
    # Keep installed source extension update checks, now delegated to the
    # original worker; the independent Selura update prompt is separate.
    s=s[:start]+"""        // SeluraStartupUpdateCheck handles signed Selura releases.
        // Do not query the original project's application release feed.

"""+s[end:]
    return s

def patch(root):
    root=Path(root).resolve()
    transforms={ABOUT:patch_about,MORE:patch_more,TAB:patch_tab,LOGO:patch_logo,MAIN:patch_main}
    pending={}
    for name,transform in transforms.items():
        path=root/name
        if not path.is_file():
            raise SeluraUiPatchError("Missing pinned native file: "+name)
        old=path.read_text(encoding="utf-8")
        newer=transform(old)
        if newer==old:
            raise SeluraUiPatchError("Unexpected unchanged source: "+name)
        pending[path]=newer
    # Fail closed before any Kotlin source is written.
    for path,newer in pending.items():
        path.write_text(newer,encoding="utf-8")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("upstream",type=Path)
    patch(p.parse_args().upstream)
