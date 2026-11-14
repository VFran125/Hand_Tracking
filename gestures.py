"""Right hand movement and fist detection for the volume control."""

import math

# MediaPipe landmark indices
WRIST = 0
KNUCKLES = (5, 9, 13, 17)          # base of index, middle, ring, pinky
FINGER_TIPS = (8, 12, 16, 20)
FINGER_PIPS = (6, 10, 14, 18)      # middle joint of each finger


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def palm_center(landmarks):
    pts = [landmarks[WRIST]] + [landmarks[i] for i in KNUCKLES]
    return (sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts))


def is_fist(landmarks):
    # Check how many fingertips are tucked in.
    wrist = landmarks[WRIST]
    curled = 0
    for tip, pip in zip(FINGER_TIPS, FINGER_PIPS):
        if _dist(landmarks[tip], wrist) < _dist(landmarks[pip], wrist):
            curled += 1
    return curled >= 3


class VerticalVolumeGesture:
    def __init__(self, sensitivity=150.0, deadzone=0.004, smoothing=0.5,
                 fist_frames=3, hand_label="Right"):
        # More smoothing means less jitter, but a bit more delay.
        self.sensitivity = sensitivity
        self.deadzone = deadzone
        self.smoothing = smoothing
        self.fist_frames = fist_frames
        self.hand_label = hand_label

        self._smoothed_y = None
        self._prev_y = None
        self._fist_count = 0
        self._open_count = 0
        self.locked = False
        self.active = False          # True while the control hand is visible
        self.palm = None             # (x, y) normalised, for drawing

    def reset(self):
        self._smoothed_y = None
        self._prev_y = None
        self.active = False
        self.palm = None

    def update(self, hands):
        """Feed this frame's hands; returns the volume change in % (may be 0)."""
        hand = None
        for h in hands:
            if h.label == self.hand_label:
                hand = h
                break
        if hand is None:
            self.reset()
            return 0.0

        self.active = True
        lm = hand.landmarks
        x, y = palm_center(lm)
        self.palm = (x, y)

        # Wait a few frames before locking or unlocking.
        if is_fist(lm):
            self._fist_count += 1
            self._open_count = 0
        else:
            self._open_count += 1
            self._fist_count = 0
        if self._fist_count >= self.fist_frames:
            self.locked = True
        elif self._open_count >= self.fist_frames:
            if self.locked:
                # re-anchor so the hand's position while locked doesn't count
                self._smoothed_y = self._prev_y = None
            self.locked = False

        # Smooth out the hand movement.
        if self._smoothed_y is None:
            self._smoothed_y = y
        else:
            a = self.smoothing
            self._smoothed_y = a * self._smoothed_y + (1 - a) * y

        if self._prev_y is None or self.locked:
            self._prev_y = self._smoothed_y
            return 0.0

        dy = self._prev_y - self._smoothed_y   # positive when the hand moves UP
        if abs(dy) < self.deadzone:
            return 0.0                          # keep _prev_y so slow drifts still add up
        self._prev_y = self._smoothed_y
        return dy * self.sensitivity
