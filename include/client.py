# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import queue
import socket
import sys
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, QRect, QTimer, Qt, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QTextEdit, QWidget

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 50007
PORTRAIT_DIR = Path(r"D:\Codex_quanzhi\character_illustrations")
BUTTON_POSITIONS = [(40, 520), (215, 520), (390, 520), (565, 520), (40, 580), (215, 580), (390, 580), (565, 580)]

class ArrowWidget(QWidget):
    def __init__(self, parent=None, direction: str = "left", callback=None):
        super().__init__(parent)
        self.direction = direction
        self.callback = callback
        self.hovered = False
        self.pressed = False
        self.setFixedSize(20, 40)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        fill = QColor(200, 200, 200)
        if self.pressed:
            fill = QColor(140, 140, 140)
        elif self.hovered:
            fill = QColor(170, 170, 170)
        painter.setBrush(fill)
        painter.setPen(QPen(Qt.black, 2))
        if self.direction == "left":
            points = [QPoint(1, self.height() // 2), QPoint(self.width() - 1, 1), QPoint(self.width() - 1, self.height() - 1)]
        else:
            points = [QPoint(self.width() - 1, self.height() // 2), QPoint(1, 1), QPoint(1, self.height() - 1)]
        painter.drawPolygon(points)

    def enterEvent(self, event):
        self.hovered = True
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.pressed = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.callback:
            self.pressed = True
            self.update()

    def mouseReleaseEvent(self, event):
        was_pressed = self.pressed
        self.pressed = False
        self.update()
        if (
            was_pressed
            and event.button() == Qt.LeftButton
            and self.callback
            and self.rect().contains(event.position().toPoint())
        ):
            self.callback()

class PortraitCard(QWidget):
    def __init__(self, parent=None, callback=None):
        super().__init__(parent)
        self.callback = callback
        self.player_data: Optional[dict] = None
        self.pixmap: Optional[QPixmap] = None
        self.interactive = False
        self.hovered = False
        self.pressed = False
        self.setGeometry(0, 0, 150, 225)
        self.setMouseTracking(True)

    def set_player(self, player: Optional[dict]):
        self.player_data = player
        self.pixmap = None
        if player is not None:
            image_path = PORTRAIT_DIR / f"{player['role_name']}.png"
            if image_path.exists():
                self.pixmap = QPixmap(str(image_path))
        self.update()

    def set_interactive(self, interactive: bool):
        self.interactive = interactive
        if not interactive:
            self.hovered = False
            self.pressed = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(244, 244, 240))
        if self.player_data is None:
            painter.setPen(QColor(150, 150, 150))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
            return
        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        painter.fillRect(0, self.height() - 36, self.width(), 36, QColor(248, 248, 245, 220))
        painter.setPen(Qt.black)
        painter.drawText(QRect(4, self.height() - 34, self.width() - 8, 16), Qt.AlignLeft | Qt.AlignVCenter, self.player_data["role_name"])
        hp_text = f"HP {self.player_data['current_hp']}/{self.player_data['max_hp']}"
        painter.drawText(QRect(4, self.height() - 18, self.width() - 8, 14), Qt.AlignLeft | Qt.AlignVCenter, hp_text)
        if not self.player_data["alive"]:
            painter.fillRect(self.rect(), QColor(255, 255, 255, 120))
        if self.interactive:
            if self.pressed:
                painter.fillRect(self.rect(), QColor(120, 120, 120, 90))
            elif self.hovered:
                painter.fillRect(self.rect(), QColor(170, 170, 170, 70))
        if self.player_data.get("is_current_actor"):
            painter.setPen(QPen(QColor(255, 220, 90), 3))
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        else:
            painter.setPen(QPen(QColor(160, 160, 160), 1))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def enterEvent(self, event):
        if self.interactive:
            self.hovered = True
            self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.pressed = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.callback and self.player_data is not None and self.interactive:
            self.pressed = True
            self.update()

    def mouseReleaseEvent(self, event):
        was_pressed = self.pressed
        self.pressed = False
        self.update()
        if (
            was_pressed
            and event.button() == Qt.LeftButton
            and self.callback
            and self.player_data is not None
            and self.interactive
            and self.rect().contains(event.position().toPoint())
        ):
            self.callback(self.player_data["id"])

class MainWindow(QWidget):
    def __init__(self, host: str, port: int, name: str, team: str, character: str):
        super().__init__()
        self.host = host
        self.port = port
        self.profile = {"name": name.strip(), "team": team.strip(), "character": character.strip()}
        self.pending_fields = [field for field in ("name", "team", "character") if not self.profile[field]]
        self.current_prompt: Optional[str] = None
        self.sock: Optional[socket.socket] = None
        self.closed = threading.Event()
        self.readqueue: "queue.Queue[dict]" = queue.Queue()
        self.connect_result_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.send_lock = threading.Lock()
        self.connected = False
        self.connecting = False
        self.server_state = {"game_active": False, "players": [], "can_act": False, "can_view": False, "formal_actions": [], "turn_id": 0}
        self.ui_mode = "locked"
        self.pending_action: Optional[dict] = None
        self.action_page = 0
        self.portrait_page = 0
        self.chat_scope = "all"
        self.setGeometry(100, 100, 1120, 640)
        self.setWindowTitle("全职")
        self.setObjectName("mainWindow")
        self.setStyleSheet("#mainWindow { background-color: rgb(244,244,240); color: black; }")

        self.left_arrow = ArrowWidget(self, "left", self._prev_portrait_page)
        self.left_arrow.setGeometry(22, 112, 20, 40)
        self.right_arrow = ArrowWidget(self, "right", self._next_portrait_page)
        self.right_arrow.setGeometry(718, 112, 20, 40)
        self.portraits: list[PortraitCard] = []
        for pos in [(44, 20), (218, 20), (392, 20), (566, 20)]:
            card = PortraitCard(self, self._on_portrait_clicked)
            card.setGeometry(pos[0], pos[1], 150, 225)
            self.portraits.append(card)

        self.left_output = QTextEdit(self)
        self.left_output.setReadOnly(True)
        self.left_output.setGeometry(20, 265, 720, 245)
        self.right_output = QTextEdit(self)
        self.right_output.setReadOnly(True)
        self.right_output.setGeometry(780, 20, 320, 550)
        self.scope_button = QPushButton("全部", self)
        self.scope_button.setGeometry(780, 590, 45, 30)
        self.scope_button.clicked.connect(self._toggle_scope)
        self.input_line = QLineEdit(self)
        self.input_line.setGeometry(830, 590, 270, 30)
        self.input_line.returnPressed.connect(self.on_input_entered)
        self.action_buttons: list[QPushButton] = []
        for pos in BUTTON_POSITIONS:
            button = QPushButton(self)
            button.setGeometry(pos[0], pos[1], 155, 50)
            button.clicked.connect(self._on_action_button)
            self.action_buttons.append(button)
        self.bottom_prev = ArrowWidget(self, "left", self._prev_action_page)
        self.bottom_prev.setGeometry(10, 555, 20, 40)
        self.bottom_next = ArrowWidget(self, "right", self._next_action_page)
        self.bottom_next.setGeometry(730, 555, 20, 40)
        self._apply_text_styles()
        self._refresh_portraits()
        self._refresh_buttons()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_queues)
        self.timer.start(50)
        QTimer.singleShot(0, self._begin_setup)

    def _apply_text_styles(self):
        common = "background:#f8f8f5;color:#111;border:1px solid #b8b8b8;"
        self.left_output.setStyleSheet(common)
        self.right_output.setStyleSheet(common)
        self.input_line.setStyleSheet("background:#ffffff;color:#111;border:1px solid #b8b8b8;")
        button_style = (
            "QPushButton { background:#deded8; color:#111; border:2px solid black; }"
            "QPushButton:hover { background:#bdbdb8; }"
            "QPushButton:pressed { background:#9a9a96; }"
        )
        small_button_style = (
            "QPushButton { background:#ecece7; color:#111; border:1px solid #b8b8b8; }"
            "QPushButton:hover { background:#cfcfc9; }"
            "QPushButton:pressed { background:#b3b3ae; }"
        )
        self.scope_button.setStyleSheet(small_button_style)
        for button in self.action_buttons:
            button.setStyleSheet(button_style)

    def _append_chat(self, text: str):
        self.right_output.append(text)

    def _append_battle(self, text: str):
        self.left_output.append(text)

    def _begin_setup(self):
        self._append_chat(f"服务器：{self.host}:{self.port}")
        self._append_chat("请在下方输入连接信息。")
        self._prompt_next_field()

    def _prompt_next_field(self):
        if self.pending_fields:
            self.current_prompt = self.pending_fields.pop(0)
            prompt_map = {"name": "请输入昵称：", "team": "请输入队伍名：", "character": "请输入角色名或角色ID："}
            placeholder_map = {"name": "输入昵称", "team": "输入队伍名", "character": "输入角色名或ID"}
            self._append_chat(prompt_map[self.current_prompt])
            self.input_line.setEnabled(True)
            self.input_line.setPlaceholderText(placeholder_map[self.current_prompt])
            self.input_line.setFocus()
            return
        self.current_prompt = "connecting"
        self._schedule_connection_attempt()

    def _schedule_connection_attempt(self):
        if self.connecting:
            return
        self.connecting = True
        self.input_line.setEnabled(False)
        self.input_line.setPlaceholderText("正在连接服务器...")
        self._append_chat(f"正在连接 {self.host}:{self.port} ...")
        worker = threading.Thread(target=self._attempt_connection, daemon=True, name="client-connect")
        worker.start()

    def _attempt_connection(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))
            with self.send_lock:
                sock.sendall((self.profile["name"] + "\n" + self.profile["team"] + "\n" + self.profile["character"] + "\n").encode("utf-8"))
        except OSError as exc:
            try:
                sock.close()
            except OSError:
                pass
            self.connect_result_queue.put(("error", str(exc)))
            return
        self.connect_result_queue.put(("success", sock))
    def _reader_loop(self, sock: socket.socket):
        with sock.makefile("r", encoding="utf-8") as file_obj:
            while not self.closed.is_set():
                try:
                    line = file_obj.readline()
                except (ConnectionResetError, ConnectionAbortedError, OSError):
                    break
                if not line:
                    break
                try:
                    payload = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                self.readqueue.put(payload)
        if not self.closed.is_set():
            self.readqueue.put({"type": "chat_log", "text": "服务端断开连接，游戏结束……"})
        self.closed.set()

    def _handle_connect_result(self, status: str, payload: object):
        self.connecting = False
        if status == "error":
            self.current_prompt = "retry"
            self.input_line.setEnabled(True)
            self._append_chat(f"连接服务器失败：{payload}")
            self._append_chat("输入 Y 或 y 重试，输入其他内容则退出。")
            self.input_line.setPlaceholderText("输入 Y 重试，否则退出")
            self.input_line.setFocus()
            return
        self.sock = payload
        self.connected = True
        self.current_prompt = None
        self.input_line.setEnabled(True)
        self.input_line.setPlaceholderText("输入聊天信息...")
        self.input_line.setFocus()
        self._append_chat("连接成功，已加入房间。")
        threading.Thread(target=self._reader_loop, args=(self.sock,), daemon=True, name="client-reader").start()

    def _send_json(self, payload: dict):
        if self.sock is None:
            return
        data = json.dumps(payload, ensure_ascii=False) + "\n"
        with self.send_lock:
            self.sock.sendall(data.encode("utf-8"))

    def _toggle_scope(self):
        self.chat_scope = "team" if self.chat_scope == "all" else "all"
        self.scope_button.setText("队伍" if self.chat_scope == "team" else "全部")

    def _visible_players(self) -> list[dict]:
        players = self.server_state.get("players", [])
        start = self.portrait_page * 4
        return players[start : start + 4]

    def _refresh_portraits(self):
        players = self.server_state.get("players", [])
        page_count = max(1, (len(players) + 3) // 4) if players else 1
        self.portrait_page = max(0, min(self.portrait_page, page_count - 1))
        visible = self._visible_players()
        for index, card in enumerate(self.portraits):
            player = visible[index] if index < len(visible) else None
            card.set_player(player)
            if player is None:
                card.set_interactive(False)
            elif self.ui_mode == "view_select":
                card.set_interactive(True)
            elif self.ui_mode == "target_select":
                card.set_interactive(bool(player.get("alive")))
            else:
                card.set_interactive(False)
        show_arrows = len(players) > 4
        self.left_arrow.setVisible(show_arrows)
        self.right_arrow.setVisible(show_arrows)

    def _button_defs(self) -> list[tuple[str, str]]:
        if self.ui_mode == "base":
            return [("查看", "view"), ("出招", "formal_open"), ("行动", "behavior_open"), ("解除", "release_todo")]
        if self.ui_mode == "spectator":
            return [("查看", "view")] if self.server_state.get("can_view") else []
        if self.ui_mode == "view_select":
            return [("返回", "back")]
        if self.ui_mode == "view_result":
            return [("确认", "confirm_view")]
        if self.ui_mode == "formal_menu":
            actions = self.server_state.get("formal_actions", [])
            page_size = 7
            start = self.action_page * page_size
            defs = [(entry["label"], f"formal::{start + idx}") for idx, entry in enumerate(actions[start : start + page_size])]
            defs.append(("返回", "back"))
            return defs
        if self.ui_mode == "action_menu":
            return [("到你身边", "behavior:approach"), ("离你远点", "behavior:away"), ("寻找", "behavior:search"), ("嘲讽", "behavior:taunt"), ("返回", "back")]
        if self.ui_mode == "target_select":
            return [("返回", "back")]
        return []

    def _refresh_buttons(self):
        defs = self._button_defs()
        for button, item in zip(self.action_buttons, defs):
            button.setText(item[0])
            button.setProperty("action_value", item[1])
            button.show()
        for button in self.action_buttons[len(defs):]:
            button.hide()
            button.setProperty("action_value", None)
        formal_actions = self.server_state.get("formal_actions", [])
        show_bottom_page = self.ui_mode == "formal_menu" and len(formal_actions) > 7
        page_count = max(1, (len(formal_actions) + 6) // 7) if formal_actions else 1
        self.action_page = max(0, min(self.action_page, page_count - 1))
        self.bottom_prev.setVisible(show_bottom_page and self.action_page > 0)
        self.bottom_next.setVisible(show_bottom_page and self.action_page < page_count - 1)

    def _reset_ui_mode(self):
        if self.server_state.get("game_active"):
            self.ui_mode = "base" if self.server_state.get("can_act") else ("spectator" if self.server_state.get("can_view") else "locked")
        else:
            self.ui_mode = "locked"
        self.pending_action = None
        self.action_page = 0
        self._refresh_buttons()
        self._refresh_portraits()

    def _apply_state(self, payload: dict):
        turn_changed = payload.get("turn_id") != self.server_state.get("turn_id")
        self.server_state = payload
        if turn_changed or not payload.get("can_act") or not payload.get("game_active"):
            self._reset_ui_mode()
        else:
            self._refresh_buttons()
        self._refresh_portraits()

    def _prev_portrait_page(self):
        if self.portrait_page > 0:
            self.portrait_page -= 1
            self._refresh_portraits()

    def _next_portrait_page(self):
        if (self.portrait_page + 1) * 4 < len(self.server_state.get("players", [])):
            self.portrait_page += 1
            self._refresh_portraits()

    def _prev_action_page(self):
        if self.action_page > 0:
            self.action_page -= 1
            self._refresh_buttons()

    def _next_action_page(self):
        if (self.action_page + 1) * 7 < len(self.server_state.get("formal_actions", [])):
            self.action_page += 1
            self._refresh_buttons()

    def _submit_intent(self, intent: dict):
        self._send_json({"type": "submit", "turn_id": self.server_state.get("turn_id"), "intent": intent})
        self.ui_mode = "locked"
        self.pending_action = None
        self._refresh_buttons()
        self._refresh_portraits()

    def _handle_setup_input(self, message: str):
        self._append_chat(f"> {message}")
        if self.current_prompt in ("name", "team", "character"):
            self.profile[self.current_prompt] = message
            self._prompt_next_field()
            return
        if self.current_prompt == "retry":
            if message.lower() == "y":
                self.current_prompt = "connecting"
                self._schedule_connection_attempt()
            else:
                self.close()
            return
        self._append_chat("当前不需要这条输入。")

    @Slot()
    def on_input_entered(self):
        message = self.input_line.text().strip()
        if not message:
            return
        self.input_line.clear()
        if not self.connected:
            self._handle_setup_input(message)
            return
        try:
            self._send_json({"type": "chat", "scope": self.chat_scope, "text": message})
        except OSError as exc:
            self._append_chat(f"发送聊天失败：{exc}")
    def _on_action_button(self):
        button = self.sender()
        value = button.property("action_value")
        if not value:
            return
        if value == "view":
            self.ui_mode = "view_select"
        elif value == "formal_open":
            self.ui_mode = "formal_menu"
            self.action_page = 0
        elif value == "behavior_open":
            self.ui_mode = "action_menu"
        elif value == "release_todo":
            self._append_battle("TODO！")
        elif value in ("back", "confirm_view"):
            self._reset_ui_mode()
        elif value.startswith("formal::"):
            index = int(value.split("::", 1)[1])
            actions = self.server_state.get("formal_actions", [])
            if index >= len(actions):
                return
            action = actions[index]
            if action.get("requires_target"):
                self.pending_action = {"category": "formal_action", "action": action["action"]}
                self.ui_mode = "target_select"
            else:
                self._submit_intent({"category": "formal_action", "action": action["action"]})
                return
        elif value == "behavior:away":
            self._submit_intent({"category": "behavior", "behavior": "away"})
            return
        elif value == "behavior:taunt":
            self._submit_intent({"category": "behavior", "behavior": "taunt"})
            return
        elif value == "behavior:approach":
            self.pending_action = {"category": "behavior", "behavior": "approach"}
            self.ui_mode = "target_select"
        elif value == "behavior:search":
            self.pending_action = {"category": "behavior", "behavior": "search"}
            self.ui_mode = "target_select"
        self._refresh_buttons()
        self._refresh_portraits()

    def _find_player(self, player_id: int) -> Optional[dict]:
        for player in self.server_state.get("players", []):
            if player["id"] == player_id:
                return player
        return None

    def _on_portrait_clicked(self, player_id: int):
        player = self._find_player(player_id)
        if player is None:
            return
        if self.ui_mode == "view_select":
            self._send_json({"type": "view", "target_id": player_id})
            self.ui_mode = "view_result"
            self._refresh_buttons()
            return
        if self.ui_mode != "target_select" or self.pending_action is None:
            return
        if not player.get("alive"):
            return
        payload = dict(self.pending_action)
        payload["target_id"] = player_id
        self._submit_intent(payload)

    def _poll_queues(self):
        try:
            while True:
                status, payload = self.connect_result_queue.get(block=False)
                self._handle_connect_result(status, payload)
        except queue.Empty:
            pass
        try:
            while True:
                payload = self.readqueue.get(block=False)
                msg_type = payload.get("type")
                if msg_type == "state":
                    self._apply_state(payload.get("payload") or {})
                elif msg_type == "chat":
                    self._append_chat(payload.get("text", ""))
                elif msg_type == "chat_log":
                    self._append_chat(payload.get("text", ""))
                elif msg_type == "battle_log":
                    self._append_battle(payload.get("text", ""))
        except queue.Empty:
            pass
        if self.closed.is_set():
            self.close()

    def closeEvent(self, event):
        self.closed.set()
        try:
            if self.sock is not None:
                self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            if self.sock is not None:
                self.sock.close()
        except OSError:
            pass
        super().closeEvent(event)

def parse_args():
    parser = argparse.ArgumentParser(description="Quanzhi 联网客户端")
    parser.add_argument("--host", default=DEFAULT_HOST, help="服务端地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="服务端端口")
    parser.add_argument("--name", default="", help="昵称")
    parser.add_argument("--team", default="", help="队伍名")
    parser.add_argument("--character", default="", help="角色名或角色ID")
    return parser.parse_args()

def main():
    args = parse_args()
    app = QApplication(sys.argv)
    window = MainWindow(host=args.host, port=args.port, name=args.name, team=args.team, character=args.character)
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
