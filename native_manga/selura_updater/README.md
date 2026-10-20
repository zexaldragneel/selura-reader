# Selura Manga in-app update notification

Selura now has a first-party Android startup update prompt. It is independent of Mihon's default updater, which remains disabled for the Selura build.

### Behavior
- On a fresh app launch, attempt an HTTPS GET to `https://raw.githubusercontent.com/zexaldragneel/selura-reader/gh-pages/updates/latest.json`.
- Silently continue offline if the feed is missing/unreachable, if content is invalid, or if versionCode is not newer than installed `com.selura.manga`.
- Show a themed Material update dialog with build name, release notes, **Download update** and **Later**.
- The download streams directly from the exact GitHub release APK into Selura's private `cacheDir/selura-apk-updates`, with progress percentage/MB, cancel, verification and retry states. No web browser or system Downloads app is needed.
- The expected `sha256` from the public feed is checked against the streamed APK bytes; Selura additionally verifies `com.selura.manga`, increasing versionCode and the installed app's signing certificate before launching an installation.
- For installation, Selura grants only temporary read access to its verified APK via the existing `com.selura.manga.provider` FileProvider. Android's package installer shows the required user confirmation; on Android 8+ the first install can require granting **Allow from this source** to Selura in system Settings. Silent APK installation is neither attempted nor supported.
- The app never contains GitHub tokens, secrets or signing material.

### Privacy and deployment blocker
**The repository `zexaldragneel/selura-reader` is public.** The update feed lives in a `gh-pages` branch inside the same repository and is served at a public HTTPS raw-content URL. The app never contains a token.

The owner has chosen a public repository and approved version metadata. The update prompt only activates once the `gh-pages` branch contains a newer signed build's metadata and the URL is reachable.

The verified native APK workflow maintains the public feed in the `gh-pages` branch, without requiring GitHub Pages configuration. The JSON contains only:
`schemaVersion`, `applicationId`, `versionCode`, `versionName`, `notes`, `releaseUrl`, and signed APK `sha256`. GitHub Actions generates it only *after* APK build and signing verification and release publication. It archives `selura-update-feed-private` as an Actions artifact before atomically publishing JSON to the same public repository's `gh-pages` branch. It never commits decrypted signing material.

The release is public; when a user taps Download update, Selura derives the fixed APK asset path from the allowlisted release tag and follows only trusted HTTPS GitHub asset hosts. No sign-in is necessary.

### Test cases
- Feed says versionCode equal to or below installed → no popup.
- Feed says newer versionCode with correct applicationId, 64-digit SHA-256 and release URL under `github.com/zexaldragneel/selura-reader/releases/tag/<tag>` → show dialog.
- Invalid repo, HTTP error, wrong app ID, malformed JSON, bad checksum, timeout, offline → no crash/no popup.
- Later dismisses for current launch; reopening can check again.
- Download update displays in-app progress; Cancel deletes partial APK, and Retry is available for network/checksum/identity errors.
- Wrong SHA-256, wrong application ID, wrong version, or wrong APK signing certificate blocks installation and displays a readable error.
- Download redirects stay on HTTPS GitHub asset hosts, and the APK size is bounded (256 MiB).
- After verification, Android's system installer prompts for confirmation; when required, the user can grant Selura's install permission in system Settings and tap Install again.
- Existing Library, categories, downloads, progress and installed app package are not deleted. If Android rejects the install, the current app remains installed.
- Test with an owner-approved reachable feed and two real signed APK version codes before claiming fully operational notification.

### Maintained build workflow
The native release workflow `.github/workflows/native-manga-apk.yml` generates metadata from `native_manga/selura_updater/write_update_feed.py` after the signed APK has been verified and published, then commits only `updates/latest.json` to the `gh-pages` branch when the versionCode increases.
