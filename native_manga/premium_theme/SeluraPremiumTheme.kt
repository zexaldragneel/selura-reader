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
            primary = Color(0xFFEED09A),
            onPrimary = Color(0xFF22180E),
            primaryContainer = Color(0xFF3F3021),
            onPrimaryContainer = Color(0xFFFFE6BD),
            secondary = Color(0xFFD3AC73),
            onSecondary = Color(0xFF20130E),
            secondaryContainer = Color(0xFF412C1F),
            onSecondaryContainer = Color(0xFFF8E5C9),
            tertiary = Color(0xFFD99374),
            onTertiary = Color(0xFF21130E),
            background = Color(0xFF090807),
            onBackground = Color(0xFFF5E5C6),
            surface = Color(0xFF161110),
            onSurface = Color(0xFFF5E5C6),
            surfaceVariant = Color(0xFF312923),
            onSurfaceVariant = Color(0xFFDCC8A6),
            outline = Color(0xFFAE8A50),
            outlineVariant = Color(0xFF4F3B29),
            surfaceContainerLowest = Color(0xFF090807),
            surfaceContainerLow = Color(0xFF20130E),
            surfaceContainer = Color(0xFF211815),
            surfaceContainerHigh = Color(0xFF2D211A),
            surfaceContainerHighest = Color(0xFF3E2D22),
            surfaceBright = Color(0xFF493322),
            surfaceDim = Color(0xFF090807),
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
            if (artwork) listOf(Color(0xFF251B19), Color(0xFF170F10), Color(0xFF090807))
            else listOf(Color(0xFF090807), Color(0xFF090807)),
        )
        SeluraLibraryTheme.NEON_NIGHT -> Brush.verticalGradient(
            if (artwork) listOf(Color(0xFF1C1642), Color(0xFF10142C), Color(0xFF080A18))
            else listOf(Color(0xFF080A18), Color(0xFF080A18)),
        )
    }
