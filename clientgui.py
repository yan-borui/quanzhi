import socket
import threading
import queue
import sys
from PySide6.QtWidgets import QApplication, QWidget, QTextEdit, QLineEdit
from PySide6.QtCore import Qt, QTimer, Slot, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter
import pygame
debug = False

if debug:
    HOST = '127.0.0.1'
    PORT = 50007
else:
    HOST = 'frp-oil.com'
    PORT = 63867

closed = threading.Event()
readqueue = queue.Queue()
sendlock = threading.Lock()
quandict = {"剪刀": "0", "石头": "1", "布": "2"}


def reader(s):
    with s.makefile('r', encoding='utf-8') as f:
        while True:
            try:
                msg = f.readline().strip()
            except (ConnectionResetError, ConnectionAbortedError):
                break
            if not msg:
                break
            readqueue.put(msg)
    if not closed.is_set():
        print("服务端断开连接！游戏结束……")
    closed.set()


class PygameButton:
    def __init__(self, topleft=(0, 0), text=("", ""), buttontype=0, bg=(200, 200, 200), hover=(170, 170, 170),
                 down=(140, 140, 140), text_color=(0, 0, 0)):
        size = (155, 50)
        if buttontype:
            PAx = 10
            PAy = 520
            if buttontype == 1:
                topleft = (10 - PAx, 555 - PAy)
                size = (20, 40)
            elif buttontype == 2:
                topleft = (730 - PAx, 555 - PAy)
                size = (20, 40)
            elif buttontype == 3:
                topleft = (780 - PAx, 590 - PAy)
                size = (50, 30)
                text = ("全部", "")
        self.buttontype = buttontype
        self.rect = pygame.Rect(topleft, size)
        self.display = text[0]
        self.send = text[1]
        self.bg = bg
        self.hover = hover
        self.down = down
        self.text_color = text_color
        self._down = False
        self._hover = False

    def draw(self, surf, font):
        color = self.bg
        if self._down:
            color = self.down
        elif self._hover:
            color = self.hover
        if self.buttontype:
            if self.buttontype == 1:
                pygame.draw.polygon(surf, color, [self.rect.midleft, self.rect.topright, self.rect.bottomright])
                pygame.draw.polygon(surf, (0, 0, 0), [self.rect.midleft, self.rect.topright, self.rect.bottomright], 2)
            elif self.buttontype == 2:
                pygame.draw.polygon(surf, color, [self.rect.midright, self.rect.topleft, self.rect.bottomleft])
                pygame.draw.polygon(surf, (0, 0, 0), [self.rect.midright, self.rect.topleft, self.rect.bottomleft], 2)
            elif self.buttontype == 3:
                pygame.draw.rect(surf, color, self.rect, border_radius=6)
                pygame.draw.rect(surf, (0, 0, 0), self.rect, 2, border_radius=6)
        else:
            pygame.draw.rect(surf, color, self.rect, border_radius=6)
            pygame.draw.rect(surf, (0, 0, 0), self.rect, 2, border_radius=6)
        if self.display:
            txt_surf = font.render(self.display, True, self.text_color)
            tr = txt_surf.get_rect(center=self.rect.center)
            surf.blit(txt_surf, tr)

    def handle_mouse_down(self, pos):
        if self.rect.collidepoint(pos):
            self._down = True
        return

    def handle_mouse_up(self, pos):
        clicked = self._down and self.rect.collidepoint(pos)
        self._down = False
        return clicked

    def handle_mouse_hover(self, pos):
        self._hover = self.rect.collidepoint(pos)


class PygameArea(QWidget):
    def __init__(self, parent=None, geom=QRect(10, 520, 820, 110)):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setGeometry(geom)
        self.w = geom.width()
        self.h = geom.height()

        pygame.font.init()
        self.font = pygame.font.SysFont("SimHei", 24)
        self.surface = pygame.Surface((self.w, self.h))

        global_positions = [(40, 520), (215, 520), (390, 520), (565, 520), (40, 580), (215, 580), (390, 580),
                            (565, 580)]
        topleft = (geom.x(), geom.y())
        self.rel_positions = [(x - topleft[0], y - topleft[1]) for (x, y) in global_positions]
        self.texts = []
        self.chatmode = "q"
        self.update_button(1)

        self._qpix = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timeout)
        self.timer.start(30)

        self.on_button_clicked = None

    def update_button(self, page):
        self.buttons = [PygameButton(buttontype=3)]
        if self.chatmode == "d":
            self.buttons[0].display = "队伍"
        self.page = page
        for pos, text in zip(self.rel_positions, self.texts[(page - 1) * 8:]):
            self.buttons.append(PygameButton(pos, text))
        buttonnum = len(self.texts)
        self.pagemax = (buttonnum + 6) // 8
        if self.page > 1:
            self.buttons.append(PygameButton(buttontype=1))
        if self.pagemax > page:
            self.buttons.append(PygameButton(buttontype=2))

    def on_timeout(self):
        try:
            self.render_frame()
            self.update()
        except KeyboardInterrupt:
            closed.set()

    def render_frame(self):
        self.surface.fill((240, 240, 240))
        # print(len(self.buttons))
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
        if ev.button() == Qt.LeftButton:
            pos = self._map_pos(ev.position().toPoint())
            for b in self.buttons:
                b.handle_mouse_down(pos)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            pos = self._map_pos(ev.position().toPoint())
            for b in self.buttons:
                if b.handle_mouse_up(pos):
                    if b.buttontype:
                        if b.buttontype == 1:
                            self.update_button(self.page - 1)
                        elif b.buttontype == 2:
                            self.update_button(self.page + 1)
                        elif b.buttontype == 3:
                            if self.chatmode == "q":
                                self.chatmode = "d"
                                self.buttons[0].display = "队伍"
                            else:
                                self.chatmode = "q"
                                self.buttons[0].display = "全部"

                    else:
                        self.texts = []
                        self.update_button(1)
                        self.page = 1
                        with sendlock:
                            s.sendall((b.send + "\n").encode('utf-8'))
                    break

    def mouseMoveEvent(self, ev):
        pos = self._map_pos(ev.position().toPoint())
        for b in self.buttons:
            b.handle_mouse_hover(pos)

    def leaveEvent(self, ev):
        for b in self.buttons:
            b._hover = False


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1120, 640)
        self.setWindowTitle("全职")
        self.setObjectName("mainWindow")
        self.setStyleSheet("#mainWindow { background-color: rgb(240,240,240); }")

        button_region = QRect(10, 520, 820, 110)
        self.pyg_area = PygameArea(self, geom=button_region)

        self.left_output = QTextEdit(self)
        self.left_output.setReadOnly(True)
        self.left_output.setGeometry(20, 20, 720, 490)

        self.right_output = QTextEdit(self)
        self.right_output.setReadOnly(True)
        self.right_output.setGeometry(780, 20, 320, 550)

        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("输入聊天信息…")
        self.input_line.setGeometry(830, 590, 270, 30)
        self.input_line.returnPressed.connect(self.on_input_entered)

        self._close_timer = QTimer(self)
        self._close_timer.timeout.connect(self._check_closed_event)
        self._close_timer.start(100)

    @Slot()
    def on_input_entered(self):
        msg = self.input_line.text().strip()
        if msg:
            with sendlock:
                if self.pyg_area.chatmode == "d":
                    s.sendall(("/d " + msg + "\n").encode('utf-8'))
                else:
                    s.sendall(("/q " + msg + "\n").encode('utf-8'))
            self.input_line.clear()

    def _check_closed_event(self):  # 兼有接受信息功能
        try:
            while True:
                msg = readqueue.get(block=False)
                if msg.startswith("/q") or msg.startswith("/d"):
                    self.right_output.append(msg[2:].strip())
                elif msg.startswith("/b"):
                    self.pyg_area.texts = []
                    msg = msg[2:].strip()
                    while msg:
                        display, send, msg = msg.split(";", 2)
                        self.pyg_area.texts.append((display, send))
                    # print(len(self.pyg_area.texts))
                    self.pyg_area.update_button(1)

                else:
                    self.left_output.append(msg)
        except queue.Empty:
            pass
        except KeyboardInterrupt:
            closed.set()

        if closed.is_set():
            self.close()


if __name__ == '__main__':
    if debug:
        name = "jk"
        team = "t1"
        character = "剑客"
    else:
        name = str(input("请输入昵称：")).strip()
        team = str(input("请输入队伍名：")).strip()
        character = str(input("请输入角色名：")).strip()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, PORT))
        with sendlock:
            s.sendall((name + "\n" + team + "\n" + character + "\n").encode('utf-8'))
        t = threading.Thread(target=reader, args=(s,), name="reader")
        t.start()

        app = QApplication(sys.argv)
        win = MainWindow()
        win.show()
        app.exec()
    finally:
        closed.set()
        s.shutdown(socket.SHUT_RDWR)
        s.close()
