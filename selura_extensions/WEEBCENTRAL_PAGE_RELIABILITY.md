# Weeb Central — resilient public chapter image parsing

## Why this one-source update

The pinned Weeb Central adapter's chapter-image parser only read `abs:src` from `section[x-data~=scroll] > img`. On lazy-loaded image elements, `src` may be absent or contain a placeholder even when `data-src` contains the page URL. Previously, empty page results silently propagated to the reader, obscuring site layout or access failures.

## Kotlin change

- In **only** the isolated `en/seluraweebcentral` Kotlin module, prefer `abs:data-src`, then fall back to `abs:src`, choosing the first well-formed **HTTPS** image URL. Preserve all existing page order, any intentional repeated page URLs, the chapter path and HTMX `images?is_prev=False&reading_style=long_strip` request.
- Fail clearly with an `IOException` inviting the user to check the chapter in WebView if no valid page URLs remain. Do not fabricate pages, silently report successful zero-page chapters, or blindly retry a 403/429/Cloudflare challenge.
- Do not change Weeb Central's request headers, `rateLimit(1, 2.seconds)`, image downloads, existing source package/ID, user stored library entries or backups. No user agent spoofing, access-control bypass, forced caching, CDN host substitution, download rewriting or data migration. Unlike the withdrawn Hive Scans cache experiment, no cache policy is touched.
- Exact pinned Apache-2.0 source: `keiyoushi/extensions-source@ff521c17bb3e503c01e658e8fac00b60a95829f3`, with its licensing and attribution retained. Build only `:src:en:seluraweebcentral:assembleRelease` and `lintRelease` from the existing `expansion_5.prepare` source family, maintaining source versionId `7303`.
- Published store Weeb Central before update: `1.6.4001`, `versionCode 110001`, package `eu.kanade.tachiyomi.extension.en.seluraweebcentral`. Only publish a higher-version APK with the unchanged original Selura signing certificate SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`.

## Gates

1. Python regression contracts including fail-closed pinned source inspection and preservation of source IDs.
2. Full Kotlin release compilation and lint plus APK signature, package and higher-version inspection.
3. Publish only the one verified Weeb Central release in the `zexaldragneel/selura-extensions` store, retaining **42 byte-identical other APKs**, 43 byte-identical icons, 43 package identities and 341 original source IDs. Hive Scans stays on owner-accepted `v1.6.4430`. NHentai migration logic and Selura Manga Build #119 untouched.
4. Require owner Android acceptance: refresh Weeb Central extension only, browse/search a series, load a public chapter containing real images, verify repeated reading and a downloaded chapter offline if desired. Do not claim live runtime improvement or cache/network speed increase before user testing.

## Verification status

Implemented in a native extension branch. CI build, signing, publication and device acceptance must be tracked separately; source-only tests do not prove on-device site availability.
