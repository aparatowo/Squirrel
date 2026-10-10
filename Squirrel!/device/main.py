# /flash/main.py - starts Squirrel! (the app itself is frozen into the firmware; see BUILD.md)
import sys
sys.path.append("/flash/apps/Squirrel")      # only a fallback: the frozen squirrel_boot is found first
import squirrel_boot
squirrel_boot.run()
