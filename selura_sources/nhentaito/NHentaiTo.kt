// Selura-maintained source adapter derived from Keiyoushi NHentai.to (Apache-2.0).
// Original upstream attribution: https://github.com/keiyoushi/extensions-source
package eu.kanade.tachiyomi.extension.all.seluranhentaito

import eu.kanade.tachiyomi.multisrc.galleryadults.GalleryAdults
import eu.kanade.tachiyomi.multisrc.galleryadults.SortOrderFilter
import eu.kanade.tachiyomi.multisrc.galleryadults.imgAttr
import eu.kanade.tachiyomi.multisrc.galleryadults.toDate
import eu.kanade.tachiyomi.source.model.Filter
import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.Page
import keiyoushi.annotation.Source
import keiyoushi.network.get
import keiyoushi.utils.firstInstanceOrNull
import keiyoushi.utils.parseAs
import kotlinx.serialization.json.JsonElement
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Response
import org.jsoup.nodes.Element
import org.jsoup.nodes.Document
import java.io.IOException

@Source
abstract class NHentaiTo : GalleryAdults() {

    override val mangaLang = when (lang) {
        "en" -> LANGUAGE_ENGLISH
        "ja" -> LANGUAGE_JAPANESE
        "zh" -> LANGUAGE_CHINESE
        "ko" -> LANGUAGE_KOREAN
        "all" -> LANGUAGE_MULTI
        else -> throw IllegalArgumentException("Invalid lang: $lang")
    }

    override val supportSpeechless = true

    override val searchPopularPath = ""

    /**
     * Bounded, source-specific image recovery. Never retry rate limits or access
     * denials and never send fallback requests to an unrelated host.
     * No CAPTCHA, authentication, or anti-bot controls are bypassed.
     */
    override fun OkHttpClient.Builder.configureClient() = apply {
        addInterceptor { chain ->
            val request = chain.request()
            val fragment = request.url.fragment.orEmpty()
            val path = request.url.encodedPath.lowercase()
            val isImage = listOf(".jpg", ".jpeg", ".png", ".webp", ".gif")
                .any { path.endsWith(it) }
            if (!isImage && !fragment.startsWith("fallback")) {
                return@addInterceptor chain.proceed(request)
            }

            val original = request.url.newBuilder().fragment(null).build()
            val fallbackUrls = if (fragment.startsWith("fallback")) {
                runCatching {
                    fragment.substringAfter("fallback").parseAs<List<String>>()
                }.getOrDefault(emptyList())
                    .mapNotNull { candidate ->
                        candidate.toHttpUrlOrNull()?.takeIf { url ->
                            url.scheme == "https" &&
                                (url.host == original.host ||
                                    url.host == "nhentai.to" ||
                                    url.host.endsWith(".nhentai.to"))
                        }
                    }
            } else {
                emptyList()
            }
            val candidates = (listOf(original) + fallbackUrls).distinct().take(5)
            var lastFailure: IOException? = null

            for ((index, url) in candidates.withIndex()) {
                val retries = if (index == 0) 2 else 1
                for (attempt in 0 until retries) {
                    val response = try {
                        chain.proceed(request.newBuilder().url(url).build())
                    } catch (error: IOException) {
                        lastFailure = error
                        continue
                    }

                    if (response.isRealSuccess()) return@addInterceptor response

                    // Access controls and site throttling must be respected.
                    if (response.code == 401 || response.code == 403 || response.code == 429) {
                        return@addInterceptor response
                    }

                    val canRetry = response.code in 500..599 && attempt + 1 < retries
                    if (canRetry || index < candidates.lastIndex) {
                        response.close()
                        continue
                    }
                    return@addInterceptor response
                }
            }
            throw lastFailure ?: IOException("Unable to load image from NHentai.to")
        }
    }

    /**
     * Fail visibly when page metadata is incomplete instead of silently showing
     * a truncated chapter. Try the site's thumbnail-based fallback once.
     */
    override suspend fun pageListParse(document: Document): List<Page> {
        val pages = super.pageListParse(document)
        val expected = document.selectFirst(mangaDetailInfoSelector)
            ?.totalPages()?.trim()?.toIntOrNull()
            ?: return pages
        if (expected <= 0 || expected > 2000 || pages.size == expected) return pages

        val recovered = pageListParseAlternative(document)
        if (recovered.size == expected &&
            recovered.all { it.imageUrl?.startsWith("https://") == true || it.url.isNotBlank() }
        ) {
            return recovered
        }
        throw IOException("Incomplete chapter: expected $expected images, found ${pages.size}. Retry or open in WebView.")
    }

    // popular

    override val popularMangaUrl get() = basicSearchUrl(
        0,
        "",
        FilterList(
            SortOrderFilter(emptyList())
                .apply {
                    state = 2
                },
        ),
    )

    override val latestUpdatesUrl get() = basicSearchUrl(
        0,
        "",
        FilterList(
            SortOrderFilter(emptyList())
                .apply {
                    state = 1
                },
        ),
    )

    override fun popularMangaSelector() = ".gallery a:not([rel~=sponsored])"
    override fun popularMangaNextPageSelector() = "a.next"

    override fun Element.mangaUrl() = absUrl("href")

    override fun Element.getCover() = selectFirst("#cover img")?.withFallback()

    override fun Element.mangaThumbnail() = selectFirst("img")?.withFallback()

    private fun Element.withFallback(): String? {
        val image = imgAttr().ifEmpty { return null }
        val fallbacks = attr("data-fallbacks")
        return if (fallbacks.isBlank()) image else "$image#fallback$fallbacks"
    }

    // Details
    override val mangaDetailInfoSelector = "#bigcontainer"
    override val idPrefixUri = "g"

    // Tags
    override fun getInfoSelector(tag: String) = "#info-block .field-name:contains($tag) .tags a"
    override fun Element.infoTagName() = selectFirst(".name")?.ownText() ?: ""

    // Pages
    override val serverPrefix = "i"

    override fun Element.totalPages() = getInfo("Pages")

    override fun Element.getTime() = selectFirst(".tags time")?.attr("datetime").toDate(null)

    override val thumbnailSelector = "#thumbnail-container .thumb-container"

    // search
    override fun basicSearchUrl(page: Int, query: String, filters: FilterList): String {
        val sortOrderFilter = filters.firstInstanceOrNull<SortOrderFilter>()
        val excludeTags = filters.firstInstanceOrNull<ExcludeFilter>()

        return "$baseUrl/search".toHttpUrl().newBuilder().apply {
            addQueryParameter("q", query.ifEmpty { "*" })
            sortOrderFilter?.state?.let { addQueryParameter("sort", getSortOrderURIs()[it].second) }
            excludeTags?.state?.let { addQueryParameter("exclude", it) }
            addQueryParameter("lang", mangaLang)
        }.build().toString()
    }

    // Filters
    override val supportsFilterFetching = false

    override fun getFilterList(data: JsonElement?) = FilterList(
        listOf(
            ExcludeFilter(),
        ) + super.getFilterList(data).list,
    )

    override fun getSortOrderURIs() = listOf(
        "Relevance" to "relevance",
        "Newest" to "newest",
        "Most favorited" to "most-favorited",
        "Most Liked" to "most-liked",
    )

    class ExcludeFilter : Filter.Text("Exclude Tags (seperate by comma)")

    fun Response.isRealSuccess() = isSuccessful && !peekBody(64).string().contains("<html", true)
}
