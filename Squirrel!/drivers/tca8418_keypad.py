# tca8418_keypad.py - a key matrix scanned by a TCA8418 on I2C (the Cardputer ADV keyboard)
#
# The key maps (which action each key code gives, with and without the modifiers) belong to the device and come from
# the port (ports/<port>/keymap.py); the I2C bus comes from the board, which can open it again after errors.
import time
from boot_log import log
from charmap import compose
from appconfig import cfg

# Boot logs showed read errors (259 = ESP_ERR_INVALID_STATE) that vanish as soon as
# machine.I2C(0, ...) is constructed again, so recovery = reopen the bus.
_RECOVER_MIN_INTERVAL_MS = 200   # do not reopen more often than this
_MAX_LOGGED_FAILURES = 30        # keep the log file small

# TCA8418 keyboard controller (subset of its registers).  Cardputer ADV wires the 56
# keys as a 7 x 8 matrix (rows R0-R6, columns C0-C7); a key event carries
# code = row * 10 + col + 1, which is what MAP_NAV of the port's keymap is keyed on.
_TCA_CFG = 0x01
_TCA_INT_STAT = 0x02
_TCA_KEY_EVENT_A = 0x04          # FIFO head: bit7 = pressed, bits 6..0 = key code
_TCA_KP_GPIO = (0x1D, 0x1E, 0x1F)  # which pins belong to the key matrix (rows, cols 0-7, cols 8-9)
_KP_CONFIG = (0x7F, 0xFF, 0x00)
_CFG_KE_IEN = 0x01


class TCA8418Keypad:
    def __init__(self, open_bus, addr, keymap):
        """open_bus() -> a new machine.I2C object for the bus the controller is on (called again to recover);
        keymap: a module with MAP_NAV, MAP_TEXT, MAP_FN, MAP_SHIFT, MAP_CTRL, MAP_OPT, MAP_ALT, MAP_ALT_SHIFT,
        MODIFIER_STICKY and MODIFIER_MOMENTARY (see ports/cardputer_adv/keymap.py)."""
        self._new_bus = open_bus
        self._keys = keymap
        self.i2c = None
        self.addr = addr
        self.is_text_mode = False
        # Set per screen by the app: when True, Aa / OPT / FN / CTRL / ALT are delivered
        # to the screen as ordinary key actions instead of toggling a modifier.
        self.modifiers_as_keys = False
        
        self.flags = {
            'SHIFT': False,
            'FN': False,
            'CTRL': False,
            'OPT': False,
            'ALT': False
        }

        self.last_key_code = 0
        # Persistent modifier label for the UI indicator — updated on toggle,
        # NOT cleared after a key action, so the renderer always sees current state.
        self.display_modifier = None  # None | 'SHIFT' | 'FN' | 'CTRL' | 'OPT' | 'ALT'

        self._failing = False
        self._fail_count = 0
        self._next_recover_ms = 0

        if self._open_bus(scan=True):
            self._init_controller()

    def _open_bus(self, scan=False):
        """(Re)create the I2C bus object; also used as the recovery step.

        machine.I2C has no deinit() on this firmware, so constructing it again
        is the only reset available.  The device scan runs only at start-up.
        """
        try:
            self.i2c = self._new_bus()
        except Exception as e:
            self.i2c = None
            log(f"[KEYPAD ERROR] I2C init: {e}")
            return False
        print("[KEYPAD] Magistrala I2C gotowa.")
        if scan:
            try:
                log(f"[KEYPAD] I2C scan: {[hex(x) for x in self.i2c.scan()]}")
            except Exception as e:
                log(f"[KEYPAD] I2C scan failed: {e}")
        return True

    def _tca_regs(self):
        """Read (CFG, (KP_GPIO1, KP_GPIO2, KP_GPIO3)) from the TCA8418."""
        cfg = self.i2c.readfrom_mem(self.addr, _TCA_CFG, 1)[0]
        kp = tuple(self.i2c.readfrom_mem(self.addr, r, 1)[0] for r in _TCA_KP_GPIO)
        return cfg, kp

    def _init_controller(self):
        """Make sure the TCA8418 actually scans the key matrix.

        After power-up the controller is idle and reports no key until the matrix
        size is configured.  Some firmware builds do that during their own start-up
        (e.g. a start-up screen that reads the keyboard); others do not, and then
        the FIFO stays empty forever.  Configuring it is idempotent, so registers
        are written only when they differ, and both states are logged.
        """
        try:
            cfg, kp = self._tca_regs()
            log("[KEYPAD] TCA8418 before: CFG=0x%02X KP_GPIO=%s" % (cfg, ",".join("0x%02X" % v for v in kp)))
            if kp != _KP_CONFIG:
                for reg, val in zip(_TCA_KP_GPIO, _KP_CONFIG):
                    self.i2c.writeto_mem(self.addr, reg, bytes([val]))
                log("[KEYPAD] TCA8418 was not scanning the matrix - configured 7x8")
            if not cfg & _CFG_KE_IEN:
                self.i2c.writeto_mem(self.addr, _TCA_CFG, bytes([cfg | _CFG_KE_IEN]))
            for _ in range(10):                     # drop events queued before we started
                if self.i2c.readfrom_mem(self.addr, _TCA_KEY_EVENT_A, 1)[0] == 0:
                    break
            self.i2c.writeto_mem(self.addr, _TCA_INT_STAT, bytes([0x1F]))
            cfg, kp = self._tca_regs()
            log("[KEYPAD] TCA8418 after:  CFG=0x%02X KP_GPIO=%s" % (cfg, ",".join("0x%02X" % v for v in kp)))
        except Exception as e:
            log(f"[KEYPAD] TCA8418 init failed: {e}")

    def _recover(self):
        """Reopen the bus after a failed read (rate-limited)."""
        now = time.ticks_ms()
        if time.ticks_diff(now, self._next_recover_ms) < 0:
            return
        self._next_recover_ms = time.ticks_add(now, _RECOVER_MIN_INTERVAL_MS)
        self._open_bus()

    def set_text_mode(self, enable: bool):
        self.is_text_mode = enable
        self._reset_all_flags()
        print(f"[KEYPAD] Set text mode: {self.is_text_mode}")

    def _reset_all_flags(self):
        for k in self.flags:
            self.flags[k] = False
        self.display_modifier = None

    def _toggle_modifier(self, mod_name: str):
        """Toggle a modifier key.

        Pressing an already-active modifier deactivates it (toggle off).
        Pressing a different modifier first clears all others (only one active
        at a time), then activates the new one.  The one exception is the pair
        Aa + ALT, in either order: together they type capital accented letters
        (ALT+a = ą, Aa + ALT+a = Ą), so each keeps the other.
        """
        current_state = self.flags.get(mod_name, False)
        keep = None
        if mod_name == 'ALT' and self.flags['SHIFT']:
            keep = 'SHIFT'
        elif mod_name == 'SHIFT' and self.flags['ALT']:
            keep = 'ALT'
        self._reset_all_flags()          # clear everything (including display)
        if keep:
            self.flags[keep] = True
        if not current_state:
            # Activate this modifier
            self.flags[mod_name] = True
            self.display_modifier = mod_name

        print(f"[KEYPAD MODIFIER] {mod_name} -> {self.flags.get(mod_name)} "
              f"(sticky={mod_name in self._keys.MODIFIER_STICKY}, display={self.display_modifier})")

    def _release_momentary_modifiers(self):
        """Auto-reset modifiers that are MOMENTARY after a key has been consumed."""
        for mod in self._keys.MODIFIER_MOMENTARY:
            if self.flags.get(mod):
                self.flags[mod] = False
                # a sticky modifier that was kept alongside (Aa) is what the mark shows again
                self.display_modifier = 'SHIFT' if self.flags['SHIFT'] else ('FN' if self.flags['FN'] else None)
                print(f"[KEYPAD MODIFIER] {mod} auto-released (momentary)")

    def _get_active_map(self):
        k = self._keys
        if self.flags['SHIFT'] and self.flags['ALT']:
            return k.MAP_ALT_SHIFT                    # ALT with Aa on: capital accented letters
        if self.flags['SHIFT']:
            return k.MAP_SHIFT
        if self.flags['FN']:
            return k.MAP_FN
        if self.flags['CTRL']:
            return k.MAP_CTRL
        if self.flags['OPT']:
            return k.MAP_OPT
        if self.flags['ALT']:
            return k.MAP_ALT
        
        return k.MAP_TEXT if self.is_text_mode else k.MAP_NAV

    def acknowledge(self):
        """Clear the controller's interrupt flag (INT_STAT, reg 0x02): the INT line (GPIO 11) goes high again."""
        try:
            self.i2c.writeto_mem(self.addr, 0x02, b"\x1f")
            return True
        except Exception:
            return False

    def get_pressed_action(self):
        """Read one key event from the I2C keypad controller.

        Returns a tuple (action, modifier_changed) so the app loop knows
        whether to re-render the screen even when action is None (e.g. when
        the user just toggled FN or Aa and the indicator must update).
        """
        if not self.i2c:
            self._failing = True
            self._recover()
            return None, False

        try:
            data = self.i2c.readfrom_mem(self.addr, 0x04, 1)
            if self._failing:
                self._failing = False
                if self._fail_count <= _MAX_LOGGED_FAILURES:
                    log("[KEYPAD] read recovered")
            if not data or data[0] == 0:
                self.last_key_code = 0
                return None, False

            val = data[0]
            is_press = (val & 0x80) != 0
            key_code = val & 0x7F

            if is_press and key_code > 0:
                if key_code == self.last_key_code:
                    return None, False  # Ignore hold-down repetition until release

                self.last_key_code = key_code

                # 1. Check if the pressed key is a modifier
                base_action = self._keys.MAP_NAV.get(key_code)

                if base_action in self.flags or base_action == 'Aa':
                    if self.modifiers_as_keys:
                        print(f"[KEY EVENT] KeyCode: {key_code} -> Action: '{base_action}' (as key)")
                        return base_action, False
                    mod_key = 'SHIFT' if base_action == 'Aa' else base_action
                    self._toggle_modifier(mod_key)
                    # Return None action but signal that modifier state changed
                    # so the caller can trigger a re-render of the indicator.
                    return None, True

                # 2. Resolve action using the active modifier map
                current_map = self._get_active_map()
                action = current_map.get(key_code)

                # Fallback to base map when the modifier has no special binding
                if not action:
                    fallback_map = self._keys.MAP_TEXT if self.is_text_mode else self._keys.MAP_NAV
                    action = fallback_map.get(key_code)

                print(f"[KEY EVENT] KeyCode: {key_code} | TextMode: {self.is_text_mode} "
                      f"| Modifier: {self.display_modifier} -> Action: '{action}'")

                if not action:
                    return None, False

                # 3. Release only MOMENTARY modifiers after the key is consumed;
                #    STICKY modifiers (FN, SHIFT/Aa) remain until toggled off.
                self._release_momentary_modifiers()

                # ALT + letter types an accented letter with the chosen layout (ALT+a -> ą with "pl")
                return compose(action, cfg.get("KEYBOARD_LAYOUT")), False

        except Exception as e:
            # Never swallow silently: a dead keypad looks exactly like this.
            self._fail_count += 1
            if self._fail_count <= _MAX_LOGGED_FAILURES:
                log(f"[KEYPAD ERROR] read failed (#{self._fail_count}): {e}")
            self._failing = True
            self._recover()

        return None, False