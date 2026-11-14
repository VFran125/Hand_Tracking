"""Move your right hand up/down to change volume. Fist locks it.
q quits, space pauses, +/- changes sensitivity."""

import cv2 as cv

from gestures import VerticalVolumeGesture
from hand_tracker import HandTracker
from volume_control import VolumeController

MODEL_PATH = "hand_landmarker.task"
CAMERA_INDEX = 0
WINDOW_NAME = "Hand Volume Control"

GREEN = (54, 205, 88)     # BGR
ORANGE = (0, 165, 255)
GREY = (160, 160, 160)
WHITE = (255, 255, 255)


def draw_volume_bar(img, volume, color):
    h, w, _ = img.shape
    x0, x1 = w - 60, w - 30
    y0, y1 = 60, h - 60
    cv.rectangle(img, (x0, y0), (x1, y1), WHITE, 2)
    fill_top = int(y1 - (y1 - y0) * volume / 100)
    cv.rectangle(img, (x0 + 3, fill_top), (x1 - 3, y1 - 3), color, cv.FILLED)
    cv.putText(img, f"{volume}%", (x0 - 20, y1 + 35), cv.FONT_HERSHEY_DUPLEX,
               0.8, WHITE, 1, cv.LINE_AA)


def draw_status(img, gesture, paused, sensitivity):
    if paused:
        text, color = "PAUSED (space to resume)", GREY
    elif not gesture.active:
        text, color = "Show your right hand", GREY
    elif gesture.locked:
        text, color = "LOCKED - open hand to resume", ORANGE
    else:
        text, color = "Move right hand up / down", GREEN
    cv.putText(img, text, (20, 40), cv.FONT_HERSHEY_DUPLEX, 0.8, color, 1, cv.LINE_AA)
    cv.putText(img, f"sensitivity {sensitivity:.0f}  (+/-)   q = quit", (20, 70),
               cv.FONT_HERSHEY_DUPLEX, 0.5, WHITE, 1, cv.LINE_AA)

    if gesture.palm is not None:
        h, w, _ = img.shape
        cx, cy = int(gesture.palm[0] * w), int(gesture.palm[1] * h)
        cv.circle(img, (cx, cy), 12, color, 3)
    return color


def main():
    volume = VolumeController()
    gesture = VerticalVolumeGesture()
    paused = False
    # Keep the small volume changes between frames.
    level = float(volume.volume)

    cap = cv.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    try:
        with HandTracker(MODEL_PATH, num_hands=2) as tracker:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Can't receive frame (stream end?). Exiting ...")
                    break

                # Flip it so the hand controls feel natural.
                frame = cv.flip(frame, 1)
                rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

                hands = tracker.process(rgb)
                change = gesture.update(hands)

                if not paused and change:
                    level = max(0.0, min(100.0, level + change))
                    volume.set(level)

                out = cv.cvtColor(tracker.draw(rgb), cv.COLOR_RGB2BGR)
                color = draw_status(out, gesture, paused, gesture.sensitivity)
                draw_volume_bar(out, volume.volume, color)
                cv.imshow(WINDOW_NAME, out)

                key = cv.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord(" "):
                    paused = not paused
                    level = float(volume.volume)
                elif key in (ord("+"), ord("=")):
                    gesture.sensitivity = min(500, gesture.sensitivity + 25)
                elif key in (ord("-"), ord("_")):
                    gesture.sensitivity = max(25, gesture.sensitivity - 25)
    finally:
        cap.release()
        cv.destroyAllWindows()
        volume.close()


if __name__ == "__main__":
    main()
