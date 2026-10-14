# radio.py - keeps the radios off unless something explicitly needs them
#
# UIFlow's start-up code can leave Wi-Fi connected (boot option 1 or 2) and may
# start a BLE advertisement before main.py runs.  Both cost battery for nothing,
# so the app calls power_down() at start-up and after every network task.

from boot_log import log


def _state():
    """(wifi_sta_active, wifi_ap_active, ble_active); None where the module is missing."""
    sta = ap = ble = None
    try:
        import network
        sta = bool(network.WLAN(network.STA_IF).active())
        ap = bool(network.WLAN(network.AP_IF).active())
    except Exception:
        pass
    try:
        import bluetooth
        ble = bool(bluetooth.BLE().active())
    except Exception:
        pass
    return (sta, ap, ble)


class RadioManager:
    ble_in_use = False          # a Bluetooth sync is on (screens/ble_*_screen.py): power_down() leaves BLE alone

    def power_down(self, tag=""):
        """Disconnect and switch off Wi-Fi (station + access point) and BLE - BLE not while a sync uses it (the Wi-Fi
        time sync at start-up ends with a power_down(); a Bluetooth session started meanwhile lost its radio)."""
        before = _state()
        try:
            import network
            sta = network.WLAN(network.STA_IF)
            if sta.active():
                try:
                    sta.disconnect()
                except Exception:
                    pass
                sta.active(False)
            ap = network.WLAN(network.AP_IF)
            if ap.active():
                ap.active(False)
        except Exception as e:
            log(f"[RADIO] Wi-Fi power-down problem: {e}")
        try:
            import bluetooth
            ble = bluetooth.BLE()
            if ble.active() and not self.ble_in_use:
                ble.active(False)
        except Exception as e:
            log(f"[RADIO] BLE power-down problem: {e}")
        after = _state()
        log(f"[RADIO] {tag or 'power-down'}: sta/ap/ble {before} -> {after}")
        return after