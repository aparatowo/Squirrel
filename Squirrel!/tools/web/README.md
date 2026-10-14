# Squirrel! over Web Bluetooth

`squirrel_ble.html` (with `squirrel_protocol.js` next to it) talks to the Squirrel! devices from a browser: Chrome or
Edge on Android, Windows, macOS or Linux (not Safari / iOS, not Firefox).

- **Connected to the boss** (Cardputer: *Settings → Bluetooth → Be visible*): everything can be edited — To-Dos and
  their `>` checklists, routines, notes, settings, and the device's time from the phone.
- **Connected to a node** (watch: *Settings → Bluetooth*): ticking To-Dos and checklist items, routines on / off,
  settings and the time; the content of To-Dos and routines belongs to the boss.

The device waits 2 minutes for a connection; the page keeps the session alive while it is open.

**Pairing:** the first time, the device shows a 6-digit code and the page asks for it. The key is then kept in this
browser (per device); after clearing site data or in a private window the page asks for a new code. The records
themselves go over the air unencrypted — see docs/implementation/en/bluetooth.md §6.

**A watch remembers one pairing:** pairing this page with the watch makes the Cardputer ask for a new code at its next
sync (and pairing the Cardputer again makes the page ask). Pairing the page with the Cardputer changes nothing for the
watch.

## Opening the page - no server needed

Web Bluetooth needs a secure page: `https://`, `http://localhost` - or **a file opened from disk** (`file://`), which
Chrome treats as secure too.

- **On a computer:** open `squirrel_ble.html` straight from this folder (double-click, or drag it into Chrome). Keep
  `squirrel_protocol.js` next to it.
  - **Linux:** Chrome has Web Bluetooth switched off there by default: turn on
    `chrome://flags/#enable-experimental-web-platform-features` once (or start Chrome with
    `--enable-experimental-web-platform-features`). Windows and macOS need nothing.
  - Checked with Chrome 154: the page loads from `file://` and `navigator.bluetooth` is there, as on `localhost`.
- **On a phone (Android):** Chrome does not open local HTML files, so the page has to come from an `https://` address -
  any static hosting will do, no server of your own. For GitHub Pages the repository has a workflow ready,
  `.github/workflows/web-page.yml`: switch Pages on (*Settings → Pages → Source: GitHub Actions*) and run it (*Actions →
  Web Bluetooth page → Run workflow*); the page is then at `https://<user>.github.io/<repository>/`.
- `python3 -m http.server 8000` in this folder and `http://localhost:8000/squirrel_ble.html` also work, if you prefer.

## For developers

The codec is the JavaScript twin of `Squirrel!/ble/protocol.py` (docs/implementation/en/data-format.md);
`tools/tests/test_web_protocol.py` checks that both give the same bytes for the same records (needs Node.js).
