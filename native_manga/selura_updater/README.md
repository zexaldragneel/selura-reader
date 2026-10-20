# Selura Manga in-app update notification

Selura now has a first-party Android startup update prompt. It is independent of Mihon's default updater, which remains disabled for the Selura build.

### Behavior
- On a fresh app launch, attempt an HTTPS GET to `https://raw.githubusercontent.com/zexaldragneel/selura-reader/gh-pages/updates/latest.json`.
- Silently continue offline if the feed is missing/unreachable, if content is invalid, or if versionCode is not newer than installed `com.selura.manga`.
- Show a themed Material update dialog with build name, release notes, **View update** and **Later**.
- View update opens an allowlisted GitHub release page in the phone browser so the user can download and install the update with Android's normal installer. The app never silently replaces itself or needs installation permissions.
- The app never contains GitHub tokens, secrets or signing material.

### Privacy and deployment blocker
**The repository `zexaldragneel/selura-reader` is public.** The update feed lives in a `gh-pages` branch inside the same repository and is served at a public HTTPS raw-content URL. The app never contains a token.

The owner has chosen a public repository and approved version metadata. The update prompt only activates once the `gh-pages` branch contains a newer signed build's metadata and the URL is reachable.

The verified native APK workflow maintains the public feed in the `gh-pages` branch, without requiring GitHub Pages configuration. The JSON contains only:
`schemaVersion`, `applicationId`, `versionCode`, `versionName`, `notes`, `releaseUrl`, and signed APK `sha256`. GitHub Actions generates it only *after* APK build and signing verification and release publication. It archives `selura-update-feed-private` as an Actions artifact before atomically publishing JSON to the same public repository's `gh-pages` branch. It never commits decrypted signing material.

The release is public; when a user taps View update, the phone browser opens the GitHub release page without requiring sign-in.

### Test cases
- Feed says versionCode equal to or below installed → no popup.
- Feed says newer versionCode with correct applicationId, 64-digit SHA-256 and release URL under `github.com/zexaldragneel/selura-reader/releases/tag/<tag>` → show dialog.
- Invalid repo, HTTP error, wrong app ID, malformed JSON, bad checksum, timeout, offline → no crash/no popup.
- Later dismisses for current launch; reopening can check again.
- View update opens the browser release page; Android installer and signature checks remain system-controlled.
- Test with an owner-approved reachable feed and two real signed APK version codes before claiming fully operational notification.

### Maintained build workflow
The native release workflow `.github/workflows/native-manga-apk.yml` generates metadata from `native_manga/selura_updater/write_update_feed.py` after the signed APK has been verified and published, then commits only `updates/latest.json` to the `gh-pages` branch when the versionCode increases.
