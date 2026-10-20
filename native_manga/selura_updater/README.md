# Selura Manga in-app update notification

Selura now has a first-party Android startup update prompt. It is independent of Mihon's default updater, which remains disabled for the Selura build.

### Behavior
- On a fresh app launch, attempt an HTTPS GET to `https://raw.githubusercontent.com/zexaldragneel/selura-updates/main/latest.json`.
- Silently continue offline if the feed is missing/unreachable, if content is invalid, or if versionCode is not newer than installed `com.selura.manga`.
- Show a themed Material update dialog with build name, release notes, **View update** and **Later**.
- View update opens an allowlisted GitHub release page in the phone browser so the user can download and install the update with Android's normal installer. The app never silently replaces itself or needs installation permissions.
- The app never contains GitHub tokens, secrets or signing material.

### Privacy and deployment blocker
**The repository `zexaldragneel/selura-reader` is private.** GitHub Releases REST and raw-content endpoints require GitHub authentication for private repositories. Putting credentials in the APK is unsafe, and app sandbox cookies cannot simply use the browser's GitHub sign-in.

The public feed is intentionally **not deployed yet**. This is an explicit owner-choice privacy boundary. The update prompt is compiled, but it will not trigger until the owner approves publication of the small update JSON feed and public static hosting is operational. Neither the repository nor APK releases are made public by these changes.

After owner authorization, create a minimal publicly readable feed at the URL above via GitHub Pages (if their plan permits Pages for this private repo), or another owner-authorized static endpoint. The JSON contains only:
`schemaVersion`, `applicationId`, `versionCode`, `versionName`, `notes`, `releaseUrl`, and signed APK `sha256`. GitHub Actions generates it only *after* APK build and signing verification and release publication. It currently archives `selura-update-feed-private` as a nonpublic workflow artifact. It does not expose the source tree or certificate.

The release itself stays private; when a user taps View update, their signed-in mobile browser opens the GitHub release page. To serve unauthenticated users eventually, the owner must explicitly authorize publishing downloadable APK assets too, or sign-in will still be required.

### Test cases
- Feed says versionCode equal to or below installed → no popup.
- Feed says newer versionCode with correct applicationId, 64-digit SHA-256 and release URL under `github.com/zexaldragneel/selura-reader/releases/tag/<tag>` → show dialog.
- Invalid repo, HTTP error, wrong app ID, malformed JSON, bad checksum, timeout, offline → no crash/no popup.
- Later dismisses for current launch; reopening can check again.
- View update opens the browser release page; Android installer and signature checks remain system-controlled.
- Test with an owner-approved reachable feed and two real signed APK version codes before claiming fully operational notification.

### Maintained build workflow
The native release workflow `.github/workflows/native-manga-apk.yml` generates metadata from `native_manga/selura_updater/write_update_feed.py` after the verified APK has been published. It stores the JSON privately; external deployment is disabled pending approval.
