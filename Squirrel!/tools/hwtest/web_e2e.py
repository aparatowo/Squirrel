# tools/hwtest/web_e2e.py - the Web Bluetooth page (tools/web/squirrel_ble.html) against a real watch, end to end
#
# The watch (node) runs the app in its REPL with Settings -> Bluetooth open and reports the pairing code; Chrome opens
# the page straight from disk (file://) with a throwaway profile; a small DevTools script (Node.js) clicks Connect,
# picks the watch in Chrome's device chooser (the DeviceAccess domain), types the code into the page's prompt and
# reads what the page shows.  From the folder with squirrel_app.py:
#     python3 tools/hwtest/web_e2e.py /dev/ttyACM1
# Needs google-chrome (or CHROME=...) and node.  Note: a node keeps one pairing key, so pairing the page replaces the
# Cardputer's key on the watch - pair the Cardputer again afterwards (tools/hwtest/ble_e2e.py does it).
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

sys.path.insert(0, ".")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ble_e2e

CDP = r'''
const [wsUrl, codeFile] = process.argv.slice(2);
const fs = require("fs");
const ws = new WebSocket(wsUrl);
let id = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((ok) => { const n = ++id; pending.set(n, ok); ws.send(JSON.stringify({ id: n, method, params })); });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const text = async (expr) => (await send("Runtime.evaluate", { expression: expr, returnByValue: true })).result?.value;
let picked = false;
ws.onmessage = async (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result || msg); pending.delete(msg.id); return; }
  if (msg.method === "DeviceAccess.deviceRequestPrompted" && !picked) {
    const dev = msg.params.devices.find((d) => (d.name || "").includes("Squirrel"));
    console.log("CHOOSER", JSON.stringify(msg.params.devices.map((d) => d.name)));
    if (dev) { picked = true; await send("DeviceAccess.selectPrompt", { id: msg.params.id, deviceId: dev.id }); console.log("PICKED", dev.name); }
  }
  if (msg.method === "Page.javascriptDialogOpening") {
    console.log("DIALOG", msg.params.type, msg.params.message);
    let code = "";
    for (let i = 0; i < 100 && !code; i++) { try { code = fs.readFileSync(codeFile, "utf8").trim(); } catch (e) {} if (!code) await sleep(200); }
    console.log("TYPING", code);
    await send("Page.handleJavaScriptDialog", { accept: true, promptText: code });
  }
};
ws.onopen = async () => {
  await send("Page.enable"); await send("Runtime.enable"); await send("DeviceAccess.enable");
  await send("Runtime.evaluate", { expression: 'document.getElementById("connect").click()', userGesture: true });
  let last = "";
  for (let i = 0; i < 90; i++) {
    await sleep(1000);
    const s = await text('document.getElementById("status").textContent');
    if (s !== last) { console.log("STATUS", s); last = s; }
    if (/Connected to/.test(s || "")) {
      await sleep(4000);
      console.log("PAGE", JSON.stringify(await text('document.getElementById("app").innerText')));
      break;
    }
  }
  console.log("CDP-END"); process.exit(0);
};
'''


def main(watch_port):
    chrome = os.environ.get("CHROME") or shutil.which("google-chrome") or shutil.which("chromium")
    page = os.path.abspath("tools/web/squirrel_ble.html")
    work = tempfile.mkdtemp()
    code_file = os.path.join(work, "code")
    out = {}
    node = threading.Thread(target=ble_e2e.run, args=(watch_port, ble_e2e.NODE % {"pre": ""}, True, 0, out, "watch"))
    node.start()
    proc = subprocess.Popen([chrome, "--user-data-dir=" + os.path.join(work, "profile"), "--no-first-run",
                             "--no-default-browser-check", "--enable-experimental-web-platform-features",
                             "--remote-debugging-port=9333", "file://" + page],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(50):
            time.sleep(0.3)
            try:
                tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9333/json"))
                ws_url = next(t["webSocketDebuggerUrl"] for t in tabs if t.get("url", "").startswith("file://"))
                break
            except Exception:
                pass
        time.sleep(8)                                   # the watch starts its app and begins advertising
        script = os.path.join(work, "cdp.js")
        open(script, "w").write(CDP)
        cdp = subprocess.Popen(["node", script, ws_url, code_file], stdout=subprocess.PIPE, text=True)
        while True:
            line = cdp.stdout.readline()
            if not line:
                break
            print(line.rstrip())
            if "code" in ble_e2e.SHARED and not os.path.exists(code_file):
                open(code_file, "w").write(ble_e2e.SHARED["code"])
            if line.startswith("DIALOG"):               # the code may come just after the prompt opens
                for _ in range(100):
                    if "code" in ble_e2e.SHARED:
                        open(code_file, "w").write(ble_e2e.SHARED["code"])
                        break
                    time.sleep(0.2)
        cdp.wait()
    finally:
        proc.terminate()
        node.join()
        shutil.rmtree(work, ignore_errors=True)
    print("---- watch ----")
    print("\n".join(l for l in out.get("watch", "").splitlines() if "[BLE]" in l or l.startswith(("PASSKEY", "NODE-RESULT", "TODOS"))))


if __name__ == "__main__":
    main(sys.argv[1])
