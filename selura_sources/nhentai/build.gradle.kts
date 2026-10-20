import io.github.keiyoushi.gradle.api.ContentWarning

plugins {
    alias(kei.plugins.extension)
}

keiyoushi {
    // New name and source IDs; original Cursed Yuzono library stays intact.
    name = "Selura NHentai"
    versionCode = 2
    contentWarning = ContentWarning.NSFW
    libVersion = "1.4"

    listOf("all", "en", "ja", "zh").forEach { sourceLang ->
        source {
            lang = sourceLang
            baseUrl = "https://nhentai.net"
        }
    }

    deeplink {
        host("nhentai.net")
        path("/g/..*")
    }
}

dependencies {
    implementation(project(":lib:randomua"))
}
