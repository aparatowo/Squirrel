# audio_manager.py — Audio abstraction layer for Squirrel!
#
# Recording strategy: chunked async via Mic.record()
#   - Each chunk = CHUNK_SAMPLES samples = ~0.5s at 8000Hz
#   - Mic.record() is non-blocking; isRecording() signals completion
#   - Main loop calls tick() every iteration; when chunk is ready it is
#     appended to the WAV file and the next chunk starts immediately
#   - This keeps the main loop (keyboard, display) fully responsive
#
# Playback: chunked async via Speaker.playRaw() (returns at once)
#   - The WAV file is streamed in 0.5 s chunks through three rotating buffers,
#     never more than two chunks queued ahead, so the main loop stays free.
#   - Speaker.isPlaying() is only a boolean, so progress is tracked on our own
#     timeline (ticks since the first chunk of a segment was queued).
#   - Pause = stop the speaker and remember the position; seek = restart the
#     stream at another file offset.

import os
import struct
import time
from boot_log import log, trace
from appconfig import cfg
from quiet_hours import quiet_guard
from nuts import AUDIO_SAMPLE_RATE, AUDIO_BITS, AUDIO_STEREO, RECORD_MIN_MS

# Chunk size: ~0.5s at 8000Hz, 16-bit mono = 8000 bytes
# Mic.record() takes a bytearray sized in bytes (not samples)
CHUNK_BYTES = 8000   # 0.5s × 8000Hz × 2 bytes/sample × 1 channel

_WAV_HEADER_BYTES = 44
_PB_BUFFERS = 3          # rotating playback buffers (one is always safe to refill)
_PB_LOOKAHEAD = 2        # chunks queued ahead of the one that is playing
_PB_END_GRACE_MS = 1500  # give up waiting for isPlaying() to drop after the last chunk


def _wav_header(data_bytes: int, sample_rate: int, bits: int, channels: int) -> bytes:
    """Build a 44-byte WAV header for PCM data of known size."""
    byte_rate   = sample_rate * channels * (bits // 8)
    block_align = channels * (bits // 8)
    return struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_bytes,   # ChunkSize
        b'WAVE',
        b'fmt ',
        16,                # Subchunk1Size (PCM)
        1,                 # AudioFormat   (PCM = 1)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        b'data',
        data_bytes,
    )


class AudioManager:
    """Chunked async recorder + WAV file writer, plus WAV playback."""

    def __init__(self):
        self._volume   = cfg.get("AUDIO_DEFAULT_VOL") / 100.0
        self._Mic      = None
        self._Speaker  = None
        # Recording state
        self._rec_file     = None   # open file handle
        self._rec_filepath = None
        self._rec_bufs     = None   # two chunk buffers (double buffering)
        self._rec_order    = []     # buffer indices queued in the mic, oldest first
        self._rec_free     = []     # buffer indices not held by the mic
        self._rec_active   = False  # user requested recording
        self._data_bytes   = 0      # total PCM bytes written so far
        # Playback state
        self._speaker_on   = False
        self._pb_state     = 'idle'   # 'idle' | 'playing' | 'paused'
        self._pb_file      = None
        self._pb_bufs      = None
        self._pb_rate      = 8000
        self._pb_byte_rate = 16000
        self._pb_chunk_ms  = 500
        self._pb_duration_ms = 0
        self._pb_base_ms   = 0      # position at the start of the current timeline segment
        self._pb_t0        = None   # ticks when the segment's first chunk was queued
        self._pb_seg_chunks = 0     # chunks queued in the current segment
        self._pb_seq       = 0      # global chunk counter (selects the buffer)
        self._pb_pending   = None   # buffer index read from file but not yet accepted
        self._pb_eof       = False
        self._beep_buf     = None   # signal being played (must stay referenced until it ends) - kept as a cache
        self._beep_pattern = None   # which pattern _beep_buf holds: repeats of a notification do not rebuild it
        self._init()

    def _init(self):
        try:
            from M5 import Mic, Speaker
            self._Mic     = Mic
            self._Speaker = Speaker
            # Both stay stopped until needed: the UIFlow reference example stops
            # the speaker before the mic starts and restarts it after the mic ends.
            log("[AUDIO] Mic and Speaker references ready (both stopped)")
        except Exception as e:
            print(f"[AUDIO] Init failed: {e}")

    # ------------------------------------------------------------------
    # Recording — call tick() from the main loop every iteration
    # ------------------------------------------------------------------

    def start_recording(self, filepath: str) -> bool:
        """Open the WAV file and queue the first two chunks (gapless double buffering)."""
        if not self._Mic:
            print("[AUDIO] No Mic available")
            return False
        self.stop_playback()
        try:
            try:
                self._Speaker.end()
                self._speaker_on = False
                trace("[AUDIO] Speaker.end() before recording")
            except Exception as e:
                log(f"[AUDIO] Speaker.end() failed: {e}")
            # Built-in input multiplier (Mic.config); 0 leaves the firmware default.
            # Read at the start of every take, so a change applies to the next recording.
            mag = cfg.get("AUDIO_MIC_MAGNIFICATION")
            if mag:
                try:
                    self._Mic.config(magnification=mag)
                except Exception as e:
                    log(f"[AUDIO] Mic.config(magnification={mag}) failed: {e}")
            trace("[AUDIO] Mic.begin()")
            self._Mic.begin()
            trace("[AUDIO] Mic.begin() returned")
            try:
                trace(f"[AUDIO] Mic magnification in effect: {self._Mic.config('magnification')}")
            except Exception as e:
                log(f"[AUDIO] Cannot read Mic magnification: {e}")
            # Write placeholder header — we'll patch it on stop
            self._rec_file = open(filepath, 'wb')
            self._rec_file.write(_wav_header(0, 8000, AUDIO_BITS,
                                             2 if AUDIO_STEREO else 1))
            self._rec_filepath = filepath
            self._data_bytes   = 0
            self._rec_active   = True
            self._rec_bufs     = [bytearray(CHUNK_BYTES), bytearray(CHUNK_BYTES)]
            self._rec_order    = []
            self._rec_free     = [0, 1]
            self._recording_tick()          # queues both buffers
            print(f"[AUDIO] Recording started: {filepath}")
            return True
        except Exception as e:
            print(f"[AUDIO] start_recording error: {e}")
            self._cleanup_rec()
            return False

    def tick(self):
        """Call once per main-loop iteration: drives recording and playback."""
        if self._rec_active:
            self._recording_tick()
        if self._pb_state == 'playing':
            self._playback_tick()

    def _write_finished_chunks(self, pending):
        """Write out the queued chunks that the mic no longer holds."""
        while len(self._rec_order) > pending:
            idx = self._rec_order.pop(0)
            self._rec_file.write(self._rec_bufs[idx])
            self._data_bytes += CHUNK_BYTES
            self._rec_free.append(idx)

    def _recording_tick(self):
        """Keep two chunks queued in the mic so no audio falls between chunks.

        Mic.isRecording() reports how many chunks the mic still holds (0, 1 or 2).
        Chunks we queued beyond that count are finished and are written to the
        file.  record() is only called while fewer than two chunks are pending,
        because it may block when the mic's queue is full.
        """
        try:
            pending = int(self._Mic.isRecording())
        except Exception:
            pending = 0
        try:
            self._write_finished_chunks(pending)
        except Exception as e:
            log(f"[AUDIO] Write error: {e}")
            self.stop_recording()
            return
        while pending < 2 and self._rec_free:
            idx = self._rec_free.pop(0)
            try:
                self._Mic.record(self._rec_bufs[idx], 8000, AUDIO_STEREO)
            except Exception as e:
                log(f"[AUDIO] record() failed: {e}")
                self.stop_recording()
                return
            self._rec_order.append(idx)
            pending += 1

    def stop_recording(self) -> bool:
        """Stop recording, patch WAV header with real size, close file.

        Returns True when the take was kept.  One shorter than RECORD_MIN_MS is removed (an accidental press)."""
        if not self._rec_active:
            return False
        self._rec_active = False

        # Keep every chunk the mic has already finished; the one in progress is dropped.
        try:
            pending = int(self._Mic.isRecording()) if self._Mic else 0
            self._write_finished_chunks(pending)
        except Exception as e:
            log(f"[AUDIO] Final write error: {e}")

        try:
            if self._Mic:
                trace("[AUDIO] Mic.end()")
                self._Mic.end()
        except Exception:
            pass

        # Patch WAV header with real data size
        try:
            self._rec_file.seek(0)
            self._rec_file.write(_wav_header(
                self._data_bytes, 8000, AUDIO_BITS,
                2 if AUDIO_STEREO else 1
            ))
        except Exception as e:
            print(f"[AUDIO] Header patch error: {e}")

        path = self._rec_filepath
        self._cleanup_rec()
        length_ms = self._data_bytes * 1000 // (8000 * (AUDIO_BITS // 8) * (2 if AUDIO_STEREO else 1))
        if length_ms < RECORD_MIN_MS:
            try:
                os.remove(path)
                log(f"[AUDIO] Recording too short ({length_ms} ms) - not saved")
            except OSError as e:
                log(f"[AUDIO] Could not remove the too short {path}: {e}")
            return False
        log(f"[AUDIO] Recording saved ({self._data_bytes} bytes PCM)")
        return True

    def cancel_recording(self):
        """Stop the current take and throw it away (the file is removed).

        Does nothing when no recording is running, so an earlier, saved file is safe.
        """
        if not self._rec_active:
            return
        path = self._rec_filepath
        if not self.stop_recording():
            return                                # too short: already removed
        try:
            os.remove(path)
            log(f"[AUDIO] Recording discarded: {path}")
        except OSError as e:
            log(f"[AUDIO] Could not remove {path}: {e}")

    def is_recording(self) -> bool:
        return self._rec_active

    def _cleanup_rec(self):
        try:
            if self._rec_file:
                self._rec_file.close()
        except Exception:
            pass
        self._rec_file     = None
        self._rec_bufs     = None
        self._rec_order    = []
        self._rec_free     = []
        self._rec_active   = False

    # ------------------------------------------------------------------
    # Playback — streamed from the main loop via tick()
    # ------------------------------------------------------------------

    def start_playback(self, filepath: str) -> bool:
        """Start streaming a WAV file from the beginning.  Returns True on success."""
        self.stop_playback()
        if not self._Speaker:
            return False
        f = None
        try:
            f = open(filepath, 'rb')
            header = f.read(_WAV_HEADER_BYTES)
            if len(header) < _WAV_HEADER_BYTES:
                raise ValueError("file too short")
            f.seek(0, 2)
            size = f.tell()
            rate = struct.unpack('<I', header[24:28])[0]
            byte_rate = struct.unpack('<I', header[28:32])[0]
            if rate <= 0 or byte_rate <= 0:
                raise ValueError("bad WAV header")

            self._pb_file = f
            self._pb_rate = rate
            self._pb_byte_rate = byte_rate
            self._pb_duration_ms = max(0, size - _WAV_HEADER_BYTES) * 1000 // byte_rate
            self._pb_chunk_ms = max(1, CHUNK_BYTES * 1000 // byte_rate)
            self._pb_bufs = [bytearray(CHUNK_BYTES) for _ in range(_PB_BUFFERS)]
            self._pb_seq = 0
            self._pb_restart(0)
            trace(f"[AUDIO] Streaming playback: {filepath} ({self._pb_duration_ms} ms)")
            return True
        except Exception as e:
            log(f"[AUDIO] Cannot play {filepath}: {e}")
            if self._pb_file is None and f is not None:
                try:
                    f.close()
                except Exception:
                    pass
            self.stop_playback()
            return False

    def pause_playback(self):
        if self._pb_state != 'playing':
            return
        pos = self.position_ms()
        self._speaker_halt()
        self._pb_base_ms = pos
        self._pb_t0 = None
        self._pb_seg_chunks = 0
        self._pb_pending = None
        self._pb_state = 'paused'

    def resume_playback(self):
        if self._pb_state == 'paused':
            self._pb_restart(self._pb_base_ms)

    def seek(self, delta_ms: int):
        """Jump delta_ms (+/-) from the current position, clamped to the file."""
        if self._pb_state not in ('playing', 'paused'):
            return
        pos = max(0, min(self._pb_duration_ms, self.position_ms() + delta_ms))
        if self._pb_state == 'playing':
            self._speaker_halt()
            self._pb_restart(pos)
        else:
            self._pb_base_ms = pos

    def stop_playback(self):
        if self._pb_state == 'playing':
            self._speaker_halt()
        self._pb_state = 'idle'
        self._pb_release()

    def playback_state(self) -> str:
        return self._pb_state

    def is_playing(self) -> bool:
        return self._pb_state == 'playing'

    def position_ms(self) -> int:
        if self._pb_state == 'playing' and self._pb_t0 is not None:
            elapsed = time.ticks_diff(time.ticks_ms(), self._pb_t0)
            elapsed = min(elapsed, self._pb_seg_chunks * self._pb_chunk_ms)
            return min(self._pb_duration_ms, self._pb_base_ms + elapsed)
        return self._pb_base_ms

    def duration_ms(self) -> int:
        return self._pb_duration_ms

    # -- playback internals --

    def _speaker_start(self):
        if not self._speaker_on:
            trace("[AUDIO] Speaker.begin() for playback")
            self._Speaker.begin()
            self._speaker_on = True
        self._Speaker.setVolumePercentage(self._volume)

    @property
    def speaker_on(self):
        """True once the speaker has been started (it stays on after a signal, see beep())."""
        return self._speaker_on

    def set_speaker(self, on):
        """Start or end the speaker now - used by the LED tests to see whether a running speaker disturbs the LED.
        Does nothing while recording or playing back."""
        if self._rec_active or self._pb_state != 'idle' or not self._Speaker or on == self._speaker_on:
            return self._speaker_on
        try:
            if on:
                self._Speaker.begin()
            else:
                self._Speaker.end()
            self._speaker_on = on
            log(f"[AUDIO] Speaker {'begin' if on else 'end'} (LED test)")
        except Exception as e:
            log(f"[AUDIO] Speaker switch failed: {e}")
        return self._speaker_on

    def _speaker_halt(self):
        """Silence the speaker and drop anything still queued."""
        try:
            self._Speaker.stop()
        except Exception as e:
            log(f"[AUDIO] Speaker.stop() failed ({e}); using end()")
            try:
                self._Speaker.end()
                self._speaker_on = False
            except Exception:
                pass

    def _pb_restart(self, pos_ms: int):
        """(Re)start streaming at pos_ms."""
        self._speaker_start()
        pos_ms = max(0, min(self._pb_duration_ms, pos_ms))
        offset = (pos_ms * self._pb_byte_rate // 1000) & ~1     # keep sample alignment
        self._pb_file.seek(_WAV_HEADER_BYTES + offset)
        self._pb_base_ms = pos_ms
        self._pb_t0 = None
        self._pb_seg_chunks = 0
        self._pb_pending = None
        self._pb_eof = False
        self._pb_state = 'playing'

    def _pb_release(self):
        try:
            if self._pb_file:
                self._pb_file.close()
        except Exception:
            pass
        self._pb_file = None
        self._pb_bufs = None
        self._pb_pending = None
        self._pb_t0 = None
        self._pb_seg_chunks = 0

    def _pb_finish(self):
        """Playback reached the end of the file."""
        self._pb_state = 'idle'
        self._pb_base_ms = self._pb_duration_ms
        self._pb_release()
        trace("[AUDIO] Playback finished")

    def _playback_tick(self):
        now = time.ticks_ms()
        chunk_ms = self._pb_chunk_ms

        # How many queued chunks have finished, by our own timeline.
        completed = 0
        if self._pb_t0 is not None:
            completed = time.ticks_diff(now, self._pb_t0) // chunk_ms
            if completed > self._pb_seg_chunks:
                completed = self._pb_seg_chunks
            if completed >= self._pb_seg_chunks and not self._pb_eof:
                # Queue ran dry (main loop stalled): open a new timeline segment.
                self._pb_base_ms += self._pb_seg_chunks * chunk_ms
                self._pb_seg_chunks = 0
                self._pb_t0 = None
                completed = 0

        # Keep up to _PB_LOOKAHEAD chunks queued.
        fed = 0
        while (not self._pb_eof and fed < _PB_LOOKAHEAD
               and self._pb_seg_chunks - completed < _PB_LOOKAHEAD):
            idx = self._pb_seq % _PB_BUFFERS
            buf = self._pb_bufs[idx]
            if self._pb_pending is None:
                n = self._pb_file.readinto(buf)
                if not n:
                    self._pb_eof = True
                    break
                if n < CHUNK_BYTES:
                    buf[n:] = bytes(CHUNK_BYTES - n)     # pad the last chunk with silence
                self._pb_pending = idx
            try:
                ok = self._Speaker.playRaw(buf, self._pb_rate)
            except Exception as e:
                log(f"[AUDIO] playRaw failed: {e}")
                self._pb_finish()
                return
            if ok is False:
                break                # speaker queue full: keep the chunk, retry next tick
            self._pb_pending = None
            self._pb_seq += 1
            self._pb_seg_chunks += 1
            fed += 1
            if self._pb_t0 is None:
                self._pb_t0 = time.ticks_ms()

        if self._pb_eof and self._pb_pending is None:
            self._pb_maybe_finish(now)

    def _pb_maybe_finish(self, now):
        """After the last chunk was queued: finish once it has played out."""
        if self._pb_t0 is None or self._pb_seg_chunks == 0:
            self._pb_finish()
            return
        elapsed = time.ticks_diff(now, self._pb_t0)
        due = self._pb_seg_chunks * self._pb_chunk_ms
        if elapsed >= due:
            try:
                still = self._Speaker.isPlaying()
            except Exception:
                still = False
            if not still or elapsed >= due + _PB_END_GRACE_MS:
                self._pb_finish()

    @quiet_guard("sound")
    def beep(self, pattern, volume=None) -> bool:
        """Play a short signal (see sound.py) at the notification volume (or `volume` percent).

        Skipped during the silent hours of the sound (Settings -> Silent mode), unless called with force=True.

        Returns False, and stays silent, while a recording runs (it must not be disturbed, and the
        signal would be in it), while a recording is being played, and when the sound is switched off.
        The speaker is left on afterwards: switching it on and off around every signal is what
        makes the keyboard controller report errors.
        """
        if self._rec_active or self._pb_state != 'idle' or not cfg.get("NOTIFY_SOUND"):
            return False
        if not self._Speaker:
            return False
        try:
            import sound
            if self._beep_buf is not None and self._beep_pattern == pattern:
                buf = self._beep_buf
            else:
                buf = sound.build(pattern)
                self._beep_pattern = pattern
            if not self._speaker_on:
                trace("[AUDIO] Speaker.begin() for a signal")
                self._Speaker.begin()
                self._speaker_on = True
            self._Speaker.setVolumePercentage((cfg.get("NOTIFY_VOLUME") if volume is None else volume) / 100.0)
            self._beep_buf = buf
            self._Speaker.playRaw(buf, sound.RATE)
            return True
        except Exception as e:
            log(f"[AUDIO] Signal failed: {e}")
            return False

    def set_volume(self, pct: float):
        self._volume = max(0.0, min(1.0, pct))
        if self._Speaker:
            try:
                self._Speaker.setVolumePercentage(self._volume)
            except Exception as e:
                print(f"[AUDIO] Volume error: {e}")

    def get_volume(self) -> float:
        return self._volume

    def volume_pct_int(self) -> int:
        return int(self._volume * 100)
