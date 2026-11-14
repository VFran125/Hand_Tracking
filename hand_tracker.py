"""MediaPipe hand tracking and drawing."""

import time
from dataclasses import dataclass

import cv2 as cv
import mediapipe as mp
import numpy as np

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode
mp_hands = mp.tasks.vision.HandLandmarksConnections
mp_drawing = mp.tasks.vision.drawing_utils
mp_drawing_styles = mp.tasks.vision.drawing_styles

MARGIN = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)


@dataclass
class Hand:
    label: str
    score: float
    landmarks: list


class HandTracker:
    def __init__(self, model_path="hand_landmarker.task", num_hands=2):
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.VIDEO,
            num_hands=num_hands,
        )
        self._landmarker = HandLandmarker.create_from_options(options)
        self._last_ts = -1
        self.last_result = None

    def process(self, rgb_frame):
        """Run detection on an RGB frame and return a list of Hand objects."""
        # VIDEO mode requires strictly increasing timestamps.
        ts = int(time.monotonic() * 1000)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts

        mp_frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_frame, ts)
        self.last_result = result

        hands = []
        for landmarks, handedness in zip(result.hand_landmarks, result.handedness):
            top = handedness[0]
            hands.append(Hand(top.category_name, top.score, landmarks))
        return hands

    def draw(self, rgb_frame):
        """Draw the hands and their labels."""
        annotated = np.copy(rgb_frame)
        result = self.last_result
        if result is None or not result.hand_landmarks:
            return annotated

        height, width, _ = annotated.shape
        for hand_landmarks, handedness in zip(result.hand_landmarks, result.handedness):
            mp_drawing.draw_landmarks(
                annotated,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style(),
            )
            text_x = int(min(lm.x for lm in hand_landmarks) * width)
            text_y = int(min(lm.y for lm in hand_landmarks) * height) - MARGIN
            cv.putText(annotated, handedness[0].category_name, (text_x, text_y),
                       cv.FONT_HERSHEY_DUPLEX, FONT_SIZE, HANDEDNESS_TEXT_COLOR,
                       FONT_THICKNESS, cv.LINE_AA)
        return annotated

    def close(self):
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
