#!/bin/bash
# twatch_phase0.sh - BEFORE anything is written to the T-Watch: what chip and flash it has, and a full copy of its flash.
#
#   tools/hwtest/twatch_phase0.sh /dev/ttyACM1 [ESP-IDF folder]
#
# Reads only.  The copy (.build/hwtest/twatch-backup-<MAC>-<time>.bin, with its MD5) restores the watch exactly as it is
# now (its factory firmware):  esptool.py --chip esp32 -p PORT -b 921600 write_flash 0x0 <that file>
PORT=${1:?usage: twatch_phase0.sh PORT [ESP-IDF folder]}
IDF=${2:-$HOME/esp-idf-v5.4.2}
. "$IDF/export.sh" > /dev/null 2>&1 || { echo "cannot load ESP-IDF from $IDF (export.sh needs bash)"; exit 1; }
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
OUT="$HERE/../../.build/hwtest"
mkdir -p "$OUT"
ESPTOOL="python -m esptool --chip esp32 -p $PORT -b 921600"

echo "== chip"
$ESPTOOL chip_id | tee "$OUT/twatch-chip.txt" | grep -E "Chip is|Features|Crystal|MAC"
echo "== flash"
$ESPTOOL flash_id | tee -a "$OUT/twatch-chip.txt" | grep -E "Manufacturer|Device|Detected flash size"
SIZE=$(grep -o "Detected flash size: [0-9]*MB" "$OUT/twatch-chip.txt" | grep -o "[0-9]*" | head -1)
MAC=$(grep -o "MAC: [0-9a-f:]*" "$OUT/twatch-chip.txt" | head -1 | cut -c6- | tr -d ':')
[ -n "$SIZE" ] || { echo "flash size not detected - stopping"; exit 1; }
FILE="$OUT/twatch-backup-$MAC-$(date +%Y%m%d-%H%M).bin"
echo "== reading all $SIZE MB into $FILE (a few minutes)"
$ESPTOOL read_flash 0 $((SIZE * 1024 * 1024)) "$FILE"
md5sum "$FILE" | tee "$FILE.md5"
echo "done. Keep $FILE somewhere safe (it is under .build/, which git ignores)."
