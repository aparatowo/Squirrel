# ble/node_data.py - the app's data as the records of docs/implementation/en/data-format.md, for the Bluetooth sync (both sides use it)
#
# Routines are records already (routines.json); To-Dos and notes are files plus records_meta.Meta (id, e, c); the
# statistics come from the day counters and the focus timer; the routine log from the EventLog.  put() / delete()
# take what the head sent and write it the device's own way - a tick that comes from the head is not counted in this
# device's statistics (it was counted where it was made).
from ble import protocol as P
from timeutil import wire_now, civil_from_days, weekday_from_days
from storage_manager import file_stem


def _day(wire):
    """'YYYY-MM-DD' of a wire time (0 -> today)."""
    z = (wire or wire_now()) // 86400
    return "%04d-%02d-%02d" % civil_from_days(z)


class NodeData:
    def __init__(self, cfg, rtc, storage, todo_editor, routines, events=None, routines_done=None, todos_done=None,
                 focus=None, kind="cardputer", name="Squirrel!", app_version="2.0", caps=(), slot=0, has_rtc=False,
                 peers=None):
        self.cfg, self.rtc, self.storage, self.todo = cfg, rtc, storage, todo_editor
        self.routines, self.events = routines, events
        self._counters = {"routines": routines_done, "todos": todos_done}
        self.focus = focus
        self._info = {"kind": kind, "caps": list(caps), "name": name, "app": app_version, "slot": slot}
        self._has_rtc = has_rtc
        self.peers = peers                # ble.peers.Peers: where this device's slot is kept
        self.auth = None                  # ble.auth.AuthStore: the pairing keys (for_app() sets it)

    def join(self, slot):
        """The head made this device the node in `slot`: the records it has so far (made here, or copied over USB,
        all in slot 0 or in an earlier slot) become its LOCAL records in the new slot - the head will neither
        overwrite nor delete them."""
        from ble.merge import COUNTER_BITS, slot_of
        if not 1 <= slot <= 6:
            raise ValueError(P.ERR_BAD_DATA)
        old = self._info["slot"]
        mask = (1 << COUNTER_BITS) - 1

        def renumber(rid):
            return slot << COUNTER_BITS | (rid & mask) if slot_of(rid) in (0, old) else rid
        if old != slot:
            for r in self.routines.items:
                r["id"] = renumber(r["id"])
            self.routines.slot = slot
            self.routines.save()
            for folder in ("todo", "notes"):
                meta = self.storage.meta(folder)
                for stem in self.storage.stems(folder):
                    entry = meta.get(stem)
                    if "id" in entry:
                        entry = dict(entry)
                        entry["id"] = renumber(entry["id"])
                        meta.set(stem, entry)
        self._info["slot"] = slot
        if self.peers is not None:
            self.peers.slot = slot
            self.peers.save()

    # ------------------------------------------------------------------------------------------- INFO / TIME
    def info(self):
        return dict(self._info)

    def time(self):
        src = getattr(self.rtc, "last_sync_source", "soft")
        source = {"wifi": "ntp", "manual": "manual", "soft": "soft", "peer": "peer"}.get(src, "rtc")
        return {"time": wire_now(), "offset": self._offset(), "source": source, "age": 0,
                "has_rtc": self._has_rtc, "rtc_valid": self._has_rtc and source == "rtc"}

    def _offset(self):
        try:
            return self.cfg.get("TIME_UTC_OFFSET_MIN")
        except KeyError:
            return 0

    def set_time(self, t):
        """Set the clock from a TIME record (written to the hardware clock too, as a manual setting is)."""
        days, rest = divmod(t["time"], 86400)
        y, m, d = civil_from_days(days)
        self.rtc.set_manual((y, m, d, rest // 3600, rest // 60 % 60, rest % 60, weekday_from_days(days), 0))
        self.rtc.last_sync_source = "peer"

    # ------------------------------------------------------------------------------------------- SETTINGS
    def settings(self):
        out = {}
        known = self.cfg.keys()
        for key in P.SYNCED_KEYS:
            if key in known:
                out[key] = self.cfg.text_of(key)
        if "TRAINING_PLAN" in P.SYNCED_KEYS:
            import nuts
            from intervals import load_training
            out["TRAINING_PLAN"] = P.training_text(load_training(nuts.TRAINING_FILE))
        return out

    def apply_settings(self, values):
        """-> (applied, refused): keys this device does not know are neither."""
        applied, refused = 0, 0
        known = self.cfg.keys()
        for key, text in values.items():
            try:
                if key == "TRAINING_PLAN":
                    import nuts
                    from intervals import save_training
                    save_training(nuts.TRAINING_FILE, P.training_plan(text))
                elif key in known:
                    self.cfg.set(key, self.cfg.parse(key, text), save=False)
                else:
                    continue
                applied += 1
            except ValueError:
                refused += 1
        if applied:
            self.cfg.save()
        return applied, refused

    # ------------------------------------------------------------------------------------------- data sets
    def records(self, which, since=0):
        if which == P.SET_ROUTINES:
            return [dict(r) for r in self.routines.items]
        if which == P.SET_TODO:
            return self._todos()
        if which == P.SET_NOTES:
            return self._notes()
        if which == P.SET_STATS:
            return self._stats()
        if which == P.SET_EVENTS:
            return self.events.since(since) if self.events is not None else []
        raise ValueError(P.ERR_UNKNOWN_SET)

    def get(self, which, rid):
        for r in self.records(which):
            if r.get("id") == rid:
                return r
        return None

    def put(self, which, r):
        if which == P.SET_ROUTINES:
            items = self.routines.items
            for n, old in enumerate(items):
                if old["id"] == r["id"]:
                    items[n] = dict(r)
                    break
            else:
                items.append(dict(r))
            self.routines.save()
        elif which == P.SET_TODO:
            self._put_file("todo", r, todo=True)
        elif which == P.SET_NOTES:
            self._put_file("notes", r, todo=False)
        else:
            raise ValueError(P.ERR_UNKNOWN_SET)

    def delete(self, which, rid):
        """-> False when there is no such record."""
        if which == P.SET_ROUTINES:
            before = len(self.routines.items)
            self.routines.items[:] = [r for r in self.routines.items if r["id"] != rid]
            if len(self.routines.items) == before:
                return False
            self.routines.save()
            return True
        if which in (P.SET_TODO, P.SET_NOTES):
            folder = "todo" if which == P.SET_TODO else "notes"
            stem = self.storage.meta(folder).stem_of(rid)
            if stem is None:
                return False
            if which == P.SET_TODO:
                self.todo.apply_state(stem, False, {})
            return self.storage.delete_path("%s/%s/%s.txt" % (self.storage.base_dir, folder, stem))
        raise ValueError(P.ERR_UNKNOWN_SET)

    # ------------------------------------------------------------------------------------------- To-Dos, notes
    def _read(self, folder, stem):
        try:
            with open("%s/%s/%s.txt" % (self.storage.base_dir, folder, stem)) as f:
                return f.read()
        except OSError:
            return None

    def _todos(self):
        from todo_editor import checklist_items
        stems = self.storage.stems("todo")
        meta = self.storage.meta("todo")
        ids = meta.ids(stems, self._info["slot"])
        done = self.todo.done_map()
        out = []
        for stem in stems:
            text = self._read("todo", stem)
            if text is None:
                continue
            m = meta.get(stem)
            r = {"id": ids[stem], "t": text, "done": stem in done, "e": m.get("e", 0), "c": m.get("c", 0)}
            items = checklist_items(text)
            if items:
                times = m.get("items", {})
                r["items"] = [{"t": t, "done": (stem + "#" + t) in done, "c": times.get(t, 0)} for t in items]
            out.append(r)
        return out

    def _notes(self):
        stems = self.storage.stems("notes")
        meta = self.storage.meta("notes")
        ids = meta.ids(stems, self._info["slot"])
        out = []
        for stem in stems:
            text = self._read("notes", stem)
            if text is not None:
                out.append({"id": ids[stem], "t": text, "e": meta.get(stem).get("e", 0)})
        return out

    def _put_file(self, folder, r, todo):
        meta = self.storage.meta(folder)
        title = r["t"].split("\n")[0].strip() or "untitled"
        stem = file_stem(title)
        old = meta.stem_of(r["id"])
        if old is None and stem in self.storage.stems(folder):
            stem = file_stem(self.storage.unique_title(folder, title, 30))     # another record has that name here
        path = "%s/%s/%s.txt" % (self.storage.base_dir, folder, stem)
        try:
            import os
            os.mkdir("%s/%s" % (self.storage.base_dir, folder))
        except OSError:
            pass
        with open(path, "w") as f:
            f.write(r["t"])
        entry = {"id": r["id"], "e": r.get("e", 0)}
        if todo:
            entry["c"] = r.get("c", 0)
            items = r.get("items") or []
            if items:
                entry["items"] = {i["t"]: i.get("c", 0) for i in items}
        if old is not None and old != stem:
            if todo:
                self.todo.apply_state(old, False, {})
            self.storage.delete_path("%s/%s/%s.txt" % (self.storage.base_dir, folder, old))
        meta.set(stem, entry)
        if todo:
            self.todo.apply_state(stem, r.get("done", False),
                                  {i["t"]: _day(i.get("c")) for i in (r.get("items") or []) if i.get("done")},
                                  _day(r.get("c")))

    # ------------------------------------------------------------------------------------------- statistics
    def _stats(self, days=60):
        out = []
        for kind, counter in self._counters.items():
            if counter is not None:
                for key, _wd, n in counter.week(days):
                    if n:
                        out.append({"day": key, "k": kind, "n": n})
        if self.focus is not None:
            for key, _wd, secs in self.focus.week(days):
                if secs >= 60:
                    out.append({"day": key, "k": "focus_min", "n": secs // 60})
        return out

    @staticmethod
    def revision(records):
        """A number that changes when the list changes (ids, edit and state times): the head compares it first."""
        h = len(records)
        for r in records:
            h = (h * 31 + r.get("id", 0) * 7 + r.get("e", 0) + r.get("c", 0) * 3 + (1 if r.get("del") else 0)) & 0xFFFFFFFF
            for item in r.get("items", ()):
                h = (h * 31 + item.get("c", 0) + (1 if item.get("done") else 0)) & 0xFFFFFFFF
        return h


def caps_of_port():
    from features import has, hardware
    caps = ["routines", "todo", "stats", "pomodoro", "breathing", "cuckoo"]
    if has("notes"):
        caps.append("notes")                       # a device without notes (the watch, by choice) is not sent them
    if hardware("clock.alarm") or has("deep_sleep"):
        caps.append("rtc")
    if has("ble_hub"):
        caps.append("hub")
    return caps


def for_app(app):
    """(NodeData, Peers) of the running app - what both Bluetooth screens work with."""
    import nuts
    import port_config
    from appconfig import cfg
    from ble.peers import Peers
    from ble.secrets import SECRETS, keys_path
    from ble.auth import AuthStore, auth_path
    SECRETS.use(keys_path(nuts.BASE_DIR))            # link pairing's bonds (nuts.BLE_LINK_PAIRING), on the internal flash
    peers = Peers(nuts.BASE_DIR + "/ble.json", nuts.BASE_DIR + "/focus/peers")
    kind = "twatch" if port_config.PORT.startswith("twatch") else "cardputer"
    chip = app.rtc.chip() if hasattr(app.rtc, "chip") else None
    app.routines.slot = peers.slot
    data = NodeData(cfg, app.rtc, app.storage, app.todo_editor, app.routines,
                    events=getattr(app.scheduler, "_events", None), routines_done=app.routines_done,
                    todos_done=app.todos_done, focus=app.focus, kind=kind, name=port_config.PORT_TITLE,
                    caps=caps_of_port(), slot=peers.slot, has_rtc=chip is not None, peers=peers)
    data.auth = AuthStore(auth_path(nuts.BASE_DIR))  # the app's pairing keys, on the internal flash too
    return data, peers


def device_name():
    import port_config
    return "Squirrel! " + ("T-Watch" if port_config.PORT.startswith("twatch") else "Cardputer")
