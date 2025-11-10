import socket
import threading
import queue
import sys
from PySide6.QtWidgets import QApplication, QWidget, QTextEdit, QLineEdit
from PySide6.QtCore import QTimer, Slot, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter
import pygame
HOST = 'frp-oil.com'
PORT = 63867
started = threading.Event()
closed = threading.Event()
readqueue = queue.Queue()
quandict = {"剪刀":"0","石头":"1","布":"2"}

def reader(s):
    with s.makefile('r', encoding='utf-8') as f:
        while True:
            msg = f.readline().strip()
            if msg == "游戏开始！":
                started.set()
            if not msg:
                break
            readqueue.put(msg)
    if not closed.is_set():
        print("服务端断开连接！游戏结束……")
    closed.set()


class PygButton:
    def __init__(self, topleft, size, text='', bg=(200,200,200), down=(140,140,140), text_color=(0,0,0)):
        self.rect = pygame.Rect(topleft, size)
        self.text = text
        self.bg = bg
        self.down = down
        self.text_color = text_color
        self._down = False

    def draw(self, surf, font):
        color = self.bg
        if self._down:
            color = self.down
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        pygame.draw.rect(surf, (0,0,0), self.rect, 2, border_radius=6)
        if self.text:
            txt_surf = font.render(self.text, True, self.text_color)
            tr = txt_surf.get_rect(center=self.rect.center)
            surf.blit(txt_surf, tr)

    def handle_mouse_down(self, pos, button=1):
        if started.is_set() and button == 1 and self.rect.collidepoint(pos):
            self._down = True
            return True
        return False

    def handle_mouse_up(self, pos, button=1):
        clicked = False
        if button == 1:
            if self._down and self.rect.collidepoint(pos):
                clicked = True
            self._down = False
        return clicked

class PygameArea(QWidget):
    def __init__(self, parent=None, geom=QRect(50, 580, 651, 50)):
        super().__init__(parent)
        self.setGeometry(geom)
        self.w = geom.width()
        self.h = geom.height()

        pygame.font.init()
        self.font = pygame.font.SysFont("SimHei", 24)

        self.surface = pygame.Surface((self.w, self.h))

        btn_size = (197, 50)
        global_positions = [(50, 580), (277, 580), (504, 580)]
        topleft = (geom.x(), geom.y())
        rel_positions = [(x - topleft[0], y - topleft[1]) for (x,y) in global_positions]
        labels = ["剪刀", "石头", "布"]
        self.buttons = [PygButton(pos, btn_size, text=lab) for pos, lab in zip(rel_positions, labels)]

        self._qpix = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timeout)
        self.timer.start(30)

        self.on_button_clicked = None

    def on_timeout(self):
        self.render_frame()
        self.update()

    def render_frame(self):
        self.surface.fill((240,240,240))

        for b in self.buttons:
            b.draw(self.surface, self.font)

        raw = pygame.image.tostring(self.surface, "RGBA", False)
        qimg = QImage(raw, self.w, self.h, QImage.Format_RGBA8888)
        self._qpix = QPixmap.fromImage(qimg)

    def paintEvent(self, ev):
        painter = QPainter(self)
        if self._qpix:
            painter.drawPixmap(0, 0, self._qpix)

    def _map_pos(self, qpos):
        return (int(qpos.x()), int(qpos.y()))


    def mousePressEvent(self, ev):
        pos = self._map_pos(ev.position().toPoint())
        for b in self.buttons:
            b.handle_mouse_down(pos, button=1)

    def mouseReleaseEvent(self, ev):
        pos = self._map_pos(ev.position().toPoint())
        for b in self.buttons:
            if b.handle_mouse_up(pos, button=1):
                if callable(self.on_button_clicked):
                    self.on_button_clicked(b.text)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1120, 640)
        self.setWindowTitle("全职")
        self.setObjectName("mainWindow")
        self.setStyleSheet("#mainWindow { background-color: rgb(240,240,240); }")

        self.left_output = QTextEdit(self)
        self.left_output.setReadOnly(True)
        self.left_output.setGeometry(20, 20, 711, 550)

        self.right_output = QTextEdit(self)
        self.right_output.setReadOnly(True)
        self.right_output.setGeometry(780, 20, 320, 550)

        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("输入聊天信息…")
        self.input_line.setGeometry(780, 590, 320, 30)
        self.input_line.returnPressed.connect(self.on_input_entered)

        btn_region = QRect(50, 580, 651, 50)
        self.pyg_area = PygameArea(self, geom=btn_region)
        self.pyg_area.on_button_clicked = self.on_pyg_button_clicked

        self._close_timer = QTimer(self)
        self._close_timer.timeout.connect(self._check_closed_event)
        self._close_timer.start(100)

    @Slot()
    def on_input_entered(self):
        msg = self.input_line.text().strip()
        if msg:
            s.sendall(("/q " + msg + "\n").encode('utf-8'))
            self.input_line.clear()

    def on_pyg_button_clicked(self, label):
        msg = quandict[label]
        s.sendall((msg + "\n").encode('utf-8'))

    def _check_closed_event(self):
        try:
            msg = readqueue.get(block=False)
            if msg.startswith("/q") or msg.startswith("/d"):
                self.right_output.append(msg[2:].strip())
            else:
                self.left_output.append(msg)
        except queue.Empty:
            pass

        if closed.is_set():
            self.close()


if __name__ == '__main__':
    name = str(input("请输入昵称：")).strip()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.sendall((name + "\n").encode('utf-8'))
    t = threading.Thread(target=reader, args=(s,), name="reader")
    t.start()

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec()
    closed.set()
    s.shutdown(socket.SHUT_RDWR)