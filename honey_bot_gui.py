import sys
import time
import threading
import platform
import subprocess
import pyautogui
from pynput import mouse
from PIL import ImageGrab
import numpy as np
from PyQt5 import QtWidgets, QtCore

# === BOT CONFIG ===
START_X, START_Y = 560, 740

screen_width, screen_height = pyautogui.size()
ITEM_WIDTH = int(65 * screen_width / 1920)
ITEM_HEIGHT = int(65 * screen_height / 1080)
ITEMS_PER_ROW = 10
MAX_ITEMS = 40
WAIT_TIME = 30

# === BOT STATE ===
bot_running = False
bot_stop_event = threading.Event()
position_selected = False

# === CORE LOGIC ===
def has_red_pixel(region):
    img = ImageGrab.grab(bbox=region)
    img_np = np.array(img)
    r, g, b = img_np[:, :, 0], img_np[:, :, 1], img_np[:, :, 2]
    red_mask = (r > 200) & (g < 80) & (b < 80)
    return np.any(red_mask)

def find_valid_item():
    global START_X, START_Y
    for i in range(MAX_ITEMS):
        col = i % ITEMS_PER_ROW
        row = i // ITEMS_PER_ROW
        x = START_X + col * ITEM_WIDTH
        y = START_Y + row * ITEM_HEIGHT
        region = (x, y, x + ITEM_WIDTH, y + ITEM_HEIGHT)
        if not has_red_pixel(region):
            return (x, y)
    return None

def focus_game_window(window_keyword):
    if platform.system() == "Darwin":
        script = f'''
        tell application "System Events"
            set frontmost of the first process whose name contains "{window_keyword}" to true
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        try:
            import pygetwindow as gw
            for w in gw.getWindowsWithTitle(window_keyword):
                w.activate()
                return True
        except:
            pass
        return False

def run_bot(status_label, window, window_keyword):
    global bot_running
    while bot_running and not bot_stop_event.is_set():
        print(f"👉 Using START_X={START_X}, START_Y={START_Y}")
        item_pos = find_valid_item()
        if item_pos:
            status_label.setText("Clicking item and pressing E...")
            pyautogui.click(item_pos)
            time.sleep(0.3)
            print("👇Pressed E to give plant")
            pyautogui.press('e')

            window.showNormal()
            window.raise_()
            window.activateWindow()
            QtCore.QThread.msleep(500)

            for i in range(WAIT_TIME):
                if bot_stop_event.is_set():
                    status_label.setText("Bot stopped.")
                    return
                status_label.setText(f"Waiting {WAIT_TIME - i}s...")
                time.sleep(1)

            focus_game_window(window_keyword)
            pyautogui.click()
            print("👇Pressed E to extract the honey")
            pyautogui.press('e')

            if bot_stop_event.is_set():
                status_label.setText("Bot stopped.")
                return

            window.hide()
            status_label.setText("Cycle complete. Restarting...")
            time.sleep(1)
        else:
            for i in range(10, 0, -1):
                if bot_stop_event.is_set():
                    status_label.setText("Bot stopped.")
                    return
                status_label.setText(f"No item. Retrying in {i}s...")
                time.sleep(1)

def delayed_start(status_label, window, start_button, pick_button, stop_button, window_keyword):
    for i in range(5, 0, -1):
        status_label.setText(f"Bot starting in {i}s...")
        time.sleep(1)
    window.hide()
    run_bot(status_label, window, window_keyword)

# === GUI ===
class BotWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Grow Garden Honey Bot")
        self.setFixedSize(360, 280)

        global START_X, START_Y

        # Labels
        self.title_label = QtWidgets.QLabel("🍯 Honey Compressor Bot", self)
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.coord_label = QtWidgets.QLabel(f"Start Position: ({START_X}, {START_Y})", self)
        self.coord_label.setStyleSheet("color: green;")
        
        self.status_label = QtWidgets.QLabel("Status: Waiting to start...", self)
        self.status_label.setStyleSheet("color: blue;")

        # Window keyword input
        self.keyword_label = QtWidgets.QLabel("Game Window Keyword:", self)
        self.keyword_input = QtWidgets.QLineEdit(self)
        self.keyword_input.setText("Grow")

        # Buttons
        self.pick_button = QtWidgets.QPushButton("📌 Pick Item Position", self)
        self.pick_button.clicked.connect(self.pick_position)

        self.start_button = QtWidgets.QPushButton("▶ Start Bot", self)
        self.start_button.clicked.connect(self.start_bot)

        self.stop_button = QtWidgets.QPushButton("▣ Stop Bot", self)
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.hide()

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.coord_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.keyword_label)
        layout.addWidget(self.keyword_input)
        layout.addWidget(self.pick_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)

    def pick_position(self):
        global START_X, START_Y, position_selected
        self.hide()
        print("👆 Click to set the start position")

        def on_click(x, y, button, pressed):
            global START_X, START_Y, position_selected
            if pressed:
                START_X, START_Y = x, y
                position_selected = True
                self.coord_label.setText(f"Start Position: ({START_X}, {START_Y})")
                print(f"✅ Picked: ({START_X}, {START_Y})")
                self.showNormal()
                self.raise_()
                listener.stop()
                return False

        listener = mouse.Listener(on_click=on_click)
        listener.start()

    def start_bot(self):
        global bot_running, bot_stop_event, position_selected

        if not position_selected:
            self.status_label.setText("⚠️ Please pick a position first.")
            return

        if not bot_running:
            bot_running = True
            bot_stop_event.clear()
            self.status_label.setText("Bot starting in 5s...")

            self.start_button.hide()
            self.pick_button.hide()
            self.stop_button.show()

            self.raise_()
            QtCore.QTimer.singleShot(500, self.raise_)

            window_keyword = self.keyword_input.text().strip()
            if not window_keyword:
                window_keyword = "Grow"

            QtCore.QTimer.singleShot(1000, lambda: focus_game_window(window_keyword))

            threading.Thread(
                target=delayed_start,
                args=(self.status_label, self, self.start_button, self.pick_button, self.stop_button, window_keyword),
                daemon=True
            ).start()

    def stop_bot(self):
        global bot_running, bot_stop_event
        bot_running = False
        bot_stop_event.set()
        self.status_label.setText("Bot stopped.")

        self.start_button.show()
        self.pick_button.show()
        self.stop_button.hide()

        self.showNormal()
        self.raise_()

    def closeEvent(self, event):
        self.stop_bot()
        event.accept()

# === RUN ===
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = BotWindow()
    window.show()
    sys.exit(app.exec_())
