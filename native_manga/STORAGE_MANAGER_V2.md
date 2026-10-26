# Offline Storage Manager 2.0 — Phase 1: Read-only Usage Overview

## Owner acceptance / baseline

The owner confirmed **both** the signed Seiryn **Build #125** native reader performance update and **Doujins v1.6.5204** on their Android device on 2026-10-25. Treat those specific builds as the owner-tested baselines; no quantified memory, FPS or extension loading speeds were supplied.

## Real native feature

Adds an opt-in **Storage overview** item to **Seiryn → More → Settings → Downloads**, immediately alongside the existing **Check download storage** and **Review unfinished transfers** actions. Running it shows:

- Size of existing completed chapter files (CBZ archives + folder-stored chapter files), based on actual filesystem metadata
- Separate size for unfinished temporary chapter folders
- Counts of completed chapters, unfinished temporary chapter folders, manga folders, and inspected files
- Up to the **10 largest** manga folders by recorded completed-download bytes
- Clear indication of **unknown-size** files and **partial** counts if the safety limits are reached

The UI uses the existing Material alert/dialog conventions and Seiryn labels. There is no new navigation backend, no persisted metadata and no data changes. **This milestone is a read-only usage overview, not yet the full bulk-delete manager.**

## SAF safety and performance constraints

The `SeirynStorageOverview.scan()` implementation accesses only the configured SAF base directory's **existing** `downloads` folder by `findFile`. It runs under `Dispatchers.IO`, checks coroutine cancellation regularly and caps:

- 5,000 chapter folders/archives inspected
- 20,000 individual saved file entries with measured size
- 3,000 manga folders and the top 10 shown

SAF providers do not reliably expose file lengths or free filesystem capacity. Reported totals are **known existing file sizes only**, and unknown sizes are separately counted rather than considered corruption or deleted. When capped, output explicitly says **partial**. No storage-wide free space claim is made. Files are not opened to decode images, and neither the storage dashboard nor its UI invokes delete, rename, creation, writes, downloads, user data migration or network requests.

The preexisting health scanner and unfinished-transfer/resume controls are unchanged, including their limitations. Do not automatically resume downloads or remove chapters from a dashboard view. Native chapter reading, local cache, extension identities and signing remain unchanged.

## Implementation

Native source patch `native_manga/storage_manager_v2_overview.py` runs **after** `review_unfinished_transfers.py` against the pinned independent Mihon native snapshot. It adds `SeirynStorageOverview.kt`, an Android string resource and a read-only Download Settings action. Contract tests reject changed source anchors before writing any files, validate XML and preserve existing scan/recovery actions.

Build on the owner-tested **Build #125** branch `feature/seiryn-reader-v2-webtoon-decode-memory`. Preserve application ID `com.selura.manga`, signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`, public update metadata feed, GitHub repo, history/categories/bookmarks/downloads, stable extension IDs and upstream attribution.

## Release gates

- All native unit tests pass, source patch applies to pinned actual Kotlin code, full release Gradle `:app:assembleRelease` succeeds.
- Android `aapt` verifies same package and higher versionCode; `apksigner` verifies the permanent certificate; publish an immutable signed APK and version/checksum-matching public update feed.
- **Android device acceptance must be separate:** install in place over Build #125, open Downloads → Storage overview, inspect totals and top 10 titles, confirm the original health and unfinished transfer actions still work, read an online chapter and an offline downloaded chapter, and verify library/category/progress unchanged.
- No speed gains, measured storage numbers or phone acceptance are claimed from source/CI alone.

Next milestones can add *opt-in, confirmed* bulk-management UX and download recovery improvements after this read-only baseline works on the owner's device.
