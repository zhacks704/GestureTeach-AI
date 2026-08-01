GestureTeach AI

AI-Based Touchless Hand Gesture Control System

Control your computer using real-time hand gestures through a webcam.

GestureTeach AI allows teachers, presenters, and users to control their computer without touching the keyboard or mouse. Using computer vision and AI-based hand tracking, users can control presentations, mouse actions, scrolling, volume, brightness, and system shortcuts using simple hand gestures.

---

Creator

ZAID BILAL

Project Creator & Maintainer

Year: 2026

---

Features

- Real-time hand tracking using AI vision
- Touchless mouse control
- Left and right click gestures
- Scrolling control
- PowerPoint presentation control
- Application switching
- File Explorer opening
- Volume control
- Brightness control
- Emergency exit system
- Enable/Disable gesture control
- Performance optimization for low-end systems

---

Technologies Used

- Python
- OpenCV
- MediaPipe
- PyAutoGUI
- Tkinter
- Pillow
- Keyboard Automation

---

Project Structure

GestureTeach-AI/

│
├── main.py                 # Main application and GUI
├── gesture_detector.py     # Hand tracking and gesture recognition
├── windows_control.py      # Windows system controls
├── config.py               # Configuration settings
│
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
├── LICENSE                 # License information
├── AUTHORS.md              # Creator information
│
└── assets/                 # Images and resources

---

Requirements

Hardware

- Webcam
- Computer/Laptop
- Good lighting conditions

Software

- Python 3.9 - 3.11
- Windows 10/11
- Linux
- macOS

---

Installation Guide

Windows

1. Clone Repository

Open Command Prompt:

git clone https://github.com/zhacks704/GestureTeach-AI.git

2. Open Project Folder

cd GestureTeach-AI

3. Create Virtual Environment

python -m venv venv

Activate:

venv\Scripts\activate

4. Install Dependencies

pip install -r requirements.txt

5. Run Application

python main.py

---

Linux

1. Clone Repository

git clone https://github.com/zhacks704/GestureTeach-AI.git

2. Open Folder

cd GestureTeach-AI

3. Install Dependencies

pip3 install -r requirements.txt

4. Run Application

python3 main.py

---

macOS

1. Clone Repository

git clone https://github.com/zhacks704/GestureTeach-AI.git

2. Open Folder

cd GestureTeach-AI

3. Install Dependencies

pip3 install -r requirements.txt

4. Run Application

python3 main.py

---

Gesture Controls

Gesture| Action
Index finger pointing| Move mouse cursor
Thumb + index pinch| Left click
Thumb + middle pinch| Right click
Two fingers moving up/down| Scroll
Two fingers held steady| Alt + Tab
Open hand swipe right| Next slide
Open hand swipe left| Previous slide
Three fingers| Open File Explorer
Thumb + index + middle movement| Volume control
Four fingers| Brightness control
Open palm| Pause gestures
Closed fist| Lock/unlock cursor

---

How It Works

GestureTeach AI uses:

1. Webcam input
2. MediaPipe hand landmark detection
3. Gesture classification
4. Gesture-to-action mapping
5. Computer control commands

Flow:

Camera
  |
  ↓
OpenCV
  |
  ↓
MediaPipe AI Hand Tracking
  |
  ↓
Gesture Recognition
  |
  ↓
System Control Action

---

Configuration

You can customize settings in:

config.py

You can modify:

- Camera index
- Gesture sensitivity
- Detection confidence
- FPS settings
- Mouse smoothing
- Cooldown timers

---

Troubleshooting

Camera not detected

Try changing:

CAMERA_INDEX = 0

in:

config.py

Try:

CAMERA_INDEX = 1

for another camera.

---

Installation error

Check Python version:

python --version

Recommended:

Python 3.9 - 3.11

---

Gesture not working

Check:

- Good lighting
- Camera permission
- Hand visibility
- Run terminal with required permissions

---

Future Improvements

Planned features:

- Linux system controller
- macOS controller
- More AI gesture models
- Voice commands
- Custom gesture training
- Multi-hand support

---

License

Copyright © 2026 ZAID BILAL

This project is licensed under the MIT License.
