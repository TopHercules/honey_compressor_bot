import sys
import time
import threading
import platform
import subprocess
import pyautogui
from PIL import ImageGrab
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

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

def has_red_pixel(region):
    try:
        img = ImageGrab.grab(bbox=region)
        img_np = np.array(img)
        r, g, b = img_np[:, :, 0], img_np[:, :, 1], img_np[:, :, 2]
        red_mask = (r > 200) & (g < 80) & (b < 80)
        return np.any(red_mask)
    except Exception as e:
        print(f"Error capturing screen region: {e}")
        return False

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

class BotWindow(QtWidgets.QWidget):
    update_status_signal = pyqtSignal(str)
    hide_window_signal = pyqtSignal()
    show_window_signal = pyqtSignal()
    raise_window_signal = pyqtSignal()

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
        
        # Connect signals
        self.update_status_signal.connect(self.status_label.setText)
        self.hide_window_signal.connect(self.hide)
        self.show_window_signal.connect(self.showNormal)
        self.raise_window_signal.connect(self.raise_)

        # Store bot thread for control
        self.bot_thread = None

    def pick_position(self):
        global START_X, START_Y, position_selected

        class OverlayWindow(QtWidgets.QWidget):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
                self.setWindowFlags(
                    QtCore.Qt.FramelessWindowHint |
                    QtCore.Qt.WindowStaysOnTopHint |
                    QtCore.Qt.Tool
                )
                self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

                screens = QtWidgets.QApplication.screens()
                desktop_rect = screens[0].geometry()
                for screen in screens[1:]:
                    desktop_rect = desktop_rect.united(screen.geometry())

                self.setGeometry(desktop_rect)

                self.setStyleSheet("background-color: rgba(0, 0, 0, 50);")

                label = QtWidgets.QLabel("Click anywhere to pick the position", self)
                label.setStyleSheet("color: white; font-size: 24px; background-color: rgba(0, 0, 0, 128);")
                label.setAlignment(QtCore.Qt.AlignCenter)

                layout = QtWidgets.QVBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(label)

                self.installEventFilter(self)

            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    global START_X, START_Y, position_selected
                    pos = event.globalPos()
                    print("Mouse press event triggered")
                    START_X = pos.x()
                    START_Y = pos.y()
                    position_selected = True
                    print(f"✅ Picked: ({START_X}, {START_Y})")
                    self.parent.coord_label.setText(f"Start Position: ({START_X}, {START_Y})")
                    self.parent.showNormal()
                    self.parent.raise_()
                    self.close()
                    return True
                return False

        self.hide()
        self.overlay = OverlayWindow(self)
        self.overlay.show()
        self.overlay.raise_()

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

            print("✅ UI updated")

            self.raise_()
            QtCore.QTimer.singleShot(500, self.raise_)

            window_keyword = self.keyword_input.text().strip()
            if not window_keyword:
                window_keyword = "Grow"

            print(f"✅ Ready to start thread")
            self.bot_thread = threading.Thread(
                target=self.delayed_start,
                args=(window_keyword,),
                daemon=True
            )
            self.bot_thread.start()

    def delayed_start(self, window_keyword):
        print("Thread was started")
        for i in range(5, 0, -1):
            if bot_stop_event.is_set():
                self.update_status_signal.emit("Bot stopped before start.")
                return
            self.update_status_signal.emit(f"Bot starting in {i}s...")
            time.sleep(1)

        if bot_stop_event.is_set():
            self.update_status_signal.emit("Bot stopped before focus.")
            return

        focus_game_window(window_keyword)
        self.hide_window_signal.emit()
        self.run_bot(window_keyword)

    def run_bot(self, window_keyword):
        global bot_running
        while bot_running and not bot_stop_event.is_set():
            try:
                print(f"👉 Using START_X={START_X}, START_Y={START_Y}")
                item_pos = find_valid_item()
                if item_pos:
                    self.update_status_signal.emit("Clicking item and pressing E twice to give plant...")
                    pyautogui.click(item_pos)
                    time.sleep(0.3)
                    pyautogui.press('e')
                    print("👇Pressed E twice to give plant")

                    self.update_status_signal.emit("Waiting 30s with bot window on top...")
                    self.show_window_signal.emit()
                    self.raise_window_signal.emit()

                    for i in range(WAIT_TIME):
                        if bot_stop_event.is_set():
                            self.update_status_signal.emit("Bot stopped.")
                            return
                        self.update_status_signal.emit(f"Waiting {WAIT_TIME - i}s...")
                        time.sleep(1)

                    if bot_stop_event.is_set():
                        self.update_status_signal.emit("Bot stopped before extracting honey.")
                        return

                    focus_game_window(window_keyword)
                    pyautogui.click()  # to focus game window
                    pyautogui.press('e')
                    print("👇Pressed E to extract the honey")

                    self.update_status_signal.emit("Cycle complete. Bot window on top.")

                    time.sleep(1)
                else:
                    for i in range(10, 0, -1):
                        if bot_stop_event.is_set():
                            self.update_status_signal.emit("Bot stopped.")
                            return
                        self.update_status_signal.emit(f"No item. Retrying in {i}s...")
                        time.sleep(1)
            except Exception as e:
                print(f"Error in run_bot loop: {e}")
                bot_running = False
                self.update_status_signal.emit(f"Error occurred: {e}")
                return

    def stop_bot(self):
        global bot_running, bot_stop_event
        bot_running = False
        bot_stop_event.set()

        self.status_label.setText("Stopping bot, please wait...")

        # Wait for the thread to finish, with timeout so UI doesn't freeze
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=2)

        self.status_label.setText("Bot stopped.")

        self.start_button.show()
        self.pick_button.show()
        self.stop_button.hide()

        self.showNormal()
        self.raise_()

    def closeEvent(self, event):
        self.stop_bot()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = BotWindow()
    window.show()
    sys.exit(app.exec_())
