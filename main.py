"""
main.py
-------
GestureTeach AI - Touchless Windows Controller
Application entry point + GUI.

This file connects:
  gesture_detector.py  (the "eyes" - sees the hand, names the gesture)
  windows_control.py   (the "hands" - actually moves the mouse, presses keys,
                         changes volume/brightness)
and displays everything inside a simple, professional Tkinter window.

RUN THIS FILE TO START THE APPLICATION:
    python main.py

See README.md for full installation and troubleshooting instructions.
"""

import time
import threading
from collections import deque

import cv2
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk

import config
from gesture_detector import HandDetector
from windows_control import WindowsController

class AutoQuality:
    """
    Watches the app's real, measured FPS while it runs and automatically
    raises or lowers the resolution MediaPipe analyses each frame, so the
    app finds a smooth setting for whatever laptop it happens to be running
    on - no manual tuning required. A fast machine settles at full quality;
    a struggling 8GB laptop automatically settles lower; if background load
    changes mid-session (another app opens), it adjusts again on its own.
    """

    def __init__(self):
        self.scale = config.MAX_PROCESS_SCALE
        self._frame_times = deque(maxlen=config.PERFORMANCE_SAMPLE_FRAMES)

    def record_frame_time(self, seconds):
        if not config.AUTO_PERFORMANCE:
            return
        self._frame_times.append(seconds)
        if len(self._frame_times) < self._frame_times.maxlen:
            return  # not enough samples yet to make a confident decision

        avg_fps = 1.0 / (sum(self._frame_times) / len(self._frame_times))
        self._frame_times.clear()  # start a fresh measurement window after each decision

        if avg_fps < config.TARGET_FPS * 0.8 and self.scale > config.MIN_PROCESS_SCALE:
            self.scale = round(max(config.MIN_PROCESS_SCALE, self.scale - config.PROCESS_SCALE_STEP), 2)
        elif avg_fps > config.TARGET_FPS * 1.15 and self.scale < config.MAX_PROCESS_SCALE:
            self.scale = round(min(config.MAX_PROCESS_SCALE, self.scale + config.PROCESS_SCALE_STEP), 2)


class ThreadedCamera:
    """
    Reads frames from the webcam on a dedicated background thread.

    On slower/low-RAM laptops, cap.read() can occasionally block for a
    noticeable moment (driver buffering, USB webcam hiccups, etc.). If that
    call happens directly on the Tkinter thread, the WHOLE GUI freezes for
    that moment - the window stops repainting and feels janky/unresponsive.
    Running capture on its own thread means the GUI loop always has the most
    recent frame available instantly, so the app stays smooth even if the
    camera itself is briefly slow.
    """

    def __init__(self, camera_index):
        if config.CAMERA_BACKEND_DSHOW:
            # CAP_DSHOW is a Windows-only backend that typically opens and
            # reads frames faster than the default backend.
            self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(camera_index)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        # Keep the internal buffer as small as possible so we always get the
        # NEWEST frame instead of processing a backlog of stale ones.
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._lock = threading.Lock()
        self._latest_frame = None
        self._running = True

        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def _reader_loop(self):
        while self._running:
            success, frame = self.cap.read()
            if success:
                with self._lock:
                    self._latest_frame = frame
            else:
                time.sleep(0.01)  # camera briefly unavailable, avoid a busy-spin

    def read(self):
        """Return the most recently captured frame (or None if not ready yet)."""
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def is_opened(self):
        return self.cap.isOpened()

    def release(self):
        self._running = False
        self._thread.join(timeout=1.0)
        self.cap.release()


# Human-readable labels shown in the GUI sidebar for each internal gesture name.
GESTURE_LABELS = {
    "none": "No Hand Detected",
    "point": "Index Finger - Moving Cursor",
    "click_left": "Thumb + Index Pinch - Left Click",
    "click_right": "Thumb + Middle Pinch - Right Click",
    "open_palm": "Open Palm - Recognition Paused",
    "fist": "Closed Fist - Cursor Locked",
    "three_fingers": "Three Fingers - File Explorer",
    "two_fingers": "Two Fingers - Scroll / Alt+Tab",
    "swipe_right": "Swipe Right - Next Slide",
    "swipe_left": "Swipe Left - Previous Slide",
    "volume": "Thumb + 2 Fingers - Volume Control",
    "brightness": "Four Fingers - Brightness Control",
}


class GestureTeachApp:
    """Main application window: webcam preview + gesture info + controls."""

    def __init__(self, root):
        self.root = root
        self.root.title(config.APP_TITLE)
        self.root.configure(bg=config.WINDOW_BG_COLOR)
        self.root.resizable(False, False)

        # ---------------- application state ---------------- #
        self.enabled = True          # False when the user presses "Disable"
        self.running = True          # False once the window is closing
        self.prev_frame_time = time.time()

        # State used to disambiguate the overloaded "two fingers" gesture
        # (scroll vs. Alt+Tab) - see gesture_detector.classify_gesture().
        self.prev_two_finger_y = None
        self.two_finger_still_since = None

        # ---------------- vision + control back-ends ---------------- #
        self.detector = HandDetector()
        self.controller = WindowsController()
        self.auto_quality = AutoQuality()   # keeps the app smooth on ANY laptop automatically

        self.cap = ThreadedCamera(config.CAMERA_INDEX)

        if not self.cap.is_opened():
            print("ERROR: Could not open webcam. Check CAMERA_INDEX in config.py "
                  "and make sure no other application is using the camera.")

        # Frame-pacing state: instead of a fixed 15ms delay (which can pile
        # up a backlog of work on a slow CPU), we time each frame and only
        # wait as long as needed to hit config.TARGET_FPS.
        self._target_frame_seconds = 1.0 / max(config.TARGET_FPS, 1)

        self._build_ui()

        # A background thread listens for the ESC key globally, so the
        # emergency exit works even if the Tkinter window isn't focused.
        threading.Thread(target=self._watch_emergency_key, daemon=True).start()

        self._update_frame()

    # ------------------------------------------------------------------ #
    # UI CONSTRUCTION
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        title_font = tkfont.Font(family=config.FONT_NAME, size=16, weight="bold")
        label_font = tkfont.Font(family=config.FONT_NAME, size=12)
        small_font = tkfont.Font(family=config.FONT_NAME, size=9, slant="italic")

        header = tk.Label(
            self.root, text=config.APP_TITLE, font=title_font,
            fg=config.ACCENT_COLOR, bg=config.WINDOW_BG_COLOR, pady=12
        )
        header.pack()

        # Webcam preview goes inside this Label (it's just an image that we
        # keep replacing, frame after frame).
        self.video_label = tk.Label(self.root, bg="black")
        self.video_label.pack(padx=12, pady=4)

        info_frame = tk.Frame(self.root, bg=config.WINDOW_BG_COLOR)
        info_frame.pack(fill="x", padx=12, pady=6)

        self.gesture_var = tk.StringVar(value="Gesture: No Hand Detected")
        self.status_var = tk.StringVar(value="Status: Running")

        tk.Label(
            info_frame, textvariable=self.gesture_var, font=label_font,
            fg="white", bg=config.WINDOW_BG_COLOR, anchor="w"
        ).pack(fill="x")

        tk.Label(
            info_frame, textvariable=self.status_var, font=label_font,
            fg="#9be3e8", bg=config.WINDOW_BG_COLOR, anchor="w"
        ).pack(fill="x")

        self.toggle_btn = tk.Button(
            self.root, text="Disable", font=label_font, width=22,
            command=self._toggle_enabled, bg=config.ACCENT_COLOR, fg="black",
            relief="flat", activebackground="#00979e", cursor="hand2"
        )
        self.toggle_btn.pack(pady=10)

        tk.Label(
            self.root, text="Press ESC anytime for emergency exit.",
            font=small_font, fg="#777777", bg=config.WINDOW_BG_COLOR, pady=6
        ).pack()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    def _toggle_enabled(self):
        """Enable/Disable button - pauses gesture recognition and all control actions."""
        self.enabled = not self.enabled
        self.toggle_btn.config(text="Disable" if self.enabled else "Enable")
        self.status_var.set(f"Status: {'Running' if self.enabled else 'Paused (disabled by user)'}")

    # ------------------------------------------------------------------ #
    def _watch_emergency_key(self):
        """Background thread: instantly quit the whole app if ESC is pressed."""
        import keyboard
        keyboard.wait(config.EMERGENCY_EXIT_KEY)
        self.running = False
        self.root.after(0, self._on_close)

    # ------------------------------------------------------------------ #
    def _on_close(self):
        """Clean shutdown: release the camera and MediaPipe resources."""
        self.running = False
        try:
            self.cap.release()   # stops the background camera thread, then releases the device
            self.detector.close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # MAIN LOOP (runs once per Tkinter "after" tick, ~60 fps target)
    # ------------------------------------------------------------------ #
    def _update_frame(self):
        if not self.running:
            return

        loop_start = time.time()

        frame = self.cap.read()
        if frame is None:
            # Camera thread hasn't produced a frame yet (e.g. still starting
            # up) - check again shortly instead of blocking.
            self.root.after(15, self._update_frame)
            return

        if config.FLIP_CAMERA:
            frame = cv2.flip(frame, 1)  # mirror image = natural hand movement

        h, w = frame.shape[:2]
        gesture = "none"

        if self.enabled:
            frame = self.detector.find_hands(
                frame, draw=config.DRAW_LANDMARKS, process_scale=self.auto_quality.scale
            )
            self.detector.find_positions(frame)
            gesture = self.detector.classify_gesture(w)

            # "open_palm" is the dedicated pause gesture: skip acting on
            # anything else while the palm is open, per the spec.
            if gesture != "open_palm":
                self._act_on_gesture(gesture, w, h)
        else:
            gesture = "paused"

        self._draw_overlay(frame, gesture)

        # Update the sidebar gesture label with a friendly name.
        if gesture == "paused":
            label_text = "Recognition Disabled"
        else:
            label_text = GESTURE_LABELS.get(gesture, "No Hand Detected")
        self.gesture_var.set(f"Gesture: {label_text}")

        if self.enabled:
            quality_pct = int(self.auto_quality.scale * 100)
            self.status_var.set(f"Status: Running (auto quality: {quality_pct}%)")

        # Push the OpenCV (BGR) frame into the Tkinter label as an image.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk  # keep a reference or Tk will garbage-collect it
        self.video_label.configure(image=imgtk)

        # Only wait as long as needed to hit TARGET_FPS. If this frame's
        # processing already took longer than the target interval (common on
        # an 8GB RAM / low-end CPU machine), schedule the next one almost
        # immediately instead of stacking an extra fixed delay on top -
        # this keeps the app feeling as responsive as the hardware allows
        # rather than artificially capping it below what it could do.
        elapsed = time.time() - loop_start
        self.auto_quality.record_frame_time(max(elapsed, 0.0001))
        delay_seconds = max(self._target_frame_seconds - elapsed, 0.001)
        self.root.after(int(delay_seconds * 1000), self._update_frame)

    # ------------------------------------------------------------------ #
    # GESTURE -> ACTION ROUTING
    # ------------------------------------------------------------------ #
    def _act_on_gesture(self, gesture, w, h):
        """Translate one detected gesture name into a real Windows action."""
        lm = self.detector.landmark_list

        if gesture == "point" and lm:
            index_tip = lm[8]
            self.controller.move_mouse(index_tip[1], index_tip[2], w, h)

        elif gesture == "click_left":
            self.controller.click_left()

        elif gesture == "click_right":
            self.controller.click_right()

        elif gesture == "fist":
            self.controller.toggle_cursor_lock()

        elif gesture == "three_fingers":
            self.controller.open_file_explorer()

        elif gesture == "swipe_right":
            self.controller.next_slide()

        elif gesture == "swipe_left":
            self.controller.previous_slide()

        elif gesture == "two_fingers":
            self._handle_two_finger_gesture()

        elif gesture == "volume":
            self._handle_volume_gesture(h)

        elif gesture == "brightness":
            self._handle_brightness_gesture(h)

        else:
            # No relevant gesture this frame - reset the "still hand" timer
            # used by the two-finger scroll/alt-tab disambiguation.
            self.two_finger_still_since = None
            self.prev_two_finger_y = None

    # ------------------------------------------------------------------ #
    def _handle_two_finger_gesture(self):
        """
        The spec assigns the SAME hand shape (index + middle extended) to
        two different actions: "scroll" and "Alt+Tab". We tell them apart
        using movement:
          - Moving the fingers up/down noticeably  -> scroll the document.
          - Holding the hand still for a brief moment -> trigger Alt+Tab
            (only once per hold, thanks to the cooldown in windows_control).
        """
        center = self.detector.palm_center()
        if not center:
            return
        _, y = center
        now = time.time()

        if self.prev_two_finger_y is None:
            self.prev_two_finger_y = y
            self.two_finger_still_since = now
            return

        dy = self.prev_two_finger_y - y  # positive = hand moved up
        self.prev_two_finger_y = y

        if abs(dy) > 6:
            # Clear vertical movement -> scroll, and reset the stillness timer.
            direction = 1 if dy > 0 else -1
            self.controller.scroll(direction)
            self.two_finger_still_since = now
        else:
            if self.two_finger_still_since is None:
                self.two_finger_still_since = now
            elif now - self.two_finger_still_since >= config.STILL_GESTURE_HOLD_TIME + 0.3:
                self.controller.alt_tab()

    # ------------------------------------------------------------------ #
    def _handle_volume_gesture(self, frame_h):
        """Map the vertical hand position to system volume while held."""
        center = self.detector.palm_center()
        if not center:
            return
        _, y = center
        fr = config.FRAME_REDUCTION
        clamped_y = max(fr, min(y, frame_h - fr))
        ratio = 1 - (clamped_y - fr) / (frame_h - 2 * fr)  # top of frame = loud

        current = self.controller.get_volume_ratio()
        smoothed = current + (ratio - current) * config.VOLUME_GESTURE_SMOOTHING
        self.controller.set_volume_from_ratio(smoothed)

    # ------------------------------------------------------------------ #
    def _handle_brightness_gesture(self, frame_h):
        """Map the vertical hand position to screen brightness while held."""
        center = self.detector.palm_center()
        if not center:
            return
        _, y = center
        fr = config.FRAME_REDUCTION
        clamped_y = max(fr, min(y, frame_h - fr))
        ratio = 1 - (clamped_y - fr) / (frame_h - 2 * fr)  # top of frame = bright
        self.controller.set_brightness_from_ratio(ratio)

    # ------------------------------------------------------------------ #
    # OVERLAY DRAWING (FPS, gesture text, active-zone box, watermark)
    # ------------------------------------------------------------------ #
    def _draw_overlay(self, frame, gesture):
        now = time.time()
        fps = 1 / (now - self.prev_frame_time) if now != self.prev_frame_time else 0
        self.prev_frame_time = now

        h, w = frame.shape[:2]

        cv2.putText(frame, f"FPS: {int(fps)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.putText(frame, f"Gesture: {gesture}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # Draw the "active rectangle" used for mouse mapping so the user
        # can see exactly which region of the frame maps to the full screen.
        if config.DRAW_ACTIVE_ZONE:
            fr = config.FRAME_REDUCTION
            cv2.rectangle(frame, (fr, fr), (w - fr, h - fr), (90, 90, 90), 1)

        # --- Watermark, bottom-right corner --- #
        text = config.WATERMARK_TEXT
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        x = w - tw - 12
        y = h - 12
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (210, 210, 210), 1, cv2.LINE_AA)


def main():
    root = tk.Tk()
    GestureTeachApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
