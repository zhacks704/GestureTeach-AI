"""
config.py
---------
Central configuration file for GestureTeach AI.

Every tunable number/string used by the rest of the app lives here so that
gesture_detector.py, windows_control.py and main.py never contain "magic
numbers" scattered through the code. If a gesture feels too sensitive, too
slow, or the mouse mapping feels off, this is the file to tweak.
"""

# ----------------------------- CAMERA SETTINGS ----------------------------- #
CAMERA_INDEX = 0            # 0 = default webcam. Change to 1 / 2 if you have multiple cameras.
# Lowered from 960x540 -> 640x360 by default. This is the single biggest lever
# for performance: every pixel here is processed by MediaPipe AND redrawn in
# the GUI every frame, so a smaller frame = noticeably less CPU/RAM work.
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
FLIP_CAMERA = True          # Mirror the image so hand movement feels natural (like a mirror).
CAMERA_BACKEND_DSHOW = True  # Windows only: DirectShow backend opens/reads faster than the default.

# ----------------------------- MEDIAPIPE SETTINGS -------------------------- #
MAX_NUM_HANDS = 1                       # Only ONE hand is tracked, as required.
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7
# 0 = "lite" model (fastest, slightly less precise), 1 = "full" model (slower,
# more precise). On an 8GB RAM / low-end CPU laptop, 0 is strongly recommended.
MODEL_COMPLEXITY = 0

# ----------------------------- PERFORMANCE MODE ----------------------------- #
# These knobs trade a little visual polish for speed. If the app still feels
# laggy after trying MODEL_COMPLEXITY = 0 and the lower resolution above,
# adjust these next.
TARGET_FPS = 24              # The app will not try to run faster than this - saves CPU on fast machines too.
DRAW_LANDMARKS = True        # Set False to skip drawing the hand skeleton (small CPU/GPU saving).
DRAW_ACTIVE_ZONE = True      # Set False to skip drawing the mouse-mapping rectangle overlay.
FINGER_STATE_SMOOTHING = 3   # How many recent frames "vote" on each finger's up/down state.
                              # Higher = steadier gestures but a touch more delay. 1 = no smoothing.

# ----------------------------- AUTO PERFORMANCE (works on ANY laptop) ------- #
# Instead of you having to guess the right settings for a specific machine,
# the app measures its own real FPS while running and automatically shrinks
# (or grows back) the resolution MediaPipe analyses each frame to keep things
# smooth - on a fast gaming laptop it will use full quality, on an 8GB office
# laptop it will automatically drop to a lighter setting, with no numbers to
# guess and no restart needed as system load changes mid-session.
AUTO_PERFORMANCE = True
PERFORMANCE_SAMPLE_FRAMES = 20     # How many frames to measure before considering an adjustment.
MIN_PROCESS_SCALE = 0.5            # Never shrink the MediaPipe analysis below 50% resolution.
MAX_PROCESS_SCALE = 1.0            # Full resolution ceiling (matches FRAME_WIDTH/HEIGHT above).
PROCESS_SCALE_STEP = 0.1           # How big each automatic quality step is.

# ----------------------------- MOUSE RESPONSIVENESS ------------------------- #
# The cursor now blends between two smoothing levels based on how fast the
# hand is actually moving, instead of one fixed value:
#   - Moving quickly  -> MOUSE_SMOOTHING_FAST (snappy, low-lag response)
#   - Barely moving   -> MOUSE_SMOOTHING_SLOW (steady, jitter-free hold)
# This gives quick reactions AND a calm resting cursor at the same time.
MOUSE_SMOOTHING_FAST = 2.0
MOUSE_SMOOTHING_SLOW = 7.0
MOUSE_VELOCITY_THRESHOLD = 45      # Pixel movement per frame that counts as "fast" (maps to full responsiveness).

# ----------------------------- MOUSE CONTROL ------------------------------- #
# The webcam frame is smaller than the monitor, so we map a central "active
# rectangle" inside the frame to the FULL screen. This means the user does
# not need to stretch their hand to the very edge of the camera view to
# reach the edge of the screen.
FRAME_REDUCTION = 100                   # Pixels trimmed from each side of the frame.
MOUSE_SMOOTHING = 5                     # Higher = smoother movement, slightly more lag.

# ----------------------------- GESTURE THRESHOLDS -------------------------- #
PINCH_THRESHOLD = 35            # Normalised pinch distance below which two fingers count as "touching".
CLICK_COOLDOWN = 0.4             # Seconds between allowed mouse clicks.
GESTURE_COOLDOWN = 0.8           # Seconds between allowed discrete actions (Explorer, Alt+Tab, lock...).
SWIPE_COOLDOWN = 1.0             # Seconds between allowed swipe (slide change) actions.
SWIPE_DISTANCE_THRESHOLD = 100   # Minimum horizontal pixel travel to register as a swipe.
SWIPE_TIME_WINDOW = 0.6          # A swipe must happen within this many seconds.
SCROLL_SENSITIVITY = 30          # Scroll "clicks" applied per detected vertical movement.
STILL_GESTURE_HOLD_TIME = 0.35   # Seconds a static gesture must be held before it is trusted.

# ----------------------------- VOLUME / BRIGHTNESS ------------------------- #
# While the volume/brightness gesture is held, the hand's vertical position
# in the frame (top = high, bottom = low) is mapped to a 0-100% value.
VOLUME_GESTURE_SMOOTHING = 0.3
BRIGHTNESS_GESTURE_SMOOTHING = 0.3

# ----------------------------- SAFETY --------------------------------------- #
EMERGENCY_EXIT_KEY = "esc"    # Pressing this key ANYWHERE instantly closes the app.

# ----------------------------- USER INTERFACE -------------------------------- #
APP_TITLE = "GestureTeach AI - Touchless Windows Controller"
WATERMARK_TEXT = "insta @aesthetic.zaidu"
WINDOW_BG_COLOR = "#101820"
ACCENT_COLOR = "#00C2CB"
FONT_NAME = "Segoe UI"
