#!/bin/sh
# compare.sh - runs two versions of the app in the simulator and compares what they drew, logged and wrote.
#
#   tools/sim/compare.sh <micropython binary> <baseline app dir> <new app dir> <work dir>
#
# Example (baseline = the last commit):
#   git archive HEAD "Squirrel!" | tar -x -C /tmp/base
#   tools/sim/compare.sh ~/mp/micropython "/tmp/base/Squirrel!" "$PWD" /tmp/simwork
# The MicroPython unix port: make -C <firmware repo>/micropython/ports/unix (see tools/sim/README.md).
set -u
MP=$1; A=$2; B=$3; W=$4
HERE=$(cd "$(dirname "$0")" && pwd)
rm -rf "$W"; mkdir -p "$W/a" "$W/b"
for side in a b; do
    if [ $side = a ]; then APP=$A; else APP=$B; fi
    timeout 900 "$MP" -X heapsize=8M "$HERE/run_sim.py" "$APP" "$W/$side" "$W/trace_$side.txt" > "$W/out_$side.txt" 2>&1
    echo "$side: exit $? - $(tail -1 "$W/out_$side.txt")"
done
# lines that differ only because the code is a different size (free heap) are not behaviour
for side in a b; do
    grep -v -E "free heap|heap after|bytes free" "$W/out_$side.txt" > "$W/log_$side.txt"
    sed -E 's/^[0-9]+ //' "$W/$side/flash/boot_log.txt" | grep -v -E "free heap|heap after|bytes free" > "$W/boot_$side.txt"
done
status=0
cmp -s "$W/trace_a.txt" "$W/trace_b.txt" && echo "display trace: IDENTICAL ($(wc -l < "$W/trace_a.txt") lines)" || { echo "display trace: DIFFERENT"; diff "$W/trace_a.txt" "$W/trace_b.txt" | head -40; status=1; }
cmp -s "$W/log_a.txt" "$W/log_b.txt" && echo "console log: IDENTICAL" || { echo "console log: DIFFERENT"; diff "$W/log_a.txt" "$W/log_b.txt" | head -40; status=1; }
cmp -s "$W/boot_a.txt" "$W/boot_b.txt" && echo "boot_log.txt: IDENTICAL" || { echo "boot_log.txt: DIFFERENT"; diff "$W/boot_a.txt" "$W/boot_b.txt" | head -20; status=1; }
rm -f "$W/a/flash/boot_log.txt" "$W/b/flash/boot_log.txt"
diff -r "$W/a" "$W/b" > /dev/null && echo "files on /sd and /flash: IDENTICAL" || { echo "files: DIFFERENT"; diff -r "$W/a" "$W/b" | head -20; status=1; }
exit $status
