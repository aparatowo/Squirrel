# m5_audio.py - the microphone and the speaker of the UIFlow 2 firmware (M5.Mic, M5.Speaker)
#
# hw/audio_manager.py records and plays through these two objects; their API (Mic.record / isRecording,
# Speaker.playRaw / isPlaying / tone / setVolume ...) is the audio interface of the app.  Another port provides two
# objects with the same calls (e.g. on top of machine.I2S).


def open():
    """(Mic, Speaker).  Raises when the firmware has none."""
    from M5 import Mic, Speaker
    return Mic, Speaker
