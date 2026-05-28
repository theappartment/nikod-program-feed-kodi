import sys
import time

import xbmc
import xbmcaddon


ADDON_ID = "plugin.video.nikod.programfeed"


def bool_setting(addon, key):
    return addon.getSetting(key).strip().lower() in ("true", "1", "yes", "on")


def int_setting(addon, key, fallback):
    try:
        return max(0, int(addon.getSetting(key)))
    except (TypeError, ValueError):
        return fallback


def main():
    addon = xbmcaddon.Addon(ADDON_ID)
    if not bool_setting(addon, "autostart_enabled"):
        xbmc.log("Nikod Program Feed autostart disabled")
        return

    delay = int_setting(addon, "autostart_delay", 5)
    monitor = xbmc.Monitor()
    xbmc.log("Nikod Program Feed autostart scheduled in {0}s".format(delay))
    if monitor.waitForAbort(delay):
        return

    plugin_url = "plugin://{0}/".format(ADDON_ID)
    xbmc.executebuiltin("ActivateWindow(Videos,{0},return)".format(plugin_url))
    xbmc.log("Nikod Program Feed autostart opened {0}".format(plugin_url))


if __name__ == "__main__":
    main()
