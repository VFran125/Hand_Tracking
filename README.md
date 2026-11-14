# Hand Volume Control

Use your right hand to change your laptop's volume. Move it up or down in front of the webcam.

## Files

- `main.py` - run this one. It has the camera loop, on-screen overlay and keyboard shortcuts.
- `hand_tracker.py` - MediaPipe hand detection and drawing the 21 landmarks (my original code).
- `gestures.py` - uses right-palm movement to change the volume. Making a fist locks it.
- `volume_control.py` - changes system volume on macOS, Windows and Linux in a background thread.

## Setup

Install the requirements:

```bash
pip install -r requirements.txt
```

You also need MediaPipe's hand model. It's about 8 MB and isn't included in the repo. Download it into the same folder as `main.py`:

```bash
curl -O https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
```

Keep the filename as `hand_landmarker.task`, since that's what `MODEL_PATH` in `main.py` loads. If you put it somewhere else, change `MODEL_PATH` to that path.

Then run it:

```bash
python main.py
```

On macOS, the first run asks to let your terminal or IDE use the camera. Allow it and run the script again.

## Controls

- Move your right hand up to raise the volume, or down to lower it.
- Make a fist to lock the volume so you can move your hand without changing it. Open your hand to resume.
- Space pauses/resumes control.
- + / - changes the sensitivity.
- q quits.

## Changing the settings

These are in `gestures.py`, in `VerticalVolumeGesture(...)`:

- `sensitivity`: the percentage change when your hand moves the full height of the frame. Default is 150.
- `deadzone`: ignores jitter smaller than this. Increase it if the volume creeps while your hand is still.
- `smoothing`: from 0 to 1. A higher value makes movement smoother but takes longer to respond.

## How I made it

I wrote the original hand-tracking script, with MediaPipe landmark detection and the OpenCV video overlay. Then I used Claude (Anthropic) as a coding assistant to turn it into a modular volume controller. This included splitting the code into modules, writing the volume backend for the different operating systems, and designing the gesture logic.

I defined how it should behave, reviewed and tested the code, and tuned it on real hardware. This let me focus on the design decisions and learn some patterns I hadn't used before: threading for non-blocking I/O, debouncing noisy input, and smoothing signals with an exponential moving average.
