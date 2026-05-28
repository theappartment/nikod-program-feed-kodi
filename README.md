# Nikod Program Feed for Kodi

Standalone Kodi addon distribution for **Nikod Program Feed**.

The addon reads an authorized plain-text schedule feed and exposes days, languages, events, and optional direct channel URLs as Kodi video items.

## Install

1. Download the repository ZIP:
   `https://github.com/theappartment/nikod-program-feed-kodi/releases/download/v0.1.10/repository.nikod.programfeed-0.1.0.zip`
2. In Kodi, open `Settings > Add-ons > Install from zip file`.
3. Select the downloaded ZIP.
4. Open `Install from repository > Nikod Program Feed Repository > Video add-ons`.
5. Install `Nikod Program Feed`.

## Settings

- `Program feed URL`: authorized plain-text program feed.
- `Direct channel URL`: optional direct URL, for example a channel page.
- `Direct channel title`: label for the direct URL item.
- `User-Agent`: request user agent.
- `Timeout seconds`: network timeout.

## Repository Layout

- `plugin.video.nikod.programfeed/`: Kodi video plugin source.
- `repository.nikod.programfeed/`: Kodi repository addon.
- `zips/`: installable versioned ZIPs.
- `addons.xml`: Kodi repository index.
- `addons.xml.md5`: Kodi repository checksum.

## Release Assets

GitHub Releases contain the user-facing install ZIPs:

- `repository.nikod.programfeed-0.1.0.zip`: install this first in Kodi.
- `plugin.video.nikod.programfeed-0.1.10.zip`: direct addon package, mainly for debugging/manual installs.

## Build

Run:

```sh
python3 scripts/build_repository.py
```

The script regenerates `addons.xml`, `addons.xml.md5`, and versioned ZIPs.

## Notes

This repository does not provide or endorse any media source. Users must configure authorized feed URLs and are responsible for the content they access.
