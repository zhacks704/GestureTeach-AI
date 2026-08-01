"""
windows_control.py
-------------------
Everything that actually TOUCHES the Windows operating system lives here:

  - Mouse movement / clicking / scrolling      -> pyautogui
  - Keyboard shortcuts (Win+E, Alt+Tab, etc.)  -> keyboard + pyautogui
  - System master volume                       -> pycaw
  - Screen brightness                          -> screen-brightness-control

gesture_detector.py never imports this file, and this file never imports
gesture_detector.py. main.py is the only thing that talks to both, keeping
a clean one-way dependency: vision -> decision -> action.

NOTE: This file performs REAL system actions when run. Some actions
(keyboard shortcuts, volume, brightness) work most reliably when the
script is run with administrator privileges on Windows - see README.md.
"""

import time
import math

import pyautogui
import keyboard
import screen_brightness_control as sbc

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

import config

# pyautogui.FAILSAFE lets the user instantly abort any automated mouse
# action by slamming the cursor into a screen corner - an extra safety net
# on top of the ESC emergency key.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0  # We manage our own timing via cooldowns instead of pyautogui's default delay.

SCREEN_W, SCREEN_H = pyautogui.size()


class WindowsController:
    """High level Windows actions that the gesture engine can trigger."""

    def __init__(self):
        # --- Set up the pycaw volume interface ONCE and reuse it --- #
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.volume = cast(interface, POINTER(IAudioEndpointVolume))

        self.cursor_locked = False
        self.prev_mouse_x, self.prev_mouse_y = pyautogui.position()

        # Tracks the last time each named action fired, so gestures held
        # for multiple frames don't spam the same action dozens of times
        # per second.
        self._last_action_time = {}

    # ------------------------------------------------------------------ #
    def _cooldown_ok(self, action_name, cooldown_seconds):
        """Return True only if enough time has passed since this action last fired."""
        now = time.time()
        last = self._last_action_time.get(action_name, 0)
        if now - last >= cooldown_seconds:
            self._last_action_time[action_name] = now
            return True
        return False

    # ------------------------------------------------------------------ #
    # MOUSE CONTROL
    # ------------------------------------------------------------------ #
    def move_mouse(self, frame_x, frame_y, frame_w, frame_h):
        """
        Map an (x, y) point inside the webcam frame's "active rectangle" to
        an absolute screen coordinate, then glide the mouse there.

        The smoothing amount is now ADAPTIVE based on how fast the hand is
        moving:
          - Fast movement (a deliberate swipe across the screen) uses a LOW
            smoothing value so the cursor keeps up with almost no lag.
          - Slow/near-still movement (fine positioning, or just holding the
            cursor over a button) uses a HIGH smoothing value so tiny hand
            tremor doesn't make the cursor visibly shake.
        A single fixed smoothing value always had to compromise between
        those two cases; blending between them gives both at once.
        """
        if self.cursor_locked:
            return

        fr = config.FRAME_REDUCTION

        # Clamp so the mapping never divides by a point outside the active rectangle.
        x = max(fr, min(frame_x, frame_w - fr))
        y = max(fr, min(frame_y, frame_h - fr))

        target_x = int((x - fr) / (frame_w - 2 * fr) * SCREEN_W)
        target_y = int((y - fr) / (frame_h - 2 * fr) * SCREEN_H)

        # How far is the raw target from where the cursor currently sits?
        # A bigger jump means the hand is moving quickly right now.
        travel = math.hypot(target_x - self.prev_mouse_x, target_y - self.prev_mouse_y)
        speed_ratio = min(travel / config.MOUSE_VELOCITY_THRESHOLD, 1.0)  # 0 = still, 1 = fast

        # Blend linearly between the "slow/steady" and "fast/snappy" smoothing values.
        smoothing = config.MOUSE_SMOOTHING_SLOW - speed_ratio * (
            config.MOUSE_SMOOTHING_SLOW - config.MOUSE_SMOOTHING_FAST
        )
        smoothing = max(smoothing, 1.0)  # never divide by less than 1 (would overshoot)

        smooth_x = self.prev_mouse_x + (target_x - self.prev_mouse_x) / smoothing
        smooth_y = self.prev_mouse_y + (target_y - self.prev_mouse_y) / smoothing

        pyautogui.moveTo(smooth_x, smooth_y)
        self.prev_mouse_x, self.prev_mouse_y = smooth_x, smooth_y

    def click_left(self):
        """Thumb + index pinch -> left click."""
        if self._cooldown_ok("click_left", config.CLICK_COOLDOWN):
            pyautogui.click(button="left")

    def click_right(self):
        """Thumb + middle pinch -> right click."""
        if self._cooldown_ok("click_right", config.CLICK_COOLDOWN):
            pyautogui.click(button="right")

    def scroll(self, direction):
        """direction: +1 scroll up, -1 scroll down."""
        pyautogui.scroll(direction * config.SCROLL_SENSITIVITY)

    def toggle_cursor_lock(self):
        """Closed fist -> toggle whether the mouse cursor can be moved."""
        if self._cooldown_ok("lock_toggle", config.GESTURE_COOLDOWN):
            self.cursor_locked = not self.cursor_locked
        return self.cursor_locked

    # ------------------------------------------------------------------ #
    # KEYBOARD / WINDOW MANAGEMENT / PRESENTATION MODE
    # ------------------------------------------------------------------ #
    def next_slide(self):
        """Swipe right -> next PowerPoint slide (Right Arrow)."""
        if self._cooldown_ok("next_slide", config.SWIPE_COOLDOWN):
            pyautogui.press("right")

    def previous_slide(self):
        """Swipe left -> previous PowerPoint slide (Left Arrow)."""
        if self._cooldown_ok("prev_slide", config.SWIPE_COOLDOWN):
            pyautogui.press("left")

    def start_slideshow(self):
        """Start a PowerPoint slideshow from the beginning (F5)."""
        if self._cooldown_ok("start_slideshow", config.GESTURE_COOLDOWN):
            pyautogui.press("f5")

    def exit_slideshow(self):
        """Exit the current PowerPoint slideshow (Esc)."""
        if self._cooldown_ok("exit_slideshow", config.GESTURE_COOLDOWN):
            pyautogui.press("esc")

    def open_file_explorer(self):
        """Three fingers -> open Windows File Explorer (Win+E)."""
        if self._cooldown_ok("file_explorer", config.GESTURE_COOLDOWN):
            keyboard.press_and_release("win+e")

    def alt_tab(self):
        """Index + middle finger (held still) -> switch applications (Alt+Tab)."""
        if self._cooldown_ok("alt_tab", config.GESTURE_COOLDOWN):
            keyboard.press_and_release("alt+tab")

    # ------------------------------------------------------------------ #
    # SYSTEM VOLUME (pycaw)
    # ------------------------------------------------------------------ #
    def set_volume_from_ratio(self, ratio):
        """ratio: 0.0 (silent) to 1.0 (maximum volume)."""
        ratio = max(0.0, min(1.0, ratio))
        self.volume.SetMasterVolumeLevelScalar(ratio, None)

    def get_volume_ratio(self):
        return self.volume.GetMasterVolumeLevelScalar()

    # ------------------------------------------------------------------ #
    # SCREEN BRIGHTNESS (screen-brightness-control)
    # ------------------------------------------------------------------ #
    def set_brightness_from_ratio(self, ratio):
        """ratio: 0.0 (darkest) to 1.0 (full brightness)."""
        ratio = max(0.0, min(1.0, ratio))
        try:
            sbc.set_brightness(int(ratio * 100))
        except Exception:
            # Some external monitors / virtual displays don't expose
            # brightness control to Windows - fail quietly instead of
            # crashing the whole application.
            pass
