# Nikod Program Feed for Kodi

Standalone Kodi addon distribution for **Nikod Program Feed**.

The addon reads an authorized plain-text schedule feed and exposes days, languages, events, and optional direct channel URLs as Kodi video items.

## Install From Kodi File Source

This mirrors the common Kodi repository installer flow.

1. In Kodi, open `Settings > File manager > Add source`.
2. Add:
   `https://theappartment.github.io/nikod-pf/`
3. Name it `Nikod Program Feed repo`.
4. Open `Add-ons > Install from zip file > Nikod Program Feed repo`.
5. Select `NikodProgramFeed-installer.zip` for Kodi 19/20/21.
6. Open `Add-ons > Video add-ons > Nikod Program Feed`.

For Kodi 18/Leia, select `NikodProgramFeed-legacy-kodi18.zip` instead.

Optional: install `repository.nikod.programfeed-0.1.0.zip` from the same source to enable repository-style updates.

## Direct Install ZIP

1. Download the repository ZIP:
   `https://github.com/theappartment/nikod-pf/releases/download/v0.1.10/repository.nikod.programfeed-0.1.0.zip`
2. In Kodi, open `Settings > Add-ons > Install from zip file`.
3. Select the downloaded ZIP.
4. Open `Install from repository > Nikod Program Feed Repository > Video add-ons`.
5. Install `Nikod Program Feed`.

## Settings

- `Program feed URL`: authorized plain-text program feed. A default feed is preconfigured and can be edited.
- `Direct channel URL`: optional direct URL, for example a channel page. A default direct channel is preconfigured and can be edited.
- `Direct channel title`: label for the direct URL item.
- `User-Agent`: request user agent.
- `Timeout seconds`: network timeout.
- `Open web player externally when needed`: if Kodi cannot resolve a direct media stream from a web player page, try opening that page with the platform browser/app. Chromecast / Google TV requires a browser app installed for this to work.
- `Open addon when Kodi starts`: opens Nikod Program Feed automatically when Kodi starts.
- `Autostart delay seconds`: delay before opening the addon at Kodi startup.

## Repository Layout

- `plugin.video.nikod.programfeed/`: Kodi video plugin source.
- `repository.nikod.programfeed/`: Kodi repository addon.
- `zips/`: installable versioned ZIPs.
- `docs/`: GitHub Pages file-source installer site.
- `addons.xml`: Kodi repository index.
- `addons.xml.md5`: Kodi repository checksum.

## Release Assets

GitHub Releases contain the user-facing install ZIPs:

- `NikodProgramFeed-installer.zip`: direct install package for the playable video addon.
- `NikodProgramFeed-legacy-kodi18.zip`: legacy package for Kodi 18/Leia Python 2 runtimes.
- `repository.nikod.programfeed-0.1.0.zip`: optional repository package for update/distribution metadata.
- `plugin.video.nikod.programfeed-0.1.20.zip`: direct addon package, mainly for debugging/manual installs.

## Build

Run:

```sh
python3 scripts/build_repository.py
```

The script regenerates `addons.xml`, `addons.xml.md5`, and versioned ZIPs.

## Notes

This repository does not provide or endorse any media source. Users must configure authorized feed URLs and are responsible for the content they access.
