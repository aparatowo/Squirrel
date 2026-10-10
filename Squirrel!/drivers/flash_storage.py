# flash_storage.py - the app's folder on the internal flash's file system (a device without an SD card)
#
# Nothing to mount: the firmware mounts the flash at start-up.  The same calls as drivers/sd_spi.py.
import os
from boot_log import log


class FlashStorage:
    owns_card = False
    block_device = None

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.is_mounted = False
        self.mount()

    def mount(self):
        try:
            os.mkdir(self.base_dir)
        except OSError:
            pass                                   # there already
        try:
            os.listdir(self.base_dir)
            self.is_mounted = True
        except OSError as e:
            log(f"[FLASH] {self.base_dir} not usable: {e}")
            self.is_mounted = False
        return self.is_mounted

    def unmount(self):
        pass

    def remount(self):
        return self.mount()
