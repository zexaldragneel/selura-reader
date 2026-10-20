# Selura orphaned extensions — 18-provider development batch

Status: **source importer, contract tests, and GitHub Actions APK pipeline implemented; compilation, signing, APK publication and live Android chapter reading must be verified separately.**

## Requested providers (exactly 18; NHentai is excluded)

| Display name (no Selura prefix) | Pinned Keiyoushi source module | Isolated Selura module |
|---|---|---|
| 3Hentai | all/hentai3 | all/selurahentai3 |
| AllPornComic | en/allporncomic | en/seluraallporncomic |
| Asura Scans | en/asurascans | en/seluraasurascans |
| Doujins | en/doujins | en/seluradoujins |
| Flame Comics | en/flamecomics | en/seluraflamecomics |
| HDoujin | all/hdoujin | all/selurahdoujin |
| Hentai4Free | en/hentai4free | en/selurahentai4free |
| HentaiHand | all/hentaihand | all/selurahentaihand |
| HentaiRead | en/hentairead | en/selurahentairead |
| Hiperdex | en/hiperdex | en/selurahiperdex |
| Hive Scans | en/hivescans | en/selurahivescans |
| MangaGeko | en/mangarawclub | en/seluramangageko |
| Mangakakalot | en/mangakakalot | en/seluramangakakalot |
| Mgread.io | en/mgreadio | en/seluramgreadio |
| ToonGod | en/toongod | en/seluratoongod |
| Toonily | en/toonily | en/seluratoonily |
| Vortex Scans | en/vortexscans | en/seluravortexscans |
| WebtoonXYZ | en/webtoonxyz | en/selurawebtoonxyz |

## Safety contract

- All 18 source modules are copied, **never moved**. The original module and extension are not overwritten.
- Visible provider names stay unchanged (no `Selura` prefix). Internal APK packages get `selura` prefixes so Android can distinguish the separate APKs.
- New sources use immutable `source.versionId = 7301`; pinned upstream numeric `id` overrides are remapped deterministically using a fixed seed and source module. **Do not change either identity rule after publishing** or installed Selura-origin entries will become orphaned.
- Existing Keiyoushi/Yuzono APKs, source IDs, library entries, favorites, downloaded pages, categories, bookmarks and read progress are untouched.
- The new source IDs do **not** automatically adopt existing entries from older extensions. Any future optional migration must match chapters and copy history nondestructively before changing entries.
- Remove overlapping link-intent filters; never seize original extension web links. Do not bypass providers' authentication, age restrictions or request throttling.
- Keep Apache-2.0 LICENSE and per-module `SELURA_ORIGIN.md` with attribution and a fixed upstream commit.
- **NHentai is deliberately excluded**; the user's already working independently maintained NHentai extension stays separate.

## Provenance and current limits

- Source: [Keiyoushi/extensions-source](https://github.com/keiyoushi/extensions-source), Apache-2.0, pinned Git SHA `ff521c17bb3e503c01e658e8fac00b60a95829f3`.
- These are isolated **derivatives**, not fully standalone codebases. GitHub Actions still pulls the pinned Keiyoushi build framework and providers. The eventual independent repository will need vendored and maintained shared libraries and a Mihon-compatible `index.pb` catalogue.
- Identifying the source code and compiling extensions does **not** prove a remote provider is online. Each extension still needs device testing for search, chapter list, images, reading progress and update compatibility.
- New APKs are separate from the native Selura Manga app (`com.selura.manga`). Installing an extension does not require uninstalling that app.

## CI & installation gate

1. The `Selura Orphaned 18 Extension APKs` workflow runs six Python contract tests and creates 18 isolated modules at the pinned revision.
2. Three independent GitHub Actions build jobs each compile, lint, sign and verify six APKs using the established Selura certificate, increasing version code, package name, SHA-256 and `aapt` package information.
3. Only if **all 18** pass does GitHub Releases get a prerelease containing 18 APKs. Failed or partial runs must not be described as successful releases.
4. After successful CI, install only chosen APKs, grant extension trust in Selura Manga, open Browse → Sources, search a title, read a full chapter, revisit the chapter, and verify original library/read state is unchanged.
5. Do not delete existing extensions, restore over app storage or migrate original source IDs during this pilot.

For the first builds, leave the branch and pull request unmerged while Android verification is pending.
