# Selura coding-agent instructions

Selura is a premium, offline-first Android eBook and manga reader written in Flutter/Dart. The Android app must remain usable without a desktop computer; GitHub Actions is the build system.

## Mandatory session start

1. Read `PROJECT_CONTEXT.md` and `PROGRESS.md` before changing code.
2. Inspect the current source and open pull requests/branches relevant to the assigned task. Preserve working EPUB/PDF behavior.
3. Inspect the latest GitHub Actions result before deciding whether a build problem is still current.

## Repository boundary

- Work only in `zexaldragneel/selura-reader`.
- Never modify any other repository or deploy to any VPS/server.
- Do not merge your own pull request. Leave review/merge to the repository owner.

## Product requirements

- Flutter/Dart, Android-first, offline-first.
- Required Android application ID: `com.selura.reader`.
- Core formats: EPUB and PDF; CBZ manga support is planned next.
- Priorities: reliable local import/storage, reading progress, bookmarks, typography, highlights/annotations, polished bookshelf and reader UI, manga reading modes.
- Use original UI and maintained/licensed open-source dependencies only.
- Keep light/dark themes and a premium Material 3 Android experience.

## Engineering rules

- Make complete functional changes rather than mockups.
- Prefer small, reviewable commits and feature branches.
- Do not overwrite working functionality unnecessarily.
- Before adding or upgrading a dependency, check compatibility with the Flutter stable toolchain used by Actions.
- Run formatting, static analysis, tests when available, and an Android APK build for code changes.
- Treat GitHub Actions as the source of truth for cloud build verification.
- Never claim installation/runtime behavior is verified unless it was actually tested on an Android device by the user.
- Do not weaken security checks, disable tests, or hide build errors to get a green workflow.

## Progress tracking

After each meaningful milestone, update `PROGRESS.md` with:
- what changed,
- commit(s),
- exact build/test result,
- remaining blockers,
- next recommended step.

If a task is blocked by device-only verification, credentials, permissions, or a decision that cannot safely be inferred, stop at a clean reviewable state and document the blocker instead of guessing.
