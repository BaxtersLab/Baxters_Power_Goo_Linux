#!/usr/bin/env python3
"""
Sound Manager — Baxters Power Goo
Plays action sounds using whichever audio backend is available.
Backends tried in order: simpleaudio → pyaudio → (silent fallback).
"""

import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Probe for available backend at import time
_BACKEND: Optional[str] = None

try:
    import simpleaudio  # type: ignore
    _BACKEND = "simpleaudio"
except ImportError:
    pass

if _BACKEND is None:
    try:
        import pyaudio  # type: ignore
        import wave
        _BACKEND = "pyaudio"
    except ImportError:
        pass

if _BACKEND is None:
    logger.debug("No audio backend available — sound playback disabled.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class SoundManager:
    """
    Play short WAV sound files asynchronously.

    If no audio backend is installed the manager silently does nothing,
    so the rest of the application continues to work.
    """

    # Directory containing numbered action-sound sub-folders
    SOUNDS_DIR = Path(__file__).parent / "sounds"

    def __init__(self) -> None:
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def play_action_sound(self, sound_number: int = 1) -> None:
        """
        Play *action_sound_NN* where NN is *sound_number* (1–10).
        Plays on a background thread so the UI is never blocked.
        """
        if _BACKEND is None:
            return
        wav_path = self._resolve_wav(sound_number)
        if wav_path is None:
            return
        threading.Thread(
            target=self._play_wav,
            args=(wav_path,),
            daemon=True,
        ).start()

    def play_file(self, path: Path) -> None:
        """Play an arbitrary WAV file asynchronously."""
        if _BACKEND is None:
            return
        threading.Thread(
            target=self._play_wav,
            args=(path,),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_wav(self, number: int) -> Optional[Path]:
        folder_name = f"action_sound_{number:02d}"
        folder = self.SOUNDS_DIR / folder_name
        if not folder.is_dir():
            return None
        for wav in folder.glob("*.wav"):
            return wav
        return None

    def _play_wav(self, path: Path) -> None:
        with self._lock:
            try:
                if _BACKEND == "simpleaudio":
                    wave_obj = simpleaudio.WaveObject.from_wave_file(str(path))
                    play_obj = wave_obj.play()
                    play_obj.wait_done()
                elif _BACKEND == "pyaudio":
                    self._play_pyaudio(path)
            except Exception as exc:
                logger.debug("Sound playback failed: %s", exc)

    @staticmethod
    def _play_pyaudio(path: Path) -> None:
        import wave as _wave
        chunk = 1024
        with _wave.open(str(path), "rb") as wf:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pa.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
            )
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
            stream.stop_stream()
            stream.close()
            pa.terminate()
