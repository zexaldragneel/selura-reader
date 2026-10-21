# Five additional Selura-maintained manga source APKs

These are **real Kotlin/Mihon source extensions**, independently compiled and signed by Selura GitHub Actions. They are not links or embedded browser bookmarks.

| Provider (store label) | Upstream module (Keiyoushi pinned) | Independent internal module | Content | Homepage |
|---|---|---|---|---|
| Comix.to | `en/comix` | `en/seluracomixto` | MIXED | https://comix.to |
| Weeb Central | `en/weebcentral` | `en/seluraweebcentral` | MIXED | https://weebcentral.com |
| Kagane | `all/kagane` | `all/selurakagane` | MIXED | https://kagane.si |
| Manga Ball | `all/mangaball` | `all/seluramangaball` | MIXED | https://mangaball.com |
| MangaHub | `en/mangahubio` | `en/seluramangahubio` | MIXED | https://mangahub.io |

Upstream repository: https://github.com/keiyoushi/extensions-source at immutable commit `ff521c17bb3e503c01e658e8fac00b60a95829f3`. Apache-2.0 licenses and original author notices are retained in each copied module. This batch uses new immutable Selura `source.versionId=7303` with independent Android package names and a distinct SHA-256 seed for remapping explicit source IDs. Original module source files are copied and packaged without overwriting upstream source modules.

**Do not replace** previously installed Comick (Unoriginal): Comick's `comick.live` source and **Comix.to** are different websites and remain separate providers. NHentai is not duplicated. None of the existing 38 APK packages, source IDs, or stored manga records are migrated or removed.

## Rollout and acceptance

1. `selura_extensions/expansion_5.py` transforms the pinned upstream source checkout with deterministic package/source identity. Unit contracts confirm no overwrite or duplicate IDs.
2. [reader GitHub Actions](../.github/workflows/selura-expansion-5.yml) runs two shards (3 and 2), Gradle Kotlin compilation and lint, and verifies the existing Selura signing certificate on **all five** APKs before publishing a single immutable prerelease.
3. The separate `zexaldragneel/selura-extensions` store publisher consumes only that exact prerelease after all builds pass, verifies all prior 38 APKs, signer and source IDs, and publishes **43** packages to the existing `repo.json` URL.
4. The owner installs Comix.to and other desired sources under Selura Manga → Browse → Extensions. Test *search → manga details → chapter list → real page images → offline download* on Android. A published APK or successful Gradle compilation does not prove a source website remains reachable. Comix.to has historically returned 403 under some conditions; do not attempt to circumvent website authentication, rate limiting or access restrictions.

Android application `com.selura.manga` does not need an APK update to discover catalog additions.
