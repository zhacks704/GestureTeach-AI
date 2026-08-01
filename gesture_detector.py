"""
gesture_detector.py
--------------------
This module handles all computer-vision work:

  1. Running MediaPipe Hands on webcam frames.
  2. Extracting the 21 hand-landmark positions.
  3. Working out which fingers are extended ("up").
  4. Classifying the current hand shape into one named "gesture".

IMPORTANT DESIGN CHOICE:
This file knows NOTHING about Windows, the mouse, or the keyboard. It only
answers one question: "what is the hand doing right now?". main.py is the
only place that turns a gesture name into a real system action. Keeping
vision code and control code separate makes the project much easier to
read, test, and extend.
"""

import math
import time
from collections import deque

import cv2
import mediapipe as mp

import config


class HandDetector:
    """Wraps MediaPipe Hands and adds finger-counting / gesture-classification logic."""

    # Landmark indices for the 5 fingertips (thumb, index, middle, ring, pinky).
    TIP_IDS = [4, 8, 12, 16, 20]

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=config.MAX_NUM_HANDS,
            min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            model_complexity=config.MODEL_COMPLEXITY,   # 0 = lite/fast model for low-end hardware
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        self.landmark_list = []     # [(id, x_px, y_px), ...] for the most recent frame.
        self.results = None

        # Rolling history of the palm's horizontal position, used to detect
        # quick left/right swipes (for changing presentation slides).
        self.x_history = deque(maxlen=15)

        # Rolling history of raw finger-up readings, used to "vote" on the
        # true finger state each frame. This is what makes gestures other
        # than plain pointing feel stable instead of flickery - a single
        # noisy frame from MediaPipe can no longer flip a gesture on its own.
        self._finger_history = deque(maxlen=max(config.FINGER_STATE_SMOOTHING, 1))

    # ------------------------------------------------------------------ #
    def find_hands(self, frame, draw=True, process_scale=1.0):
        """
        Run MediaPipe on the frame and (optionally) draw the hand skeleton.

        process_scale (0.0-1.0): MediaPipe only looks at a SMALLER, resized
        copy of the frame when this is below 1.0 - fewer pixels to analyse
        means noticeably less CPU work per frame. This does NOT lose any
        visual quality: MediaPipe's landmark coordinates are normalised
        (0.0-1.0) regardless of the input size, so they still map perfectly
        onto the full-resolution frame for drawing and gesture math. This is
        what lets the app automatically get lighter on a slow machine
        without shrinking the actual webcam preview the user sees.
        """
        if process_scale < 0.999:
            h, w = frame.shape[:2]
            small = cv2.resize(frame, (max(int(w * process_scale), 2), max(int(h * process_scale), 2)))
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        self.results = self.hands.process(rgb)

        if self.results.multi_hand_landmarks:
            for hand_landmarks in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(
                        frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_styles.get_default_hand_landmarks_style(),
                        self.mp_styles.get_default_hand_connections_style(),
                    )
        return frame

    # ------------------------------------------------------------------ #
    def find_positions(self, frame):
        """Store and return [(id, x_px, y_px), ...] for the first detected hand."""
        self.landmark_list = []
        h, w = frame.shape[:2]

        if self.results and self.results.multi_hand_landmarks:
            hand = self.results.multi_hand_landmarks[0]  # only ONE hand is tracked
            for idx, lm in enumerate(hand.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                self.landmark_list.append((idx, cx, cy))

        return self.landmark_list

    # ------------------------------------------------------------------ #
    @staticmethod
    def distance(p1, p2):
        """Straight-line pixel distance between two (id, x, y) landmark points."""
        return math.hypot(p2[1] - p1[1], p2[2] - p1[2])

    # ------------------------------------------------------------------ #
    def _fingers_up_raw(self):
        """
        Single-frame estimate of [thumb, index, middle, ring, pinky],
        True = extended. This is intentionally cheap (a handful of distance
        / coordinate comparisons) so it costs almost nothing on slow CPUs.
        """
        if len(self.landmark_list) < 21:
            return [False, False, False, False, False]

        lm = self.landmark_list
        fingers = []

        # --- Thumb --- #
        # The thumb folds "sideways" toward the palm rather than up/down, so
        # a plain y-coordinate check (like the other fingers use) doesn't
        # work for it. Comparing distance-to-wrist also breaks depending on
        # which hand/orientation the camera sees. The reliable, orientation
        # independent trick: compare the thumb tip's distance to the pinky
        # knuckle (landmark 17) against the thumb's middle-joint distance to
        # that same point. When the thumb is tucked into the palm it sits
        # close to that knuckle; when extended it moves clearly away from it
        # - true regardless of left/right hand or camera mirroring.
        pinky_mcp = lm[17]
        thumb_tip = lm[4]
        thumb_ip = lm[3]
        fingers.append(self.distance(thumb_tip, pinky_mcp) > self.distance(thumb_ip, pinky_mcp) * 1.05)

        # --- Index, middle, ring, pinky --- #
        # A finger is "up" if its tip sits above (smaller y) the knuckle two
        # joints below it, in image coordinates (y grows downward).
        for tip_id in self.TIP_IDS[1:]:
            fingers.append(lm[tip_id][2] < lm[tip_id - 2][2])

        return fingers

    # ------------------------------------------------------------------ #
    def fingers_up(self):
        """
        Smoothed [thumb, index, middle, ring, pinky] booleans. Instead of
        trusting a single (possibly noisy) frame, this keeps a short history
        of raw readings and returns the MAJORITY vote for each finger. This
        is what stops gestures like the fist, three-fingers, or pinch shapes
        from flickering in and out on a slower machine that occasionally
        drops or delays frames - only the mouse-pointing gesture (which only
        needs ONE finger's state) was immune to that flicker before.
        """
        raw = self._fingers_up_raw()
        self._finger_history.append(raw)

        smoothed = []
        for i in range(5):
            votes = [frame[i] for frame in self._finger_history]
            smoothed.append(sum(votes) > len(votes) / 2)
        return smoothed

    # ------------------------------------------------------------------ #
    def hand_size(self):
        """
        Rough size of the hand in the current frame (wrist -> middle-finger
        knuckle). Used to normalise pinch distances so gestures work the
        same whether the hand is close to or far from the camera.
        """
        if len(self.landmark_list) < 21:
            return 1
        wrist = self.landmark_list[0]
        middle_mcp = self.landmark_list[9]
        return max(self.distance(wrist, middle_mcp), 1)

    # ------------------------------------------------------------------ #
    def palm_center(self):
        """Approximate centre of the palm (average of wrist + 4 knuckles)."""
        if len(self.landmark_list) < 21:
            return None
        ids = [0, 5, 9, 13, 17]
        xs = [self.landmark_list[i][1] for i in ids]
        ys = [self.landmark_list[i][2] for i in ids]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    # ------------------------------------------------------------------ #
    def classify_gesture(self, frame_width):
        """
        Inspect finger states + pinch distances and return ONE string
        describing the current gesture. main.py decides what to actually
        DO with that string.

        Possible return values:
          "none", "point", "click_left", "click_right",
          "open_palm", "fist", "three_fingers", "two_fingers",
          "swipe_right", "swipe_left", "volume", "brightness"

        NOTE ON OVERLAPPING SHAPES:
        The requested gesture list uses the SAME hand shape (index + middle
        finger extended) for two different actions: "Two fingers -> scroll"
        and "Index + middle finger -> Alt+Tab". Since a static photo of the
        hand can't tell those two apart, this detector reports the shared
        shape as "two_fingers" and main.py disambiguates using MOVEMENT:
        moving the two fingers up/down -> scroll, holding them still for a
        moment -> Alt+Tab. This is documented again in main.py and README.md.
        """
        if len(self.landmark_list) < 21:
            self.x_history.clear()
            self._finger_history.clear()
            return "none"

        fingers = self.fingers_up()
        thumb, index, middle, ring, pinky = fingers
        count_up = sum(fingers)

        lm = self.landmark_list
        size = self.hand_size()

        thumb_tip = lm[4]
        index_tip = lm[8]
        middle_tip = lm[12]

        # Distances normalised against hand size (scale-independent, 0-100ish range).
        thumb_index_dist = (self.distance(thumb_tip, index_tip) / size) * 100
        thumb_middle_dist = (self.distance(thumb_tip, middle_tip) / size) * 100

        # Track horizontal palm movement over time, for swipe detection.
        center = self.palm_center()
        now = time.time()
        if center:
            self.x_history.append((now, center[0]))

        # --- 1) Pinch gestures take top priority (deliberate, precise action) --- #
        if thumb_index_dist < config.PINCH_THRESHOLD * 0.9 and not middle:
            return "click_left"
        if thumb_middle_dist < config.PINCH_THRESHOLD * 0.9 and not index:
            return "click_right"

        # --- 2) Open palm (all 5 fingers spread) = pause gesture recognition --- #
        if count_up == 5:
            return "open_palm"

        # --- 3) Closed fist (no fingers extended) = lock the cursor --- #
        if count_up == 0:
            return "fist"

        # --- 4) Thumb + index + middle (ring & pinky folded) = volume control --- #
        if thumb and index and middle and not ring and not pinky:
            return "volume"

        # --- 4b) Four fingers, thumb folded = brightness control --- #
        # (Bonus mapping: the project brief requires using
        # screen-brightness-control but doesn't assign it a specific
        # gesture, so this shape was chosen to keep it clearly distinct
        # from every other gesture in the list.)
        if not thumb and index and middle and ring and pinky:
            return "brightness"

        # --- 5) Index + middle + ring (thumb & pinky folded) = File Explorer --- #
        if not thumb and index and middle and ring and not pinky:
            return "three_fingers"

        # --- 6) Index + middle only = swipe / scroll / alt-tab family --- #
        if index and middle and not ring and not pinky and not thumb:
            swipe = self._detect_swipe()
            if swipe:
                return swipe
            return "two_fingers"

        # --- 7) Index finger only = move the mouse cursor --- #
        if index and not middle and not ring and not pinky:
            return "point"

        return "none"

    # ------------------------------------------------------------------ #
    def _detect_swipe(self):
        """
        Look at the recent palm x-position history to decide whether the
        hand travelled far enough, fast enough, in one direction, to count
        as an intentional left/right swipe (used to change slides).
        """
        if len(self.x_history) < 2:
            return None

        t_now, x_now = self.x_history[-1]

        for t_old, x_old in self.x_history:
            if t_now - t_old <= config.SWIPE_TIME_WINDOW:
                dx = x_now - x_old
                if abs(dx) >= config.SWIPE_DISTANCE_THRESHOLD:
                    self.x_history.clear()  # prevent the same swipe firing twice
                    return "swipe_right" if dx > 0 else "swipe_left"
                break

        return None

    # ------------------------------------------------------------------ #
    def close(self):
        """Release MediaPipe resources cleanly on shutdown."""
        self.hands.close()
