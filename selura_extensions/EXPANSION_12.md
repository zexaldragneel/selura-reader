# Selura — Keiyoushi expansion: 12 new source extensions

Status: **new build pipeline implemented; GitHub Actions, APK package/signature and Android-device tests must pass before store publication.**

## Exact provider list at pinned Keiyoushi revision

All sources come from upstream Apache-2.0 `keiyoushi/extensions-source` at immutable Git SHA `ff521c17bb3e503c01e658e8fac00b60a95829f3`.

| Display name | Upstream path | Independent internal package module | Content |
|---|---|---|---|
| Comick (Unoriginal) | all/comicklive | all/seluracomicklive | MIXED |
| GlobalComix | all/globalcomix | all/seluraglobalcomix | MIXED |
| MangaToon (Limited) | all/mangatoon | all/seluramangatoon | SAFE |
| Manga UP! | all/mangaup | all/seluramangaup | SAFE |
| MANGA Plus Creators by SHUEISHA | all/mangapluscreators | all/seluramangapluscreators | SAFE |
| NamiComi | all/namicomi | all/seluranamicomi | SAFE |
| Dynasty Scans | en/dynasty | en/seluradynasty | MIXED |
| Gunnerkrigg Court | en/gunnerkriggcourt | en/seluragunnerkriggcourt | SAFE |
| Mangago | en/mangago | en/seluramangago | MIXED |
| Mangahere | en/mangahere | en/seluramangahere | MIXED |
| MangaFox | en/mangafox | en/seluramangafox | MIXED |
| Manganato | en/manganelo | en/seluramanganato | MIXED |

This brings the public catalog from 26 to **38** sources only after the new APK build and catalog CI succeed. Not all source websites have been checked for current reachability; not every source has free chapters or an accessible API.

## Non-destructive source identity contract

- Preserve **all 26 existing Android APK package names, source IDs and stored manga** as they are. The new sources **never** reuse the existing `source.versionId=7301` family or older six-source family `versionId=2`.
- New source family: `source.versionId = 7302`, which must remain immutable after initial publication.
- Explicit upstream historical `id = NUMBER` overrides are remapped by deterministic SHA-256 seed `selura-expansion-v1:<isolated module>:<original ID>`. The public index must use **the exact same algorithm** for legacy explicit IDs.
- Shared language lists are faithfully represented in the public extension catalog from each pinned `build.gradle.kts`. Read full blocks for exact languages before publishing.
- Android package names are unique with internal `selura...` suffix. Visible source titles remain upstream names; no `Selura` prefix.
- Original source modules are **copied, never replaced**; attribution and Apache-2.0 LICENSE are retained with a provenance file. Overlapping deep links are removed to avoid hijacking installed original sources.
- Preserve original NHentai/MangaDex/18-orphan/6-batch entries, manga library, categories, progress, offline downloads and backup compatibility. No silent migration and no uninstallation.

## Build / release

- Three parallel CI shards each run four source builds + four lint tasks, after pinned revision validation and Python regression tests.
- Full release only if **all 12** APKs pass Gradle compile, lint, signer SHA-256, unique package and expected theme-adjusted version checks.
- Only publish the public store from immutable, verified GitHub prerelease APK assets. Validate **38 entries, 38 APKs and 38 icons** and original 26 package/source ID stability.
- After publication Android owner must refresh Extension stores and Extensions, install a few new sources, trust them, test search, chapter listings, images and resume. Remote provider uptime is independent of Selura.
