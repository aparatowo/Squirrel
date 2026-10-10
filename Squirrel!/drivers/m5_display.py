# m5_display.py - the display of the UIFlow 2 firmware (M5.Lcd)
#
# gfx.py wraps whatever `lcd` the port's display driver gives (port_config.DISPLAY_DRIVER); the rest of the app draws
# through gfx.Lcd only.  The API the app uses is M5.Lcd's (fillRect, drawString, setTextColor, textWidth, ...):
# a display driver of another port provides the same calls.
from M5 import Lcd as lcd
