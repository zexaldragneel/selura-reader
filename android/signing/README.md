# Selura Android APK signing

Selura must use **the same Android signing certificate for every installable APK**. Its earlier GitHub Actions builds used a new ephemeral debug-signing keystore on fresh runners, so upgrading one downloaded APK over another can fail even though each APK installs after uninstalling the old app.

## One-time setup from an Android phone

After the signing workflow PR is merged:

1. Open the Selura repository in a mobile browser (enable **Desktop site** if GitHub hides repository Settings).
2. Open **Settings → Secrets and variables → Actions → New repository secret**.
3. Set the name to **`SELURA_SIGNING_PASSWORD`**. Enter a newly generated **random password of at least 24 characters**. Store a copy securely in your password manager. **Never paste it into ChatGPT, an issue, PR, or a commit.**
4. Open **Actions → Bootstrap Selura Signing Key → Run workflow**, selecting the **main** branch. **Run it only once.**
5. This workflow generates a private, long-lived Android release-signing keystore on a GitHub runner, encrypts it with GPG AES-256 using the repository secret, and commits **only its encrypted ASCII-armored form** to `android/signing/selura-release.jks.asc`. The plaintext key is never committed or uploaded as an artifact.
6. The bootstrap then starts the normal **Build Android APK** workflow automatically. Wait for **Build signed release APK**, **Verify APK certificate, package and version code**, and **Publish direct APK** to pass.
7. Download `selura.apk` from the **new** GitHub Releases entry. New installable APKs are **release-signed**, not `selura-debug.apk`.

For every subsequent APK, the workflow decrypts **the same permanent signing key** temporarily in the trusted GitHub Actions runner and increments Android `versionCode` from the workflow run number. CI verifies the APK signature and the package ID `com.selura.reader` before publishing.

**Do not change or delete the signing password or encrypted keystore.** Losing either makes it impossible to sign further updates with the same identity. Keep a secure backup of the password; back up the encrypted keystore file separately if desired. The passphrase is needed to decrypt the encrypted file.

## Important: the existing debug APK

The already installed `com.selura.reader` debug APK was signed with a different, ephemeral certificate. Android **will not** install a newly signed release APK over an app signed with an incompatible certificate. The permanent signer fixes future updates **after the first signed installation**, but **does not magically migrate data from the earlier debug install**.

**Do not uninstall your current working Selura until your books and important reading data are preserved.** Selura stores imported books in app-private storage and bookmarks/progress in app-private preferences; uninstalling can delete them. The current app has no implemented export/restore function, and Google/Android backup restoration should not be assumed. You may need to re-import your original EPUB/PDF files after the one-time transition. If your existing bookmarks or reading positions are important, wait before switching; there is no verified lossless migration path yet.

## Security and development notes

- The repository may be public. **Never commit** `.jks`, `.keystore`, private keys, or plaintext passwords.
- `android/signing/selura-release.jks.asc` is encrypted, not a plaintext key. Its security depends on the strong repository secret.
- The app's package name must remain `com.selura.reader`. Changing package name or signing certificate again would break normal updates.
- Pull requests from forks never receive repository secrets. Only trust pull-request code from the repository's own branches; Gradle builds with signing credentials should not run unreviewed contributor code.
- The bootstrap workflow must run on **main** and refuses to generate a second key once the encrypted key exists.
- Debug APK releases published before this change remain on GitHub but are **not** compatible upgrade artifacts. Future `selura.apk` releases use consistent signing.
- During setup, CI intentionally **fails closed** after analysis/tests if the secret or encrypted key has not been configured. It does not publish another misleading ephemeral-signed APK.
