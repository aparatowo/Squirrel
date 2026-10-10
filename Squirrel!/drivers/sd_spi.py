# sd_spi.py - an SD card on SPI, mounted at /sd (the Cardputer's microSD slot)
#
# The card is mounted here with machine.SDCard + os.mount (the app owns the block device).
#
# Only if that fails (for instance because something else already holds the SD bus) does it
# fall back to the firmware helper hardware.SDCard(...), which mounts /sd by itself.
# (Mounting with os.mount after the helper fails, and creating a second machine.SDCard while
# the first one is alive fails with ESP_ERR_INVALID_STATE - hence the order below.)
# The helper may print "[Errno 22] EINVAL" on its own; that is harmless.

import os
import time
from boot_log import log

MOUNT_POINT = "/sd"
_ATTEMPTS = 3
_RETRY_DELAY_MS = 300


def _sd_usable():
    """True when /sd can actually be listed (not merely named in '/')."""
    try:
        os.listdir(MOUNT_POINT)
        return True
    except OSError:
        return False


class SDCardManager:
    """Owns the lifecycle of the microSD card."""

    def __init__(self, slot, width, sck, miso, mosi, cs, freq):
        self._args = dict(slot=slot, width=width, sck=sck, miso=miso, mosi=mosi, cs=cs, freq=freq)
        self.is_mounted = False
        self._sd = None        # what the firmware helper returned (None on this firmware); kept referenced
        self._card = None      # the machine.SDCard we created: the block device
        self.mount()

    @property
    def owns_card(self):
        return self._card is not None

    @property
    def block_device(self):
        return self._card

    def mount(self):
        """Make /sd available.  Returns True on success."""
        if self._card is not None:
            return self._mount_owned()
        if _sd_usable():
            self.is_mounted = True
            log("[SD] Already available at /sd (mounted by someone else: no block access)")
            return True
        if self._mount_direct():
            return True
        return self._mount_with_helper()

    def _mount_direct(self):
        try:
            import machine
            card = machine.SDCard(**self._args)
        except Exception as e:
            log(f"[SD] machine.SDCard failed: {e}")
            return False
        try:
            os.mount(card, MOUNT_POINT)
            if not _sd_usable():
                raise OSError("mounted but not readable")
        except Exception as e:
            log(f"[SD] Mounting machine.SDCard failed: {e}")
            try:
                os.umount(MOUNT_POINT)
            except Exception:
                pass
            try:
                card.deinit()          # release the SPI bus, or the helper below could not use it either
            except Exception:
                pass
            return False
        self._card = card
        self.is_mounted = True
        log("[SD] Mounted at /sd through machine.SDCard (block access available)")
        return True

    def _mount_owned(self):
        """Mount the card we already own (after an unmount)."""
        for attempt in range(1, _ATTEMPTS + 1):
            try:
                os.mount(self._card, MOUNT_POINT)
            except Exception as e:
                log(f"[SD] Remount attempt {attempt}: {e}")
            if _sd_usable():
                self.is_mounted = True
                return True
            time.sleep_ms(_RETRY_DELAY_MS)
        log("[SD] Card NOT available after remounting")
        return False

    def _mount_with_helper(self):
        try:
            from hardware import SDCard
        except Exception as e:
            log(f"[SD] hardware.SDCard import failed: {e}")
            return False

        for attempt in range(1, _ATTEMPTS + 1):
            try:
                self._sd = SDCard(**self._args)
            except Exception as e:
                log(f"[SD] Attempt {attempt}: constructor raised: {e}")

            if _sd_usable():
                self.is_mounted = True
                log(f"[SD] Mounted at /sd through the firmware helper (attempt {attempt}; no block access)")
                return True
            time.sleep_ms(_RETRY_DELAY_MS)

        log("[SD] Card NOT available after all attempts")
        return False

    def unmount(self):
        try:
            os.umount(MOUNT_POINT)
        except Exception as e:
            log(f"[SD] Unmount error: {e}")
        if self._card is None:
            self._sd = None
        self.is_mounted = False

    def remount(self):
        if self.is_mounted:
            self.unmount()
        return self.mount()
