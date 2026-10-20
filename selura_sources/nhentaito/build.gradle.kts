import io.github.keiyoushi.gradle.api.ContentWarning

plugins {
    alias(kei.plugins.extension)
}

keiyoushi {
    // Distinct extension package and source ID: does not overwrite Keiyoushi.
    name = "Selura NHentai.to"
    versionCode = 1
    contentWarning = ContentWarning.NSFW
    libVersion = "1.6"
    theme = "galleryadults"

    listOf("en", "ja", "zh", "ko", "all").forEach { language ->
        source {
            lang = language
            baseUrl = "https://nhentai.to"
        }
    }
}
