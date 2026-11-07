# Integrated Seiryn Obsidian UI

Select **Seiryn Obsidian** under Settings → Appearance → Library theme.
The added Home tab uses the existing library/history flows and reader intent.
Home history is deduplicated by manga; recent titles use chapter-fetch timestamps;
the unread shelf contains real library titles without reading history. These are
Home also ranks unread titles from the local library by shared genres with the last-read series. Home resumes the historical chapter
through GetNextChapters with onlyUnread=false, preserving partial page progress.

The Obsidian Library uses the selected category's existing filtered manga rows,
with native long-press selection, global search, and continue-reading callbacks.
Its offline and bookmark counts and progress come from existing manga/chapter
state. Home's optional recommendation shelf ranks unread library titles by
shared genre names with the most recently read library title; it performs no
source search and does not invent missing genres.

The patch runs last, after premium_library_v2.py. It validates all replacements
before writing. It changes presentation files and adds one read-only ViewModel;
database schema, backups, source identity, downloads and signing stay with the
existing engine. Other appearance themes retain their existing screen layouts.

## Device acceptance (not covered by APK compilation)

- Upgrade the existing installation; confirm library counts, category membership,
  history, bookmarks, offline downloads and extension sources remain present.
- Select Obsidian, restart, and navigate Home/Library/Updates/Browse/More.
  Check Home history and downloads shortcuts; Back returns to Home.
- Resume a partially read chapter and confirm the saved page. Complete a chapter,
  return Home and confirm Continue advances. Test a finished series and a removed
  source: the app must give feedback instead of losing state or crashing.
- Search Library, clear search, change categories, sort/filter, long-press/select,
  bookmark/mark read/download. Clear filters to distinguish filtering from missing data.
- Open Details, cover dialog, author/source search, description/tags, notes,
  category/track actions and chapter sort/filter; confirm live unread, offline,
  and bookmark counts; test chapter swipe and selection. If an item's extension
  is unavailable, use **Find source**, review the candidate in Mihon's migration
  flow, and confirm only the correct match.
- Read online and downloaded chapters in LTR, RTL, webtoon and landscape modes.
  Check chapter skip, slider, page progress bar, crop, orientation, bookmarks
  and immersive hide/show.
- With **Download only over Wi-Fi** enabled, leave queued work waiting without
  Wi-Fi, reconnect to Wi-Fi, and confirm the existing queue resumes. Confirm
  manual Pause and Clear still prevent later automatic resumption.
- Test large fonts, small phones and tablet rails; switch to another theme and back.

Automated checks establish source integration, compilation and artifact identity.
They do not establish visual parity with the approved mockup or device behavior.

