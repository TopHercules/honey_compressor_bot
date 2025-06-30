import pyautogui
import time
import threading
import tkinter as tk
from pynput import mouse
from PIL import ImageGrab
import numpy as np
import pygetwindow as gw
import platform
import subprocess

# === BOT CONFIG ===
START_X, START_Y = 560, 740

# Adjust item size based on screen resolution
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

def focus_game_window(window_keyword='Grow'):
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
        # Fallback for Windows (if run cross-platform)
        import pygetwindow as gw
        for w in gw.getWindowsWithTitle(window_keyword):
            try:
                w.activate()
                return True
            except:
                pass
        return False

def update_status(label, text):
    label.after(0, lambda: label.config(text=text))

def run_bot(status_label, window):
    global bot_running
    while bot_running and not bot_stop_event.is_set():
        print(f"👉 Using START_X={START_X}, START_Y={START_Y}")
        item_pos = find_valid_item()
        if item_pos:
            update_status(status_label, "Clicking item and pressing E...")
            pyautogui.click(item_pos)
            time.sleep(0.3)
            print("👇Pressed E to give plant")
            pyautogui.press('e')

            window.deiconify()
            window.lift()
            window.attributes('-topmost', True)
            window.after(500, lambda: window.attributes('-topmost', False))

            for i in range(WAIT_TIME):
                if bot_stop_event.is_set():
                    update_status(status_label, "Bot stopped.")
                    return
                update_status(status_label, f"Waiting {WAIT_TIME - i}s...")
                time.sleep(1)
            
            focus_game_window()  # focus again before pressing E
            pyautogui.click()
            print("👇Pressed E to extract the honey")
            pyautogui.press('e')

            if bot_stop_event.is_set():
                update_status(status_label, "Bot stopped.")
                return

            window.withdraw()
            update_status(status_label, "Cycle complete. Restarting...")
            time.sleep(1)
        else:
            for i in range(10, 0, -1):
                if bot_stop_event.is_set():
                    update_status(status_label, "Bot stopped.")
                    return
                update_status(status_label, f"No item. Retrying in {i}s...")
                time.sleep(1)

def start_bot(status_label, window, start_button, pick_button, stop_button):
    global bot_running, bot_stop_event, position_selected

    if not position_selected:
        update_status(status_label, "⚠️ Please pick a position first.")
        return

    if not bot_running:
        bot_running = True
        bot_stop_event.clear()
        update_status(status_label, "Bot starting in 5s...")

        start_button.pack_forget()
        pick_button.pack_forget()
        stop_button.pack(pady=5)

        window.lift()
        window.attributes('-topmost', True)
        window.after(500, lambda: window.attributes('-topmost', False))
        window.after(1000, focus_game_window)

        threading.Thread(target=delayed_start, args=(status_label, window), daemon=True).start()

def delayed_start(status_label, window):
    for i in range(5, 0, -1):
        update_status(status_label, f"Bot starting in {i}s...")
        time.sleep(1)
    window.withdraw()
    run_bot(status_label, window)

def stop_bot(status_label, start_button, pick_button, stop_button, window):
    global bot_running, bot_stop_event
    bot_running = False
    bot_stop_event.set()
    update_status(status_label, "Bot stopped.")

    start_button.pack(pady=5)
    pick_button.pack(pady=5)
    stop_button.pack_forget()

    window.deiconify()
    window.lift()

def pick_position(coord_label, window):
    global START_X, START_Y, position_selected

    def on_click(x, y, button, pressed):
        global START_X, START_Y, position_selected
        if pressed:
            START_X, START_Y = x, y
            position_selected = True
            coord_label.config(text=f"Start Position: ({START_X}, {START_Y})")
            print(f"✅ Picked: ({START_X}, {START_Y})")

            window.deiconify()
            window.lift()
            window.attributes('-topmost', True)
            window.after(100, lambda: window.attributes('-topmost', False))

            listener.stop()
            return False

    window.withdraw()
    print("👆 Click to set the start position")
    listener = mouse.Listener(on_click=on_click)
    listener.start()

def create_gui():
    window = tk.Tk()
    window.title("Grow Garden Honey Bot")
    window.geometry("360x240")
    window.resizable(False, False)

    title_label = tk.Label(window, text="🍯 Honey Compressor Bot", font=("Arial", 14, "bold"))
    title_label.pack(pady=10)

    coord_label = tk.Label(window, text=f"Start Position: ({START_X}, {START_Y})", fg="green")
    coord_label.pack(pady=2)

    status_label = tk.Label(window, text="Status: Waiting to start...", fg="blue")
    status_label.pack(pady=5)

    pick_button = tk.Button(window, text="📌 Pick Item Position", width=25)
    pick_button.config(command=lambda: pick_position(coord_label, window))
    pick_button.pack(pady=5)

    stop_button = tk.Button(window, text="▣ Stop Bot", width=25)
    stop_button.config(command=lambda: stop_bot(status_label, start_button, pick_button, stop_button, window))

    def start_bot_callback():
        start_bot(status_label, window, start_button, pick_button, stop_button)

    start_button = tk.Button(window, text="▶ Start Bot", width=25)
    start_button.config(command=start_bot_callback)
    start_button.pack(pady=5)

    def on_close():
        stop_bot(status_label, start_button, pick_button, stop_button, window)
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_close)
    window.mainloop()

# === RUN ===
if __name__ == "__main__":
    create_gui()