# records_meta.py - what the shared record format (docs/implementation/en/data-format.md) needs to know about To-Dos and notes beyond their
# files: the record id, when the content was edited ("e") and when the state changed ("c"; for a checklist also
# per item) - in <collection>/meta.json:  {"<file name>": {"id": 3, "e": 1760259600, "c": 0, "items": {"mleko": 1760...}}}
#
# Kept by StorageManager (saving, renaming and deleting a file) and TodoEditor (ticking); read by the Bluetooth sync.
# A file without an entry (made before 2.0, or copied over USB) has e = c = 0 and gets its id when one is asked for.
import json
import os
from timeutil import wire_now

SYNCED = ("todo", "notes")


class Meta:
    def __init__(self, folder):
        self._path = folder + "/meta.json"
        self._data = None

    def _load(self):
        if self._data is None:
            try:
                with open(self._path) as f:
                    data = json.loads(f.read())
                self._data = data if isinstance(data, dict) else {}
            except (OSError, ValueError):
                self._data = {}
        return self._data

    def save(self):
        if self._data is None:
            return
        try:
            with open(self._path, "w") as f:
                f.write(json.dumps(self._data))
        except OSError as e:
            print(f"[META] cannot save {self._path}: {e}")

    def get(self, stem):
        return self._load().get(stem, {})

    def edited(self, stem, old_stem=None, at=None):
        """The file `stem` was written (by the editor, or as `old_stem` renamed): a new content time."""
        data = self._load()
        entry = data.pop(old_stem, None) if old_stem and old_stem != stem else None
        entry = entry or data.get(stem) or {}
        entry["e"] = wire_now() if at is None else at
        data[stem] = entry
        self.save()

    def state(self, stem, at=None, item=None):
        """The state of `stem` changed (ticked / un-ticked) - or of one of its items."""
        entry = self._load().setdefault(stem, {})
        at = wire_now() if at is None else at
        if item is None:
            entry["c"] = at
        else:
            entry.setdefault("items", {})[item] = at
        self.save()

    def forget(self, stem):
        if self._load().pop(stem, None) is not None:
            self.save()

    def ids(self, stems, slot=0):
        """{stem: id} for these files; the ones without an id get one now (in `slot`) and the file is saved."""
        from ble.merge import next_id
        data = self._load()
        known = [{"id": e["id"]} for e in data.values() if "id" in e]
        changed = False
        out = {}
        for stem in stems:
            entry = data.setdefault(stem, {})
            if "id" not in entry:
                entry["id"] = next_id(known, slot)
                known.append({"id": entry["id"]})
                changed = True
            out[stem] = entry["id"]
        if changed:
            self.save()
        return out

    def stem_of(self, rid):
        for stem, entry in self._load().items():
            if entry.get("id") == rid:
                return stem
        return None

    def set(self, stem, entry):
        """Put an entry as it came from the head (id, e, c, items)."""
        self._load()[stem] = entry
        self.save()

    def prune(self, stems):
        """Forget the entries of files that are gone."""
        data = self._load()
        gone = [s for s in data if s not in stems]
        for s in gone:
            del data[s]
        if gone:
            self.save()
