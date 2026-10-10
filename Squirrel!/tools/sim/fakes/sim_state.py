# sim_state.py - the shared state of the simulated device (clock, key FIFO, trace, file system root)

ms = 0                    # ticks_ms(): advanced only by sleeps and by the runner
wall_s = 1791622800       # time() at ms = 0: 2026-10-10 09:00:00 (as if the clock had been set)
root = "."                # host folder that stands for the device's "/" (/sd, /flash, /system)
keys = []                 # TCA8418 key-event FIFO (bit 7 = pressed)
trace = []                # every display call, in order
button0 = 1               # G0 level (1 = released)
