"""Changes system volume in a background thread so the camera stays smooth."""

import platform
import shutil
import subprocess
import threading


# Volume commands for each OS

class _MacBackend:
    def get(self):
        out = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return int(out) if out.isdigit() else 50

    def set(self, percent):
        subprocess.run(["osascript", "-e", f"set volume output volume {percent}"],
                       check=False)


class _WindowsBackend:
    def __init__(self):
        import comtypes
        comtypes.CoInitialize()  # needed because we run inside a worker thread
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        speakers = AudioUtilities.GetSpeakers()
        if hasattr(speakers, "EndpointVolume"):          # pycaw >= 2024
            self._vol = speakers.EndpointVolume
        else:                                            # older pycaw
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL
            iface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._vol = cast(iface, POINTER(IAudioEndpointVolume))

    def get(self):
        return round(self._vol.GetMasterVolumeLevelScalar() * 100)

    def set(self, percent):
        self._vol.SetMasterVolumeLevelScalar(percent / 100, None)


class _LinuxBackend:
    def __init__(self):
        self._pactl = shutil.which("pactl") is not None

    def get(self):
        import re
        if self._pactl:
            out = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                                 capture_output=True, text=True).stdout
        else:
            out = subprocess.run(["amixer", "get", "Master"],
                                 capture_output=True, text=True).stdout
        m = re.search(r"(\d+)%", out)
        return int(m.group(1)) if m else 50

    def set(self, percent):
        if self._pactl:
            cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"]
        else:
            cmd = ["amixer", "-q", "set", "Master", f"{percent}%"]
        subprocess.run(cmd, check=False)


def _make_backend():
    system = platform.system()
    if system == "Darwin":
        return _MacBackend()
    if system == "Windows":
        return _WindowsBackend()
    return _LinuxBackend()


# Background volume updates

class VolumeController:
    """Non-blocking volume setter. Use `.volume` to read, `.set()` to change."""

    def __init__(self):
        self._target = None
        self._applied = None
        self._ready = threading.Event()
        self._changed = threading.Condition()
        self._running = True
        self._error = None
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)
        if self._error:
            raise RuntimeError(f"Could not access system volume: {self._error}")
        if self._target is None:   # backend slow to answer; assume 50
            self._target = 50

    @property
    def volume(self):
        """Current target volume, 0-100."""
        return self._target

    def set(self, percent):
        percent = int(round(max(0, min(100, percent))))
        with self._changed:
            if percent != self._target:
                self._target = percent
                self._changed.notify()

    def close(self):
        with self._changed:
            self._running = False
            self._changed.notify()
        self._thread.join(timeout=1)

    def _worker(self):
        try:
            backend = _make_backend()
            self._target = self._applied = backend.get()
        except Exception as e:
            self._error = e
            self._ready.set()
            return
        self._ready.set()

        while True:
            with self._changed:
                while self._running and self._target == self._applied:
                    self._changed.wait()
                if not self._running:
                    return
                target = self._target
            backend.set(target)
            self._applied = target
