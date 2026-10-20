# Selura Extensions — independent maintenance track

This directory begins the **Selura-controlled extension family**. It is **not
the Keiyoushi official repository**, and Selura has no affiliation with
Keiyoushi, Mihon, or source websites.

## Phase 1 — proven open-source foundation

- **Existing fast Selura NHentai** is separately maintained under
  `selura_sources/nhentai` (adapted from Yuzono, not Keiyoushi). Keep it.
- **New Selura MangaDex pilot** is derived from
  [Keiyoushi/extensions-source](https://github.com/keiyoushi/extensions-source),
  pinned to `ff521c17bb3e503c01e658e8fac00b60a95829f3`.
- The Apache License 2.0 and upstream copyright notices remain with the copied
  module. The build copies Keiyoushi's *source code* into a separate
  `src/all/seluramangadex` Gradle module without changing its original.
- Own APK package: `eu.kanade.tachiyomi.extension.all.seluramangadex`.
  The source *name* is `Selura MangaDex`, which is also used by Keiyoushi's
  generated source ID algorithm. This avoids stealing the original MangaDex
  source identity.
- We disable the duplicated website deep-link intent filter so the Selura
  pilot cannot hijack links belonging to the user's existing extension.
- The signed APK is built in GitHub Actions from the Selura-owned script,
  with an increasing CI version code and the established Selura release
  signing key. The original extension remains installed and its library
  entries remain associated with its original source ID.

### Developer / CI commands

```sh
python3 -m unittest discover -s selura_extensions/tests -v
git clone https://github.com/keiyoushi/extensions-source.git keiyoushi-deps
git -C keiyoushi-deps checkout ff521c17bb3e503c01e658e8fac00b60a95829f3
python3 selura_extensions/apply_keiyoushi.py keiyoushi-deps --version-code 1
# In keiyoushi-deps with Java 25 and Android SDK:
./gradlew :src:all:seluramangadex:assembleRelease
```

**Do not install locally unsigned builds over the independently signed
release**. Do not install this in place of existing Keiyoushi MangaDex.
Source extensions are executable Android APKs; users should only trust
those that they deliberately choose.

### Acceptance checks

1. GitHub Actions completes tests, compilation, lint, and APK signature/package checks.
2. Install the separate Selura MangaDex preview alongside the original.
3. Open **Browse → Sources → Selura MangaDex**, search for a title, load a
   chapter, browse pages, then reopen and check reading position.
4. Verify **original MangaDex**, **Selura NHentai**, and all existing saved manga
   still work. A new source identity does **not** migrate existing library
   entries or downloads automatically.

## Independence roadmap

1. **Now:** own first-party extension identities, separate signed APKs, own
   overlay/source changes, reproducible pinned Keiyoushi build system.
2. **Next:** vendor the subset of Gradle build logic, core interfaces and
   libraries actually needed for supported Selura sources in a dedicated
   Selura-controlled repository. At this stage builds stop fetching Keiyoushi.
3. **Later:** publish a Selura-managed extension repository index (current
   Mihon-compatible `index.pb`), automate update signing and releases,
   maintain compatible source adapters ourselves, and offer safe migration
   of manga library entries with progress/history preservation.

**Current limitation:** Phase 1 **still downloads Keiyoushi build tooling and
the original MangaDex source at a fixed revision**. The pinned baseline will
not silently follow Keiyoushi updates, but until the build tools are vendored
we cannot honestly call builds fully upstream-independent. Website/API
availability remains outside Selura's control.

The existing separate `selura_sources` branch and PR #25 should not be
deleted or modified solely to implement this foundation.
