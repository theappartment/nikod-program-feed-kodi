import re
import os
import ssl
import sys
import socket

try:
    import urllib.error as url_error
    import urllib.request as url_request
    import urllib.parse as url_parse
    import urllib.parse as url_encode
except ImportError:
    import urllib as url_encode
    import urlparse as url_parse
    import urllib2 as url_request
    import urllib2 as url_error

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

try:
    TimeoutError
except NameError:
    TimeoutError = socket.timeout


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DEFAULT_FEED_URL = "https://www.sportsonline.vc/prog.txt"
DEFAULT_DIRECT_STREAM_URL = "https://v4.sportssonline.click/channels/hd/hd8.php"
DEFAULT_DIRECT_STREAM_TITLE = "Canale diretto"


def setting(addon, key, fallback=""):
    value = addon.getSetting(key)
    return value if value is not None and value != "" else fallback


def first_setting(addon, keys, fallback=""):
    for key in keys:
        value = setting(addon, key)
        if value:
            return value
    return fallback


def bool_setting(addon, keys, fallback=True):
    value = first_setting(addon, keys, "true" if fallback else "false")
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def normalize_url(value):
    url = (value or "").replace("\\/", "/").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url

    parsed = url_parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return url


def verified_ssl_context():
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if cafile and os.path.exists(cafile):
        return ssl.create_default_context(cafile=cafile)
    if hasattr(ssl, "create_default_context"):
        return ssl.create_default_context()
    return None


def is_ssl_verify_error(exc):
    reason = getattr(exc, "reason", exc)
    verify_error = getattr(ssl, "SSLCertVerificationError", None)
    if verify_error is not None and (isinstance(reason, verify_error) or isinstance(exc, verify_error)):
        return True
    if isinstance(reason, ssl.SSLError) or isinstance(exc, ssl.SSLError):
        return True
    return "ssl" in str(reason).lower() or "certificate" in str(reason).lower()


def unverified_ssl_context():
    if hasattr(ssl, "_create_unverified_context"):
        return ssl._create_unverified_context()
    return None


def request_for(url, user_agent, method=None, extra_headers=None):
    headers = {"User-Agent": user_agent}
    if extra_headers:
        headers.update(extra_headers)
    request = url_request.Request(url, headers=headers)
    if method and hasattr(request, "get_method"):
        request.get_method = lambda: method
    return request


def fetch_text(url, user_agent, timeout, ssl_context=None, extra_headers=None):
    request = request_for(url, user_agent, extra_headers=extra_headers)
    response = urlopen(request, timeout=timeout, context=ssl_context)
    try:
        data = response.read()
    finally:
        response.close()
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def www_variant(url):
    parsed = url_parse.urlparse(url)
    host = parsed.hostname or ""
    if not host or host.startswith("www."):
        return ""

    netloc = "www." + host
    if parsed.port:
        netloc += ":{0}".format(parsed.port)
    return url_parse.urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


def swap_scheme(url):
    parsed = url_parse.urlparse(url)
    if parsed.scheme == "https":
        scheme = "http"
    elif parsed.scheme == "http":
        scheme = "https"
    else:
        return ""
    return url_parse.urlunparse(
        (scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


def candidate_feed_urls(url):
    candidates = []
    for candidate in (url, www_variant(url), swap_scheme(url), www_variant(swap_scheme(url))):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def should_try_next_feed_url(exc):
    if isinstance(exc, url_error.HTTPError):
        return exc.code in (403, 404)
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, socket.gaierror)


def fetch_text_with_dns_fallback(url, user_agent, timeout):
    context = verified_ssl_context()
    last_error = None
    for candidate in candidate_feed_urls(url):
        try:
            if candidate != url:
                xbmc.log("Nikod Program Feed URL fallback: {0}".format(candidate))
            return fetch_text(candidate, user_agent, timeout, context)
        except url_error.URLError as exc:
            last_error = exc
            if is_ssl_verify_error(exc):
                xbmc.log(
                    "Nikod Program Feed SSL verification fallback for feed host: {0}".format(
                        url_parse.urlparse(candidate).hostname or candidate
                    )
                )
                try:
                    return fetch_text(candidate, user_agent, timeout, unverified_ssl_context())
                except url_error.URLError as fallback_exc:
                    last_error = fallback_exc
                    if should_try_next_feed_url(fallback_exc) or is_ssl_verify_error(fallback_exc):
                        continue
                    raise
            if should_try_next_feed_url(exc):
                continue
            raise

    if last_error:
        raise last_error
    raise url_error.URLError("No candidate feed URLs were available")


def fetch_page_text(url, user_agent, timeout, referer=""):
    headers = {}
    if referer:
        headers["Referer"] = referer
    try:
        return fetch_text(url, user_agent, timeout, verified_ssl_context(), headers)
    except url_error.URLError as exc:
        if is_ssl_verify_error(exc):
            return fetch_text(url, user_agent, timeout, unverified_ssl_context(), headers)
        raise


def urlopen(request, timeout, context=None):
    if context is not None:
        try:
            return url_request.urlopen(request, timeout=timeout, context=context)
        except TypeError:
            pass
    return url_request.urlopen(request, timeout=timeout)


def media_content_type(url, user_agent, timeout):
    lower = url.lower()
    if ".m3u8" in lower:
        return "application/vnd.apple.mpegurl"
    if any(token in lower for token in (".mp4", ".mov", ".m4v")):
        return "video/mp4"
    if ".mpd" in lower:
        return "application/dash+xml"

    request = request_for(url, user_agent, method="HEAD")
    context = verified_ssl_context()
    try:
        response = urlopen(request, timeout=timeout, context=context)
        try:
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        finally:
            response.close()
    except url_error.URLError as exc:
        if is_ssl_verify_error(exc):
            xbmc.log("Nikod Program Feed media probe SSL verification fallback: {0}".format(url))
            try:
                response = urlopen(request, timeout=timeout, context=ssl._create_unverified_context())
                try:
                    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                finally:
                    response.close()
            except Exception as fallback_exc:
                xbmc.log("Nikod Program Feed media probe failed: {0}".format(fallback_exc))
                return ""
        else:
            xbmc.log("Nikod Program Feed media probe failed: {0}".format(exc))
            return ""
    except Exception as exc:
        xbmc.log("Nikod Program Feed media probe failed: {0}".format(exc))
        return ""

    xbmc.log("Nikod Program Feed media probe content-type: {0}".format(content_type or "unknown"))
    return content_type


def is_direct_media_url(url):
    lower = url.lower()
    return any(token in lower for token in (".m3u8", ".mp4", ".m4v", ".mov", ".mpd"))


def absolute_url(base_url, value):
    value = (value or "").replace("\\/", "/").strip()
    if not value:
        return ""
    return url_parse.urljoin(base_url, value)


def extract_direct_media_url(html, base_url):
    patterns = [
        r"""['"]([^'"]+?\.m3u8[^'"]*)['"]""",
        r"""['"]([^'"]+?\.mp4[^'"]*)['"]""",
        r"""['"]([^'"]+?\.m4v[^'"]*)['"]""",
        r"""['"]([^'"]+?\.mpd[^'"]*)['"]""",
        r"""(?:source|file|url)\s*[:=]\s*['"]([^'"]+)['"]""",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, html, re.IGNORECASE):
            candidate = absolute_url(base_url, match)
            if is_direct_media_url(candidate):
                return candidate
    return ""


def extract_iframe_url(html, base_url):
    match = re.search(r"""<iframe[^>]+src=['"]([^'"]+)['"]""", html, re.IGNORECASE)
    if match:
        return absolute_url(base_url, match.group(1))
    return ""


def resolve_media_url(url, user_agent, timeout):
    if is_direct_media_url(url):
        return url

    try:
        html = fetch_page_text(url, user_agent, timeout)
    except Exception as exc:
        xbmc.log("Nikod Program Feed page resolver failed: {0}".format(exc))
        return ""

    direct = extract_direct_media_url(html, url)
    if direct:
        xbmc.log("Nikod Program Feed resolved direct media URL from page")
        return direct

    iframe = extract_iframe_url(html, url)
    if iframe:
        xbmc.log("Nikod Program Feed found iframe player: {0}".format(iframe))
        try:
            iframe_html = fetch_page_text(iframe, user_agent, timeout, referer=url)
            direct = extract_direct_media_url(iframe_html, iframe)
            if direct:
                xbmc.log("Nikod Program Feed resolved direct media URL from iframe")
                return direct + "|Referer={0}&User-Agent={1}".format(
                    url_encode.quote(iframe, safe=""),
                    url_encode.quote(user_agent, safe=""),
                )
        except Exception as exc:
            xbmc.log("Nikod Program Feed iframe resolver failed: {0}".format(exc))

    return ""


def describe_url_error(url, exc):
    host = url_parse.urlparse(url).hostname or ""
    if isinstance(exc, url_error.HTTPError):
        return "HTTP error {0} loading feed: {1}".format(exc.code, host or url)
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, socket.gaierror):
        return "Host not reachable: {0}. DNS lookup failed from the app runtime.".format(host or url)
    if isinstance(reason, TimeoutError):
        return "Timed out loading feed: {0}".format(host or url)
    return str(exc)


def clean_markup(value):
    value = re.sub(r"\[[^\]]+\]", "", value)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


WEEKDAYS = {
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
}


def normalized_language(value):
    value = clean_markup(value).upper()
    value = value.replace("&", ",")
    parts = [part.strip().title() for part in value.split(",") if part.strip()]
    return " / ".join(parts) if parts else "Other"


def channel_code_from_url(url):
    parsed = url_parse.urlparse(url)
    match = re.search(r"/([^/]+)\.php$", parsed.path, re.IGNORECASE)
    return match.group(1).upper() if match else ""


def parse_feed(text):
    current_day = "Unscheduled"
    channel_languages = {}
    programs = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        raw = clean_markup(line)
        if not raw or raw.startswith("#"):
            continue

        upper = raw.upper()
        if upper in WEEKDAYS:
            current_day = upper.title()
            continue

        channel_match = re.match(r"^([A-Z]{2,4}\d+)\s+(.+)$", raw, re.IGNORECASE)
        if channel_match and "://" not in raw:
            channel_languages[channel_match.group(1).upper()] = normalized_language(channel_match.group(2))
            continue

        program = parse_program_line(raw, len(programs) + 1, current_day, channel_languages)
        if program:
            programs.append(program)

    return programs


def parse_program_line(line, index, day, channel_languages):
    raw = clean_markup(line)
    if not raw or raw.startswith("#"):
        return None

    match = re.match(r"^(\d{1,2}[:.]\d{2})\s+(.+?)(?:\s*[|]\s*(https?://\S+))?$", raw)
    if match:
        time_text = match.group(1).replace(".", ":")
        title = match.group(2).strip()
        stream_url = (match.group(3) or "").strip()
    else:
        parts = [part.strip() for part in re.split(r"\s*[|;\t]\s*", raw) if part.strip()]
        if len(parts) >= 2 and re.match(r"^\d{1,2}[:.]\d{2}$", parts[0]):
            time_text = parts[0].replace(".", ":")
            title = parts[1]
            stream_url = next((part for part in parts[2:] if part.startswith(("http://", "https://"))), "")
        else:
            return None

    channel = channel_code_from_url(stream_url)
    language = channel_languages.get(channel, "Other")
    detail_parts = []
    if day:
        detail_parts.append(day)
    if channel:
        detail_parts.append(channel)
    if language:
        detail_parts.append(language)
    if stream_url:
        detail_parts.append(stream_url)

    label = " - ".join([part for part in (time_text, title) if part])
    return {
        "index": index,
        "label": label,
        "title": title or label,
        "time": time_text,
        "day": day,
        "channel": channel,
        "language": language,
        "stream_url": stream_url,
        "detail": "\n".join(detail_parts),
        "raw": raw,
    }


def add_notice(handle, title, plot):
    item = xbmcgui.ListItem(label=title)
    item.setInfo("video", {"title": title, "plot": plot, "genre": "Program Feed"})
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(handle, sys.argv[0], item, isFolder=False)


def notify(title, message):
    try:
        xbmcgui.Dialog().notification(title, message, xbmcgui.NOTIFICATION_INFO, 6000)
    except Exception:
        xbmc.log("{0}: {1}".format(title, message))


def show_web_player_url(url, android_hint=False):
    message = url
    if android_hint:
        message = (
            "Chromecast / Google TV needs a browser or web player app installed to open this page.\n\n"
            "If Android says no app can open it, install a browser such as TV Bro or Downloader, "
            "or open this URL on another device:\n\n{0}"
        ).format(url)

    try:
        if hasattr(xbmcgui.Dialog(), "textviewer"):
            xbmcgui.Dialog().textviewer("Nikod Program Feed", message)
        else:
            xbmcgui.Dialog().ok("Nikod Program Feed", message)
    except Exception:
        xbmc.log("Nikod Program Feed web player URL: {0}".format(url))


def platform_builtin_url(url):
    safe_url = (url or "").replace('"', "%22")
    if xbmc.getCondVisibility("System.Platform.Android"):
        return "StartAndroidActivity(,android.intent.action.VIEW,,{0})".format(safe_url)
    if xbmc.getCondVisibility("System.Platform.OSX"):
        return 'System.Exec(open "{0}")'.format(safe_url)
    if xbmc.getCondVisibility("System.Platform.Windows"):
        return 'System.Exec(rundll32 url.dll,FileProtocolHandler "{0}")'.format(safe_url)
    if xbmc.getCondVisibility("System.Platform.Linux"):
        return 'System.Exec(xdg-open "{0}")'.format(safe_url)
    return ""


def open_external_url(url):
    builtin = platform_builtin_url(url)
    if builtin:
        xbmc.log("Nikod Program Feed opening external web player: {0}".format(url))
        if xbmc.getCondVisibility("System.Platform.Android"):
            show_web_player_url(url, android_hint=True)
        xbmc.executebuiltin(builtin)
        return True

    show_web_player_url(url)
    xbmc.log("Nikod Program Feed external web player unsupported on this Kodi platform: {0}".format(url))
    return False


def plugin_url(params):
    query = url_encode.urlencode(params)
    return sys.argv[0] + ("?" + query if query else "")


def query_params():
    if len(sys.argv) < 3:
        return {}
    query = sys.argv[2] or ""
    if query.startswith("?"):
        query = query[1:]
    return {key: values[0] for key, values in url_parse.parse_qs(query).items()}


def selected_program_index(params):
    value = params.get("program", "") or params.get("play", "")
    try:
        return int(value)
    except ValueError:
        return None


def selected_play_index(params):
    value = params.get("play", "")
    try:
        return int(value)
    except ValueError:
        return None


def add_folder(handle, label, params, plot=""):
    item = xbmcgui.ListItem(label=label)
    item.setInfo("video", {"title": label, "plot": plot, "genre": "Program Feed"})
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(handle, plugin_url(params), item, isFolder=True)


def add_program(handle, program):
    item = xbmcgui.ListItem(label=program["label"])
    item.setInfo(
        "video",
        {
            "title": program["title"],
            "plot": program["detail"] or program["raw"],
            "genre": "Program Feed",
            "aired": program["time"],
            "studio": program["channel"],
        },
    )
    item.setProperty("IsPlayable", "true" if program["stream_url"] else "false")
    url = plugin_url({"play": program["index"]}) if program["stream_url"] else plugin_url({"program": program["index"]})
    xbmcplugin.addDirectoryItem(handle, url, item, isFolder=False)


def add_direct_stream(handle, title, direct_url):
    item = xbmcgui.ListItem(label=title)
    item.setInfo(
        "video",
        {
            "title": title,
            "plot": direct_url,
            "genre": "Program Feed",
        },
    )
    item.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(handle, plugin_url({"direct": "1"}), item, isFolder=False)


def handle_unresolved_web_player(handle, title, page_url, external_open_enabled):
    if external_open_enabled and page_url:
        if open_external_url(page_url):
            notify("Nikod Program Feed", "Opening web player externally.")
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem(label=title))
            return
        notify("Nikod Program Feed", "External web player is not supported here.")
    else:
        notify("Nikod Program Feed", "No direct video stream found for Kodi.")

    add_notice(
        handle,
        "No direct video stream found",
        "This URL opens a web player page, but no direct video stream was found for Kodi.",
    )
    xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem(label=title))


def resolve_direct_stream(handle, title, direct_url, user_agent, timeout, external_open_enabled):
    if not direct_url:
        add_notice(handle, "Nothing to play", "Set Direct channel URL in addon settings.")
        xbmcplugin.endOfDirectory(handle)
        return

    playable_url = resolve_media_url(direct_url, user_agent, timeout)
    if not playable_url:
        handle_unresolved_web_player(handle, title, direct_url, external_open_enabled)
        return

    mime_type = media_content_type(playable_url.split("|", 1)[0], user_agent, timeout)
    item = xbmcgui.ListItem(label=title, path=playable_url)
    item.setPath(playable_url)
    if mime_type:
        item.setMimeType(mime_type)
    item.setProperty("IsPlayable", "true")
    item.setInfo(
        "video",
        {
            "title": title,
            "plot": playable_url,
            "genre": "Program Feed",
        },
    )
    xbmcplugin.setResolvedUrl(handle, True, item)


def resolve_program(handle, program, user_agent, timeout, external_open_enabled):
    if not program or not program["stream_url"]:
        add_notice(handle, "Nothing to play", "This program row does not include a playable URL.")
        xbmcplugin.endOfDirectory(handle)
        return

    playable_url = resolve_media_url(program["stream_url"], user_agent, timeout)
    if not playable_url:
        handle_unresolved_web_player(handle, program["title"], program["stream_url"], external_open_enabled)
        return

    mime_type = media_content_type(playable_url.split("|", 1)[0], user_agent, timeout)

    item = xbmcgui.ListItem(label=program["title"], path=playable_url)
    item.setPath(playable_url)
    if mime_type:
        item.setMimeType(mime_type)
    item.setProperty("IsPlayable", "true")
    item.setInfo(
        "video",
        {
            "title": program["title"],
            "plot": program["detail"] or program["raw"],
            "genre": "Program Feed",
            "aired": program["time"],
            "studio": program["channel"],
        },
    )
    xbmcplugin.setResolvedUrl(handle, True, item)


def main():
    addon = xbmcaddon.Addon()
    handle = int(sys.argv[1])
    feed_url = normalize_url(first_setting(addon, ("feed_url", "feed.url"), DEFAULT_FEED_URL))
    direct_url = normalize_url(first_setting(addon, ("direct_stream_url", "direct.url", "direct_url"), DEFAULT_DIRECT_STREAM_URL))
    direct_title = first_setting(addon, ("direct_stream_title", "direct.title"), DEFAULT_DIRECT_STREAM_TITLE)
    user_agent = first_setting(addon, ("feed_user_agent", "feed.user_agent"), DEFAULT_USER_AGENT)
    external_open_enabled = bool_setting(addon, ("external_open_enabled", "external.open_enabled"), True)
    params = query_params()

    try:
        timeout = max(1, int(first_setting(addon, ("feed_timeout", "feed.timeout"), "12")))
    except ValueError:
        timeout = 12

    xbmc.log("Nikod Program Feed starting")
    xbmc.log("Nikod Program Feed URL: {0}".format(feed_url or "<empty>"))
    xbmc.log("Nikod Program Feed direct URL: {0}".format(direct_url or "<empty>"))
    xbmc.log("Nikod Program Feed external web player fallback: {0}".format(external_open_enabled))
    xbmcplugin.setContent(handle, "videos")

    if params.get("direct") == "1":
        resolve_direct_stream(handle, direct_title, direct_url, user_agent, timeout, external_open_enabled)
        return

    if not feed_url and direct_url:
        add_direct_stream(handle, direct_title, direct_url)
        xbmcplugin.endOfDirectory(handle)
        return

    if not feed_url:
        add_notice(
            handle,
            "Configure a program feed URL",
            "Open addon settings and set Program feed URL or Direct channel URL.",
        )
        xbmcplugin.endOfDirectory(handle)
        return

    try:
        text = fetch_text_with_dns_fallback(feed_url, user_agent, timeout)
    except (url_error.URLError, TimeoutError, OSError) as exc:
        add_notice(handle, "Could not load program feed", describe_url_error(feed_url, exc))
        xbmcplugin.endOfDirectory(handle)
        return

    programs = parse_feed(text)

    if not programs:
        add_notice(handle, "No programs found", "The feed loaded, but no supported text rows were found.")
        xbmcplugin.endOfDirectory(handle)
        return

    play_index = selected_play_index(params)
    if play_index is not None:
        resolve_program(
            handle,
            next((item for item in programs if item["index"] == play_index), None),
            user_agent,
            timeout,
            external_open_enabled,
        )
        return

    selected_index = selected_program_index(params)
    if selected_index is not None:
        program = next((item for item in programs if item["index"] == selected_index), None)
        if not program:
            add_notice(handle, "Program not found", "The selected program is no longer present in the feed.")
            xbmcplugin.endOfDirectory(handle)
            return

        item = xbmcgui.ListItem(label=program["title"])
        item.setInfo(
            "video",
            {
                "title": program["title"],
                "plot": program["detail"] or program["raw"],
                "genre": "Program Feed",
                "aired": program["time"],
            },
        )
        item.setProperty("IsPlayable", "false")
        xbmcplugin.addDirectoryItem(handle, sys.argv[0], item, isFolder=False)
        xbmcplugin.endOfDirectory(handle)
        return

    selected_day = params.get("day", "")
    selected_language = params.get("language", "")

    if not selected_day:
        if direct_url:
            add_direct_stream(handle, direct_title, direct_url)
        for day in sorted({program["day"] for program in programs}):
            count = sum(1 for program in programs if program["day"] == day)
            add_folder(handle, day, {"day": day}, "{0} programs".format(count))
        xbmcplugin.endOfDirectory(handle)
        return

    day_programs = [program for program in programs if program["day"] == selected_day]
    if not selected_language:
        languages = sorted({program["language"] for program in day_programs})
        add_folder(handle, "All languages", {"day": selected_day, "language": "__all__"}, "{0} programs".format(len(day_programs)))
        for language in languages:
            count = sum(1 for program in day_programs if program["language"] == language)
            add_folder(handle, language, {"day": selected_day, "language": language}, "{0} programs".format(count))
        xbmcplugin.endOfDirectory(handle)
        return

    visible_programs = day_programs
    if selected_language != "__all__":
        visible_programs = [program for program in day_programs if program["language"] == selected_language]

    for program in visible_programs:
        add_program(handle, program)

    xbmcplugin.endOfDirectory(handle)


if __name__ == "__main__":
    main()
