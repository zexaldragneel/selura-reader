# Selura Sources — NHentai.to pilot

## What this is
A **real Android source extension APK** for the Selura Manga / Mihon-compatible engine, not a website shortcut. The provider-specific adapter is developed and versioned in the Selura repository. It uses the pinned Apache-2.0 Keiyoushi extension build framework and the shared `GalleryAdults` implementation only for compilation.

**This pilot targets https://nhentai.to specifically.** It is *not* `nhentai.net`, `nhentai.xxx`, or `nhentai.com`. Confirm the hostname of the malfunctioning installed source before claiming the underlying problem is fixed.

## Reliability improvements
- Two bounded attempts at the original image on network errors and transient HTTP 5xx responses, plus up to four HTTPS fallbacks **only when explicitly provided by the original source**, restricted to the image host or the `nhentai.to` domain.
- Do **not** retry HTTP 401, 403 or 429; respect access controls and site throttling. Do not introduce any CAPTCHA or authentication bypass.
- Treat a successful HTML error page as a bad image and try declared fallbacks where available.
- Compare extracted page count with advertised gallery page count; try the existing alternate page extraction path once rather than silently showing a truncated chapter. If both fail, show an explicit incomplete-chapter error.
- Distinct extension identity `eu.kanade.tachiyomi.extension.all.seluranhentaito` and source name `Selura NHentai.to`; no signature collision or automatic replacement of the installed Keiyoushi source.
- Extension retains an **NSFW content warning**; this source is intended only for adults who are lawfully permitted to access the selected site.

## Build and attribution
- Owned code: `selura_sources/nhentaito/`; installer: `selura_sources/apply_source.py`.
- Build toolchain pinned to `keiyoushi/extensions-source@ff521c17bb3e503c01e658e8fac00b60a95829f3`, Apache 2.0. The upstream adapter is used as an audited starting point, but the Selura provider implementation is stored separately and never overwrites the Keiyoushi adapter.
- Run `python3 -m unittest discover -s selura_sources/tests -v` for contract checks.
- GitHub Actions `.github/workflows/selura-sources.yml` builds `:src:all:seluranhentaito:assembleRelease` using Java 25, applies the existing encrypted Selura signing certificate only in CI, validates APK package/signing identity and creates a separately named GitHub prerelease asset.
- The original project and modified source are subject to Apache-2.0 attribution requirements. This is not an official Keiyoushi or Mihon distribution.

## Safety and compatibility
- **Do not uninstall** Keiyoushi or Mihon and do not delete imported manga or app data.
- The new source uses **a different source ID**. Existing titles remain linked to the original source; they are *not automatically migrated*, even when the same title is accessible on this source.
- Install the preview APK only after GitHub Actions produces and verifies it. Verify under Selura → Browse → Extensions / Sources, trust the extension only if you understand its separate signing identity, browse the Selura-named source, open a test gallery and check that every expected page displays.
- This cannot guarantee access to a remote server, circumvent rate limits, or fix an unrelated `nhentai.net` provider.
- Do not merge or replace the stable Selura reader while this source remains unverified.

## Next checks
1. Confirm the exact extension name/hostname shown in Selura's Installed extensions list.
2. Verify the signed source APK is built in GitHub Actions.
3. Test loading a test gallery on the Android phone and compare full page count, retry behavior, and load time against the current extension.
4. If the actual problematic source is `nhentai.net`, design and test a **separate** adapter for that domain without pretending `nhentai.to` is the same site.
