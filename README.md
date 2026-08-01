# GestureTeach AI - Touchless Windows Controller

Control an entire Windows laptop — mouse, clicks, scrolling, PowerPoint slides,
volume, brightness, File Explorer, and app switching — using only hand
gestures seen through a webcam. Built for teachers presenting on a projector
who want to walk around the room instead of standing at the laptop.

---

## 1. Project Structure

```
GestureTeach_AI_Touchless_Windows_Controller/
│
├── main.py               # GUI + main application loop (run this file)
├── gesture_detector.py   # MediaPipe hand tracking + gesture classification
├── windows_control.py    # Mouse/keyboard/volume/brightness system actions
├── config.py              # All tunable settings in one place
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── assets/                # (empty - reserved for icons/images if you add any)
```

## 2. Requirements

- **Windows 10 or 11** (the volume/brightness/keyboard integrations are Windows-specific)
- **Python 3.9, 3.10, or 3.11** (MediaPipe does not yet support every newer Python
  release — if `pip install mediapipe` fails on your Python version, install
  Python 3.10 from python.org and use that instead)
- A working **webcam**
- Recommended: run from an **administrator terminal** (the `keyboard` library
  needs elevated privileges to reliably send global shortcuts like Alt+Tab on
  some Windows configurations)

## 3. Installation

Open PowerPoint/Command Prompt/Terminal in the project folder and run:

```bash
# 1. (Recommended) create a virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install all dependencies
pip install -r requirements.txt
```

If `mediapipe` fails to install, double-check your Python version:

```bash
python --version
```

MediaPipe wheels are published for specific Python versions — 3.9–3.11 is the
safest range as of this writing.

## 4. Camera Setup

1. Make sure no other application (Zoom, Teams, another Python script, etc.)
   is currently using the webcam.
2. Plug in / enable your webcam before starting the app.
3. If you have more than one camera (e.g. a laptop camera + a USB webcam),
   open `config.py` and change:
   ```python
   CAMERA_INDEX = 0   # try 1, 2, etc. if the wrong camera opens
   ```
4. For the best tracking accuracy, use good, even lighting facing your hand
   (avoid having a bright window directly behind you).

## 5. Running the Application

```bash
python main.py
```

A window titled **"GestureTeach AI - Touchless Windows Controller"** will open,
showing:
- A live webcam preview with your hand skeleton drawn on it
- The current FPS and detected gesture name (also shown in the sidebar)
- An **Enable / Disable** button to instantly pause all system control
- A small reminder that **ESC** is the emergency exit key

Stand (or sit) so your hand is clearly visible in the frame, and try the
gestures below.

## 6. Gesture Reference

| Gesture | Hand Shape | Action |
|---|---|---|
| Move cursor | Index finger only, pointing | Moves the mouse cursor |
| Left click | Thumb + index finger pinched together | Left mouse click |
| Right click | Thumb + middle finger pinched together | Right mouse click |
| Scroll | Index + middle fingers extended, **move hand up/down** | Scrolls the active window |
| Alt+Tab switch | Index + middle fingers extended, **held still** | Switches applications |
| Swipe right | Move an open hand quickly to the right | Next PowerPoint slide |
| Swipe left | Move an open hand quickly to the left | Previous PowerPoint slide |
| Pause recognition | Open palm, all 5 fingers spread | Ignores all other gestures |
| Lock cursor | Closed fist | Toggles the mouse cursor locked/unlocked |
| Open File Explorer | Index + middle + ring fingers extended | Opens Windows File Explorer (Win+E) |
| Volume control | Thumb + index + middle extended, **move hand up/down** | Raises/lowers system volume |
| Brightness control | Four fingers extended, thumb folded, **move hand up/down** | Raises/lowers screen brightness |

> **Design note on overlapping gestures:** the original spec assigns the exact
> same hand shape (index + middle finger extended) to two different actions —
> "scroll" and "Alt+Tab". Since a still photo of that hand shape can't tell the
> two apart, the app uses **movement** to decide: moving the fingers up/down
> scrolls, holding them still for a moment triggers Alt+Tab. This is
> implemented in `main.py` inside `_handle_two_finger_gesture()`. The
> "brightness" gesture (four fingers, thumb folded) was added so the
> `screen-brightness-control` library required by the brief has a working
> gesture attached to it — feel free to remap any of these in
> `gesture_detector.py` / `config.py` to your preference.

## 7. Presentation Mode Shortcuts

These are available as controller methods (`windows_control.py`) already wired
into the swipe gestures, and can be bound to any additional gesture you like:

- `next_slide()` — Right Arrow
- `previous_slide()` — Left Arrow
- `start_slideshow()` — F5 (start from the beginning)
- `exit_slideshow()` — Esc

## 8. Safety Features

- **Gesture cooldown timers** on every discrete action (clicks, slide changes,
  Alt+Tab, File Explorer, cursor lock) so a held gesture doesn't fire dozens
  of times per second. Tune these in `config.py`.
- **Static-gesture hold delay** so a hand shape has to be steady for a brief
  moment before it's trusted, filtering out momentary MediaPipe misreads.
- **Emergency exit key (ESC)** — works globally, even if the app window isn't
  focused, via a background keyboard listener.
- **PyAutoGUI fail-safe** — dragging the real mouse cursor into a screen
  corner immediately aborts any in-progress automated mouse movement.
- **Enable/Disable button** — instantly pauses all gesture-to-action routing
  without closing the app or the webcam.
- **Open-palm pause gesture** — a dedicated, easy-to-make gesture that
  suppresses every other action, useful when you just want to talk with your
  hands without triggering anything.

## 9. Performance Tuning (for 8GB RAM / low-end laptops)

**The app now tunes itself automatically** — you shouldn't need to hand-edit
settings for most laptops. Here's what it does on its own:

- **Auto Quality (`AUTO_PERFORMANCE = True`)** — the app measures its own
  real FPS while running and automatically shrinks or grows the resolution
  MediaPipe analyses each frame to hit a smooth target. A fast machine
  settles at full quality; an 8GB laptop automatically settles lower; if
  something else on your PC starts using more CPU mid-session, it adjusts
  again without a restart. You'll see the current level in the sidebar,
  e.g. `Status: Running (auto quality: 70%)`. This does **not** shrink the
  actual webcam preview you see — only the copy MediaPipe analyses
  internally, so visual quality in the window stays the same.
- **Adaptive mouse responsiveness** — the cursor now blends between a fast,
  low-lag response when your hand moves quickly and a steadier, jitter-free
  hold when your hand is nearly still, instead of one fixed smoothing value
  that had to compromise between the two.
- **Threaded camera capture** — reading frames happens on a background
  thread, so a slow/blocking camera read never freezes the GUI.

If you still want to tune things by hand (e.g. to force a lighter/heavier
setting), these remain available in `config.py`:

- **`FRAME_WIDTH` / `FRAME_HEIGHT`** — default 640x360. Drop to 480x270 for
  very weak hardware.
- **`MODEL_COMPLEXITY`** — `0` (fast) by default; `1` is more accurate but slower.
- **`TARGET_FPS`** — the FPS the auto-quality system aims for. Lower it
  (e.g. to `15`) on a very weak machine.
- **`MIN_PROCESS_SCALE` / `MAX_PROCESS_SCALE` / `PROCESS_SCALE_STEP`** —
  controls how far and how fast auto-quality is allowed to scale down/up.
- **`AUTO_PERFORMANCE = False`** — turns auto-tuning off entirely if you'd
  rather set a fixed quality yourself (the app will just use `MAX_PROCESS_SCALE`).
- **`MOUSE_SMOOTHING_FAST` / `MOUSE_SMOOTHING_SLOW` / `MOUSE_VELOCITY_THRESHOLD`**
  — controls how snappy vs. steady the adaptive cursor feels.
- **`DRAW_LANDMARKS`** — set to `False` to skip drawing the hand skeleton overlay.
- **`DRAW_ACTIVE_ZONE`** — set to `False` to skip drawing the mapping rectangle.
- **`FINGER_STATE_SMOOTHING`** — frames "voted" together per finger state
  (default `3`). Higher = steadier gestures, slightly more delay.

If it's still sluggish, also try:
- Closing other browser tabs / apps in the background (8GB RAM fills up fast
  with Chrome tabs open).
- Running the app in the virtual environment described above rather than a
  base install with lots of unrelated packages.

## 9b. Why Only the Mouse Gesture Felt Reliable Before

Pointing only depends on ONE finger's state (index up), so it stayed steady
even with some frame noise. Gestures like the fist, three-fingers, or pinch
shapes depend on several finger states agreeing at once, so any noisy frame
(more likely on a struggling CPU) could flip one of them and break the whole
gesture. Two changes address this directly:

1. **Finger-state voting** (`FINGER_STATE_SMOOTHING`) — each finger's
   up/down state is now decided by a short majority vote across recent
   frames instead of trusting a single frame.
2. **More robust thumb detection** — the thumb now uses a distance
   comparison to a stable palm landmark instead of a check that could be
   thrown off by hand angle, which makes pinch-based gestures (left/right
   click, volume) noticeably steadier.

## 10. Troubleshooting

**"Could not open webcam" / black preview window**
- Close any other app using the camera (Zoom, Teams, Camera app, OBS, etc.)
- Try changing `CAMERA_INDEX` in `config.py` to `1` or `2`.
- Check Windows Settings → Privacy & Security → Camera → allow desktop apps
  to access the camera.

**`pip install mediapipe` fails**
- You're likely on a Python version MediaPipe hasn't published wheels for
  yet. Install Python 3.10 or 3.11 and recreate your virtual environment.

**Volume/brightness gestures don't do anything**
- Run the terminal / IDE as **Administrator**.
- Some external monitors don't expose brightness control to Windows —
  `screen-brightness-control` will fail silently in that case (this is
  expected behaviour, not a bug).

**Alt+Tab / Win+E shortcuts don't fire**
- The `keyboard` library needs administrator privileges on some Windows
  setups to send global shortcuts. Re-run your terminal as Administrator.

**Cursor is jittery / jumps around**
- Improve lighting on your hand.
- Increase `MOUSE_SMOOTHING` in `config.py` (higher = smoother, slightly more lag).
- Increase `MIN_DETECTION_CONFIDENCE` / `MIN_TRACKING_CONFIDENCE` in `config.py`.

**Gestures trigger accidentally / too sensitive**
- Increase the relevant cooldown value in `config.py`
  (`CLICK_COOLDOWN`, `GESTURE_COOLDOWN`, `SWIPE_COOLDOWN`).
- Increase `STILL_GESTURE_HOLD_TIME` to require a steadier hold before a
  static gesture is trusted.

**App feels laggy / low FPS**
- Lower `FRAME_WIDTH` / `FRAME_HEIGHT` in `config.py` (e.g. 640x360).
- Close other GPU/CPU-heavy applications.
- Make sure you're not running inside a low-resource virtual machine.

**Emergency stop**
- Press **ESC** at any time (works even if another window has focus) — the
  app will close immediately.

## 11. Customizing Gestures

All gesture shapes are decided in `gesture_detector.py`, inside
`HandDetector.classify_gesture()`. All thresholds, cooldowns, and mappings
live in `config.py`. All actual system actions live in `windows_control.py`.
Because the three files are cleanly separated, you can:
- Change which finger combination maps to which action (`gesture_detector.py`)
- Change what an action actually does (`windows_control.py`)
- Tune sensitivity/timing without touching any logic (`config.py`)

---

*Made for teachers who'd rather walk the room than stand at the laptop.*
