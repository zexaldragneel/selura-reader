package eu.kanade.presentation.theme

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/**
 * Selura's opt-in visual layer. Preferences are entirely separate from Mihon's
 * manga/category/source database and reader settings. Default is untouched.
 */
enum class SeluraLibraryTheme(val key: String, val label: String) {
    DEFAULT("default", "Default"),
    CELESTIAL_XIANXIA("celestial_xianxia", "Celestial Xianxia"),
    NEON_NIGHT("neon_night", "Neon Night");

    companion object {
        fun fromKey(key: String?): SeluraLibraryTheme =
            entries.firstOrNull { it.key == key } ?: DEFAULT
    }
}

class SeluraLibraryAppearance(context: Context) {
    private val preferences: SharedPreferences =
        context.applicationContext.getSharedPreferences("selura_library_appearance_v1", Context.MODE_PRIVATE)

    var theme by mutableStateOf(SeluraLibraryTheme.fromKey(preferences.getString("theme", null)))
        private set
    var backgroundArtwork by mutableStateOf(preferences.getBoolean("background_artwork", true))
        private set
    var reducedEffects by mutableStateOf(preferences.getBoolean("reduced_effects", false))
        private set

    fun selectTheme(key: String) {
        theme = SeluraLibraryTheme.fromKey(key)
        preferences.edit().putString("theme", theme.key).apply()
    }

    fun updateBackgroundArtwork(enabled: Boolean) {
        backgroundArtwork = enabled
        preferences.edit().putBoolean("background_artwork", enabled).apply()
    }

    fun updateReducedEffects(enabled: Boolean) {
        reducedEffects = enabled
        preferences.edit().putBoolean("reduced_effects", enabled).apply()
    }
}

val LocalSeluraLibraryAppearance = staticCompositionLocalOf<SeluraLibraryAppearance?> { null }

/** Keep the default Material 3 theme exactly as upstream selects it. */
fun seluraColorScheme(base: ColorScheme, selected: SeluraLibraryTheme): ColorScheme =
    when (selected) {
        SeluraLibraryTheme.DEFAULT -> base
        SeluraLibraryTheme.CELESTIAL_XIANXIA -> darkColorScheme(
            primary = Color(0xFFEBC78B),
            onPrimary = Color(0xFF211525),
            primaryContainer = Color(0xFF54412D),
            onPrimaryContainer = Color(0xFFFFE4B7),
            secondary = Color(0xFF9DB9DA),
            onSecondary = Color(0xFF101B30),
            secondaryContainer = Color(0xFF263A54),
            onSecondaryContainer = Color(0xFFD7E5FB),
            tertiary = Color(0xFFFFD89B),
            onTertiary = Color(0xFF201522),
            background = Color(0xFF080F20),
            onBackground = Color(0xFFFFE9CD),
            surface = Color(0xFF10182B),
            onSurface = Color(0xFFFFE9CD),
            surfaceVariant = Color(0xFF25334A),
            onSurfaceVariant = Color(0xFFC4C9D8),
            outline = Color(0xFF91764F),
            outlineVariant = Color(0xFF4D4050),
            surfaceContainerLowest = Color(0xFF080F20),
            surfaceContainerLow = Color(0xFF101B30),
            surfaceContainer = Color(0xFF17233B),
            surfaceContainerHigh = Color(0xFF233047),
            surfaceContainerHighest = Color(0xFF303F56),
            surfaceBright = Color(0xFF34445A),
            surfaceDim = Color(0xFF080F20),
        )
        SeluraLibraryTheme.NEON_NIGHT -> darkColorScheme(
            primary = Color(0xFFAF83FF),
            onPrimary = Color(0xFF180B35),
            primaryContainer = Color(0xFF45239E),
            onPrimaryContainer = Color(0xFFE9DFFF),
            secondary = Color(0xFF69B4FF),
            onSecondary = Color(0xFF04182F),
            secondaryContainer = Color(0xFF183C72),
            onSecondaryContainer = Color(0xFFD3E6FF),
            tertiary = Color(0xFFDC8BFF),
            onTertiary = Color(0xFF290B38),
            background = Color(0xFF080A18),
            onBackground = Color(0xFFF1EDFF),
            surface = Color(0xFF0F1325),
            onSurface = Color(0xFFF1EDFF),
            surfaceVariant = Color(0xFF272842),
            onSurfaceVariant = Color(0xFFC1BED8),
            outline = Color(0xFF7652B9),
            outlineVariant = Color(0xFF393157),
            surfaceContainerLowest = Color(0xFF070916),
            surfaceContainerLow = Color(0xFF10132A),
            surfaceContainer = Color(0xFF171B34),
            surfaceContainerHigh = Color(0xFF222743),
            surfaceContainerHighest = Color(0xFF303350),
            surfaceBright = Color(0xFF383B60),
            surfaceDim = Color(0xFF080A18),
        )
    }

/** An original, shader-only sky; never caches bitmap copies of cover art. */
fun seluraLibraryBackground(selected: SeluraLibraryTheme, artwork: Boolean): Brush =
    when (selected) {
        SeluraLibraryTheme.DEFAULT -> Brush.verticalGradient(listOf(Color.Transparent, Color.Transparent))
        SeluraLibraryTheme.CELESTIAL_XIANXIA -> Brush.verticalGradient(
            if (artwork) listOf(Color(0xFF253954), Color(0xFF111B33), Color(0xFF080F20))
            else listOf(Color(0xFF080F20), Color(0xFF080F20)),
        )
        SeluraLibraryTheme.NEON_NIGHT -> Brush.verticalGradient(
            if (artwork) listOf(Color(0xFF1C1642), Color(0xFF10142C), Color(0xFF080A18))
            else listOf(Color(0xFF080A18), Color(0xFF080A18)),
        )
    }
