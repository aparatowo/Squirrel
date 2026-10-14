# tools/tests/test_i18n.py - i18n.py: every text of the catalogue is found, i18n.fill, the fallback to English
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools/i18n")
import build
import i18n

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


class Cfg:
    lang = "en"

    def get(self, key):
        return self.lang


cfg = Cfg()
i18n._wanted = lambda: cfg.lang if cfg.lang in i18n.LANGUAGES else "en"
i18n._attached = True                            # no appconfig here: the language is set as the setting would set it


def use(code):
    cfg.lang = code
    i18n._on_change("LANGUAGE", code)

langs, rows = build.read_catalog()
check("English: the text itself", i18n._("Settings") == "Settings")
for code in ("pl", "fr", "de"):
    use(code)
    wrong = [en for en, tr in rows.items() if tr.get(code) and i18n._(en) != tr[code]]
    check("%s: every catalogue text found (%d wrong)" % (code, len(wrong)), not wrong)
    check("%s: unknown text stays English" % code, i18n._("No such text, surely") == "No such text, surely")
use("pl")
check("pl: Settings", i18n._("Settings") == "Ustawienia")
check("fill: values kept", i18n.fill("Synced 2 of 3", ("Connecting: %s", "Synced %d of %d")) == "Zsynchronizowano 2 z 3")
check("fill: a name with spaces", i18n.fill("Connecting: Squirrel! T-Watch", ("Connecting: %s",)) == "Łączenie: Squirrel! T-Watch")
check("fill: no template matches -> as a plain text", i18n.fill("Stopped", ("Synced %d of %d",)) == "Zatrzymano")
check("fill: unknown stays", i18n.fill("whatever 1", ("Synced %d of %d",)) == "whatever 1")
check("fill: zero-padded", i18n.fill("Routine 08:05", ("Routine %02d:%02d",)) == "Rutyna 08:05")
check("fill: the reason inside translated too",
      i18n.fill("failed: wrong code", ("failed: %s",), ("wrong code",)) == "błąd: zły kod")
check("fill: an unknown reason stays as it is",
      i18n.fill("failed: [Errno 116] ETIMEDOUT", ("failed: %s",), ("wrong code",)) == "błąd: [Errno 116] ETIMEDOUT")
use("xx")
check("unknown language -> English", i18n._("Settings") == "Settings" and i18n.language() == "en")

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
