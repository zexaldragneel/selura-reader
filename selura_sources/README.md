# Selura NHentai.net — independent Android source extension

**Pilot for the exact extension shown on the owner's phone:** `NHentai` by **Cursed Yūzōnō**, version **1.4.62**, which uses `https://nhentai.net`. `nHentai.com (unoriginal)` is a separate Keiyoushi extension. The superseded `selura_sources/nhentaito/` experiment addresses a different hostname and **is not the shipped module**.

## Verified source and changes
- Adapted from `yuzono/cursed-manga-extensions@5dad5cf65dce98bb05ba8edf1f38770585e032b9`, `src/all/nhentai`, Apache-2.0; upstream copyright and license remain. Original source module is not changed.
- Stored first-party code in `selura_sources/nhentai/NHentai.kt` and supporting `NHDto.kt`/`NHUtils.kt`, built by Yuzono's pinned framework.
- Original code randomly selected an image CDN for *each page*. Selura chooses a consistent primary image server for the entire page list and recovers on transient image loading errors using only the site's own declared HTTPS nHentai image hosts.
- Recovery is bounded (up to two tries on each of at most five hosts). No retries for authorization denied or rate-limited HTTP 401/403/429. A chapter is rejected with an explicit error if the API advertises more pages than the data contains.
- **Separate package** `eu.kanade.tachiyomi.extension.all.seluranhentai` and source IDs, first-party name `Selura NHentai`. NSFW content warning retained. It will not overwrite the Yuzono APK or silently replace existing library items.

## Build
- Installer: `python3 selura_sources/apply_source.py <yuzono-source-checkout>`.
- Contract tests: `python3 -m unittest discover -s selura_sources/tests -v`.
- GitHub Actions: `.github/workflows/selura-sources.yml` clones pinned Yuzono source only as the compilation framework, adds Selura's independent source module, compiles the Android extension with Java 25, signs with the existing encrypted Selura release key, checks package ID and signing fingerprint, and publishes a source APK.
- **Build #8 passed**: https://github.com/john-selwyn/selura-reader/actions/runs/39390201876
- **Signed standalone APK**: https://github.com/john-selwyn/selura-reader/releases/download/test-selura-source-pr-25-run-8/selura-nhentai.apk — SHA-256 `25fb6b2ba8e6331b8d8059059287af256a0ffd26dac85f8673c5f350f532016a`.

## Phone acceptance
1. **Keep the original Cursed Yuzono NHentai, Keiyoushi and Selura apps installed.**
2. Install the separate `selura-nhentai.apk`; in Selura Browser, authorize/trust the new extension if prompted.
3. Open **Selura NHentai** under Browse → Sources and search for a gallery you've experienced issues with. Do **not** expect existing Library items to automatically switch source IDs.
4. Test total chapter page count, image loading completeness, speed, retry errors and reading progress against the existing extension.
5. If the new source still stalls, record an example gallery URL and the app's error text (without sharing passwords or cookies). We can then distinguish missing CDN access, API data, image responses or device-specific issues.

Do not make claims of a successful user-facing fix until device testing. Do not bypass provider access restrictions. This adapter and its Apache-2.0 dependencies are not official Yuzono or Mihon releases.
