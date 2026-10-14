# ble/auth.py - who may sync this device: pairing with a code and a signed proof in every session
#                (docs/implementation/en/bluetooth.md 6, data-format.md 4: AUTH_*)
#
# Done by the application, not by the Bluetooth link: link-level pairing (LE Secure Connections) worked, but an
# encrypted link reset the Cardputer now and then during a sync (2026-10-13; the cause is in the firmware, still open).
#
# Pairing (once):  the head sends its nonce (AUTH_HELLO); the node answers with its own and shows a 6-digit code; the
#                  user types the code on the head; both derive the key  K = HMAC(code, "squirrel-pair" + nonces)[:16]
#                  and the head proves it has it (AUTH_CONFIRM: HMAC(K, "confirm" + node nonce)).  The code never goes
#                  over the air.
# Every session:   the node gives a fresh challenge (AUTH_CHALLENGE); the head answers HMAC(K, "session" + challenge)
#                  (AUTH_PROVE).  Until then the node refuses everything but INFO and the time it shows.
# What it does not do: the records themselves go unencrypted - someone nearby with a radio could read them, not write
# them.  A pairing overheard by such a person could be broken offline (a 6-digit code).
import json
import os

import hashlib

KEY_LEN = 16
NONCE_LEN = 16
PROOF_LEN = 16


def hmac_sha256(key, msg):
    """HMAC-SHA256 (RFC 2104) with nothing but hashlib.sha256 - MicroPython has no hmac module."""
    block = 64
    if len(key) > block:
        key = hashlib.sha256(key).digest()
    key = key + bytes(block - len(key))
    inner = hashlib.sha256(bytes(b ^ 0x36 for b in key) + msg).digest()
    return hashlib.sha256(bytes(b ^ 0x5C for b in key) + inner).digest()


def random_bytes(n):
    return os.urandom(n)


def new_code():
    """A 6-digit code, as text ("042917")."""
    return "%06d" % (int.from_bytes(os.urandom(4), "little") % 1000000)


def pair_key(code, head_nonce, node_nonce):
    return hmac_sha256(code.encode(), b"squirrel-pair" + bytes(head_nonce) + bytes(node_nonce))[:KEY_LEN]


def confirm_proof(key, node_nonce):
    return hmac_sha256(key, b"confirm" + bytes(node_nonce))[:PROOF_LEN]


def session_proof(key, challenge):
    return hmac_sha256(key, b"session" + bytes(challenge))[:PROOF_LEN]


def same(a, b):
    """Compare without stopping at the first difference."""
    if len(a) != len(b):
        return False
    d = 0
    for x, y in zip(a, b):
        d |= x ^ y
    return d == 0


class AuthStore:
    """The keys of the pairs this device is in: on a node {"head": key}, on the head {"<node address>": key}.
    A file on the internal flash (never on a removable card)."""

    def __init__(self, path):
        self._path = path
        self._keys = {}
        try:
            with open(path) as f:
                self._keys = {k: bytes.fromhex(v) for k, v in json.loads(f.read()).items()}
        except (OSError, ValueError, AttributeError):
            pass

    def get(self, name):
        return self._keys.get(name)

    def set(self, name, key):
        self._keys[name] = bytes(key)
        self._save()

    def forget(self, name=None):
        if name is None:
            self._keys = {}
        else:
            self._keys.pop(name, None)
        self._save()

    def _save(self):
        try:
            with open(self._path, "w") as f:
                f.write(json.dumps({k: v.hex() for k, v in self._keys.items()}))
        except OSError as e:
            print("[BLE] cannot save the pairing keys: %s" % e)


def auth_path(base_dir):
    """Next to the app's data when that is on the internal flash, else on /flash."""
    return (base_dir if not base_dir.startswith("/sd") else "/flash") + "/ble_auth.json"
