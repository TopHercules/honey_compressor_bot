from pynput import mouse
from PyQt5 import QtWidgets
import sys

class TestWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test")
        self.setFixedSize(200, 100)
        self.button = QtWidgets.QPushButton("Pick Position", self)
        self.button.clicked.connect(self.pick_position)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.button)
        self.setLayout(layout)

    def pick_position(self):
        self.hide()
        def on_click(x, y, button, pressed):
            if pressed:
                print("Picked:", x, y)
                self.showNormal()
                self.raise_()
                listener.stop()
                return False

        listener = mouse.Listener(on_click=on_click)
        listener.start()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = TestWindow()
    w.show()
    sys.exit(app.exec_())
