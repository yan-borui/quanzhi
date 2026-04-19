# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import io
import json
import queue
import socket
import threading
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from backend.game_backend import GameBackend
from characters.ninja import Ninja
from config.game_config import get_game_config
import factory.character_init  # noqa: F401
from factory.character_factory import get_character_factory, get_character_registry

DEFAULT_HOST = ""
DEFAULT_PORT = 50007
NO_TARGET_SKILLS = {"技能:盾", "技能:一锅油", "技能:回旋斩", "技能:爆炸", "技能:忍法地心", "技能:空投", "技能:电池", "技能:制造机器人"}

@dataclass
class PlayerSession:
    conn: socket.socket
    addr: Tuple[str, int]
    name: str
    team: str
    character_request: str
    submit_queue: "queue.Queue[dict]" = field(default_factory=queue.Queue)
    send_lock: threading.Lock = field(default_factory=threading.Lock)
    connected: bool = True
    character = None
    character_id: Optional[int] = None

    def send_json(self, payload: dict):
        if not self.connected:
            return
        data = json.dumps(payload, ensure_ascii=False) + "\n"
        with self.send_lock:
            self.conn.sendall(data.encode("utf-8"))

    def close(self):
        if not self.connected:
            return
        self.connected = False
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.conn.close()
        except OSError:
            pass

@dataclass
class MatchModifiers:
    enabled: bool = False
    hp_multiplier: int = 1
    step_multiplier: int = 1
    cd_multiplier: int = 1

class NetworkGameServer:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.config = get_game_config()
        self.sessions: Dict[Tuple[str, int], PlayerSession] = {}
        self.sessions_lock = threading.RLock()
        self.game_lock = threading.RLock()
        self.stop_event = threading.Event()
        self.game_active = threading.Event()
        self.room_broken = threading.Event()
        self.server_socket: Optional[socket.socket] = None
        self.accept_thread: Optional[threading.Thread] = None
        self.backend: Optional[GameBackend] = None
        self.active_sessions: List[PlayerSession] = []
        self.character_sessions: Dict[int, PlayerSession] = {}
        self.current_actor_id: Optional[int] = None
        self.current_turn_id = 0
        self.character_id_seq = 1
        self.match_modifiers = MatchModifiers()

    def start(self):
        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True, name="server-accept")
        self.accept_thread.start()

    def shutdown(self):
        self.stop_event.set()
        self.game_active.clear()
        self.room_broken.set()
        if self.server_socket is not None:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None
        with self.sessions_lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for session in sessions:
            session.close()

    def _accept_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.host, self.port))
            server_sock.listen(10)
            server_sock.settimeout(1.0)
            self.server_socket = server_sock
            print(f"[服务端] 监听 {self.host or '0.0.0.0'}:{self.port}")
            while not self.stop_event.is_set():
                try:
                    conn, addr = server_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    if self.game_active.is_set():
                        self._safe_send_and_close(conn, {"type": "chat_log", "text": "游戏已开始，当前无法加入。"})
                        continue
                    if self.get_connected_count() >= self.config.max_players:
                        self._safe_send_and_close(conn, {"type": "chat_log", "text": f"房间已满，最多支持 {self.config.max_players} 名玩家。"})
                        continue
                    name, team, character, remaining = self._read_handshake(conn)
                    session = PlayerSession(conn=conn, addr=addr, name=name or f"玩家{self.get_connected_count() + 1}", team=team or "默认队伍", character_request=character or "")
                    with self.sessions_lock:
                        self.sessions[addr] = session
                    reader_thread = threading.Thread(target=self._reader_loop, args=(session, remaining), daemon=True, name=f"reader-{addr[0]}:{addr[1]}")
                    reader_thread.start()
                    self.send_chat_log(session, "连接成功，等待房主开始游戏。")
                    self.broadcast_public_log(f"队伍 {session.team} 的 {session.name} 加入了房间。")
                    self.broadcast_state()
                    print(f"[服务端] 玩家加入 {addr} -> {session.name} / {session.team} / {session.character_request or '未指定角色'}")
                except Exception as exc:
                    print(f"[服务端] 处理新连接失败 {addr}: {exc}")
                    try:
                        conn.close()
                    except OSError:
                        pass

    def _read_handshake(self, conn: socket.socket) -> Tuple[str, str, str, bytes]:
        conn.settimeout(10.0)
        buffer = b""
        fields: List[str] = []
        while len(fields) < 3:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer and len(fields) < 3:
                raw_line, buffer = buffer.split(b"\n", 1)
                fields.append(raw_line.decode("utf-8", errors="replace").strip())
        conn.settimeout(None)
        while len(fields) < 3:
            fields.append("")
        return fields[0], fields[1], fields[2], buffer

    def _reader_loop(self, session: PlayerSession, initial_buffer: bytes):
        buffer = initial_buffer
        conn = session.conn
        try:
            while not self.stop_event.is_set() and session.connected:
                if b"\n" not in buffer:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk
                while b"\n" in buffer:
                    raw_line, buffer = buffer.split(b"\n", 1)
                    message = raw_line.decode("utf-8", errors="replace").strip()
                    if not message:
                        continue
                    try:
                        payload = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                    self._handle_client_message(session, payload)
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            self._handle_disconnect(session)

    def _handle_client_message(self, session: PlayerSession, payload: dict):
        msg_type = payload.get("type")
        if msg_type == "chat":
            text = str(payload.get("text", "")).strip()
            if not text:
                return
            if payload.get("scope") == "team":
                self.broadcast_chat(f"[队伍][{session.name}] {text}", team=session.team)
            else:
                self.broadcast_chat(f"[全部][{session.name}] {text}")
            return
        if msg_type == "view":
            self._send_private_view(session, payload.get("target_id"))
            return
        if msg_type == "submit":
            with self.game_lock:
                can_act = self.game_active.is_set() and session.connected and session.character_id == self.current_actor_id and payload.get("turn_id") == self.current_turn_id
            if not can_act:
                self.send_private_log(session, "现在不是你的正式行动回合。")
                return
            session.submit_queue.put(payload)

    def _handle_disconnect(self, session: PlayerSession):
        if not session.connected:
            return
        session.close()
        with self.sessions_lock:
            self.sessions.pop(session.addr, None)
        self.broadcast_public_log(f"队伍 {session.team} 的 {session.name} 离开了房间。")
        self.broadcast_state()
        print(f"[服务端] 玩家离开 {session.addr} -> {session.name}")
        if self.game_active.is_set():
            self.room_broken.set()

    def _safe_send_and_close(self, conn: socket.socket, payload: dict):
        try:
            conn.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        except OSError:
            pass
        try:
            conn.close()
        except OSError:
            pass

    def get_connected_count(self) -> int:
        with self.sessions_lock:
            return sum(1 for session in self.sessions.values() if session.connected)

    def get_connected_sessions(self) -> List[PlayerSession]:
        with self.sessions_lock:
            return [session for session in self.sessions.values() if session.connected]

    def send_json(self, session: PlayerSession, payload: dict):
        try:
            session.send_json(payload)
        except OSError:
            self._handle_disconnect(session)

    def broadcast_json(self, payload: dict):
        for session in self.get_connected_sessions():
            self.send_json(session, payload)

    def send_chat_log(self, session: PlayerSession, text: str):
        self.send_json(session, {"type": "chat_log", "text": text})

    def broadcast_chat(self, text: str, team: Optional[str] = None):
        payload = {"type": "chat", "text": text}
        for session in self.get_connected_sessions():
            if team is None or session.team == team:
                self.send_json(session, payload)

    def send_private_log(self, session: PlayerSession, text: str):
        self.send_json(session, {"type": "battle_log", "text": text, "private": True})

    def broadcast_public_log(self, text: str):
        self.broadcast_json({"type": "battle_log", "text": text, "private": False})

    def broadcast_state(self):
        for session in self.get_connected_sessions():
            self.send_json(session, {"type": "state", "payload": self._build_state_payload(session)})
    def run(self):
        self.start()
        try:
            while not self.stop_event.is_set():
                self._wait_for_start_command()
                if self.stop_event.is_set():
                    break
                sessions = self.get_connected_sessions()
                if len(sessions) < self.config.min_players:
                    print(f"[服务端] 玩家不足，至少需要 {self.config.min_players} 名玩家才能开始。")
                    continue
                self.match_modifiers = self._prompt_match_modifiers()
                self.active_sessions = sessions[: self.config.max_players]
                self._run_single_match()
                if self.stop_event.is_set():
                    break
                choice = input("\n是否重新开始游戏？(y/n): ").strip().lower()
                if choice != "y":
                    self.broadcast_public_log("游戏结束，再见。")
                    self.broadcast_state()
                    break
                self.broadcast_public_log("新一局即将开始，请等待房主再次开始游戏。")
                self.broadcast_state()
        finally:
            self.shutdown()

    def _wait_for_start_command(self):
        print(f"\n[服务端] 当前连接玩家 {self.get_connected_count()} 人，最少 {self.config.min_players} 人，最多 {self.config.max_players} 人。")
        input("[服务端] 按回车开始游戏…\n")

    def _prompt_match_modifiers(self) -> MatchModifiers:
        choice = input("[服务端] 是否启用特殊玩法？(y/n): ").strip()
        if choice not in ("y", "Y"):
            print("[服务端] 本局按默认规则运行。")
            return MatchModifiers()
        while True:
            raw = input("[服务端] 请输入 x倍血量, y倍步数, z倍CD（非负整数，且 x/y 非 0），例如 5,3,2: ").strip()
            normalized = raw.replace("，", ",").replace(" ", ",")
            parts = [part for part in normalized.split(",") if part != ""]
            if len(parts) != 3:
                print("[服务端] 输入格式错误，请重新输入三个整数。")
                continue
            try:
                hp_multiplier, step_multiplier, cd_multiplier = [int(part) for part in parts]
            except ValueError:
                print("[服务端] 只能输入整数，请重新输入。")
                continue
            if hp_multiplier < 0 or step_multiplier < 0 or cd_multiplier < 0:
                print("[服务端] 三个数都必须是非负整数，请重新输入。")
                continue
            if hp_multiplier == 0 or step_multiplier == 0:
                print("[服务端] x 和 y 不能为 0，请重新输入。")
                continue
            print(f"[服务端] 已启用特殊玩法：血量 x{hp_multiplier}，步数 x{step_multiplier}，CD x{cd_multiplier}")
            return MatchModifiers(
                enabled=True,
                hp_multiplier=hp_multiplier,
                step_multiplier=step_multiplier,
                cd_multiplier=cd_multiplier,
            )

    def _run_single_match(self):
        self.game_active.set()
        self.room_broken.clear()
        self.current_actor_id = None
        self.current_turn_id = 0
        self.character_sessions.clear()
        self.character_id_seq = 1
        with self.game_lock:
            characters = self._build_characters_for_sessions(self.active_sessions)
            self._apply_match_modifiers(characters)
            self.backend = GameBackend(characters)
        self.broadcast_public_log("游戏开始！")
        self._announce_match_start()
        self.broadcast_state()
        while not self.stop_event.is_set() and not self.room_broken.is_set():
            with self.game_lock:
                if self.backend is None or self.backend.is_game_over():
                    break
                round_data = self.backend.start_round()
            self._broadcast_round_start(round_data)
            actor = round_data["winner"]
            if actor is None or not actor.is_alive():
                self.current_actor_id = None
                self.current_turn_id += 1
                self.broadcast_public_log("本回合没有可行动的角色。")
                self.broadcast_state()
                with self.game_lock:
                    round_end = self.backend.finish_round(None)
                self._broadcast_round_end(round_end)
                self.broadcast_state()
                continue
            round_consumed = False
            remaining_steps = self.match_modifiers.step_multiplier
            while not self.stop_event.is_set() and not self.room_broken.is_set():
                actor_session = self.character_sessions.get(id(actor))
                if actor_session is None or not actor_session.connected:
                    self.broadcast_public_log(f"{actor.name} 的操控玩家已离线，本局终止。")
                    self.room_broken.set()
                    break
                if not actor.is_alive():
                    self.broadcast_public_log(f"{actor.name} 已无法继续行动，本回合结束。")
                    round_consumed = True
                    with self.game_lock:
                        round_end = self.backend.finish_round(None)
                    self._broadcast_round_end(round_end)
                    self.broadcast_state()
                    break
                self.current_actor_id = actor_session.character_id
                self.current_turn_id += 1
                self._drain_submit_queue(actor_session)
                if self.match_modifiers.step_multiplier > 1:
                    self.broadcast_public_log(f"现在轮到 {actor.name} 行动（本回合剩余 {remaining_steps} 步）。")
                else:
                    self.broadcast_public_log(f"现在轮到 {actor.name} 行动。")
                self.broadcast_state()
                submit_payload = self._wait_for_actor_submit(actor_session)
                if submit_payload is None:
                    self.room_broken.set()
                    break
                outcome = self._process_submit(actor_session, actor, submit_payload)
                self.broadcast_state()
                if outcome == "illegal_retry":
                    with self.game_lock:
                        reroll = self.backend.rock_paper_scissors()
                    self._broadcast_rps_retry(reroll)
                    actor = reroll["winner"]
                    remaining_steps = self.match_modifiers.step_multiplier
                    if actor is None or not actor.is_alive():
                        self.broadcast_public_log("重新判定后仍没有合法行动者，本回合结束。")
                        round_consumed = True
                        with self.game_lock:
                            round_end = self.backend.finish_round(None)
                        self._broadcast_round_end(round_end)
                        self.broadcast_state()
                        break
                    continue
                with self.game_lock:
                    game_over_after_action = self.backend is None or self.backend.is_game_over()
                if game_over_after_action:
                    round_consumed = True
                    with self.game_lock:
                        round_end = self.backend.finish_round(actor if actor.is_alive() else None)
                    self._broadcast_round_end(round_end)
                    self.broadcast_state()
                    break
                remaining_steps -= 1
                if remaining_steps > 0 and actor.is_alive():
                    self.broadcast_public_log(f"{actor.name} 还可以继续行动 {remaining_steps} 次。")
                    continue
                round_consumed = True
                with self.game_lock:
                    round_end = self.backend.finish_round(actor if actor.is_alive() else None)
                self._broadcast_round_end(round_end)
                self.broadcast_state()
                break
            if not round_consumed and self.room_broken.is_set():
                break
        if self.room_broken.is_set() and not self.stop_event.is_set():
            self.broadcast_public_log("本局因玩家断线而终止。")
        elif self.backend is not None:
            self._broadcast_game_over(self.backend.get_game_over_summary())
        self.game_active.clear()
        self.current_actor_id = None
        self.current_turn_id += 1
        self.backend = None
        self.character_sessions.clear()
        self.active_sessions = []
        self.broadcast_state()

    def _apply_match_modifiers(self, characters: List[object]):
        if not self.match_modifiers.enabled:
            return
        if self.match_modifiers.hp_multiplier != 1:
            for character in characters:
                if hasattr(character, "max_hp") and hasattr(character, "current_hp"):
                    character.max_hp *= self.match_modifiers.hp_multiplier
                    character.current_hp = character.max_hp

    def _build_characters_for_sessions(self, sessions: List[PlayerSession]) -> List[object]:
        factory = get_character_factory()
        default_cycle = self.config.default_characters or ["knight", "summoner", "swordsman"]
        characters = []
        for index, session in enumerate(sessions):
            role_id = self._resolve_role_id(session.character_request)
            if role_id is None:
                role_id = default_cycle[index % len(default_cycle)]
                self.send_private_log(session, f"未识别角色“{session.character_request or '空'}”，已回退为 {role_id}。")
            display_name = (get_character_registry().get_metadata(role_id) or {}).get("display_name", role_id)
            character = factory.create(role_id, display_name)
            if character is None:
                raise RuntimeError(f"无法创建角色: {role_id}")
            session.character = character
            session.character_id = self.character_id_seq
            self.character_id_seq += 1
            self.character_sessions[id(character)] = session
            characters.append(character)
            self.send_private_log(session, f"你是 {character.name}。")
        return characters

    def _resolve_role_id(self, text: str) -> Optional[str]:
        target = (text or "").strip()
        if not target:
            return None
        normalized = target.lower()
        registry = get_character_registry()
        for role_id, metadata in registry.get_all_metadata().items():
            if role_id.lower() == normalized:
                return role_id
            display_name = str(metadata.get("display_name", "")).strip()
            stats_name = str(metadata.get("stats", {}).get("name", "")).strip()
            if target == display_name or target == stats_name:
                return role_id
        return None

    def _announce_match_start(self):
        self.broadcast_public_log("=" * 60)
        self.broadcast_public_log("欢迎来到联网角色战斗游戏！")
        self.broadcast_public_log("=" * 60)
        self.broadcast_public_log("参战角色：")
        for session in self.active_sessions:
            if session.character is None:
                continue
            self.broadcast_public_log(f"  - {session.character.name}: {session.character.max_hp} HP / 队伍 {session.team} 的 {session.name}")
        self.broadcast_public_log("游戏规则：")
        self.broadcast_public_log("  1. 每回合通过石头剪刀布决定先手")
        self.broadcast_public_log("  2. 当前行动者可出招或行动，其他玩家可随时查看信息")
        self.broadcast_public_log("  3. 最后存活的角色获胜")
        if self.match_modifiers.enabled:
            self.broadcast_public_log("特殊玩法：")
            self.broadcast_public_log(f"  - 初始生命值与生命上限 x{self.match_modifiers.hp_multiplier}")
            self.broadcast_public_log(f"  - 每次获胜可连续行动 {self.match_modifiers.step_multiplier} 步")
            self.broadcast_public_log(f"  - 技能冷却倍率 x{self.match_modifiers.cd_multiplier}")
        self.broadcast_public_log("=" * 60)

    def _broadcast_round_start(self, round_data: dict):
        self.broadcast_public_log("")
        self.broadcast_public_log("=" * 60)
        self.broadcast_public_log(f"第 {round_data['round_count']} 回合开始")
        self.broadcast_public_log("=" * 60)
        for row in round_data["battle_status"]:
            status = "存活" if row["alive"] else "已阵亡"
            self.broadcast_public_log(f"{row['name']:10} [{status}] {row['hp_bar']} {row['current_hp']}/{row['max_hp']} HP")
            if row["status_info"]:
                self.broadcast_public_log("           " + " | ".join(row["status_info"]))
        self.broadcast_public_log("=" * 60)
        for line in round_data["rps_logs"]:
            self.broadcast_public_log(line)
        if round_data["winner_message"]:
            self.broadcast_public_log(f">>> {round_data['winner_message']}")

    def _broadcast_rps_retry(self, reroll: dict):
        self.broadcast_public_log("本次提交被判定为非法，本回合重新进行石头剪刀布。")
        for line in reroll["logs"]:
            self.broadcast_public_log(line)
        if reroll["winner"] is not None:
            self.broadcast_public_log(f">>> 本回合重新由 {reroll['winner'].name} 行动")

    def _broadcast_round_end(self, round_end: dict):
        self.broadcast_public_log("")
        self.broadcast_public_log("=" * 60)
        self.broadcast_public_log(f"第 {round_end['round_count']} 回合结束")
        self.broadcast_public_log("=" * 60)
        for char in round_end["characters"]:
            if char["alive"]:
                self.broadcast_public_log(f"{char['name']}: {char['hp_bar']} {char['current_hp']}/{char['max_hp']} HP")
            else:
                self.broadcast_public_log(f"{char['name']}: [已阵亡]")
        self.broadcast_public_log("=" * 60)

    def _broadcast_game_over(self, summary: dict):
        self.broadcast_public_log("")
        self.broadcast_public_log("=" * 60)
        self.broadcast_public_log("=== 游戏结束 ===")
        self.broadcast_public_log("=" * 60)
        if summary["max_rounds_reached"]:
            self.broadcast_public_log("达到最大回合数限制。")
        if summary["type"] == "winner":
            self.broadcast_public_log(f"获胜者：{summary['winner_name']}")
            self.broadcast_public_log(f"剩余生命值：{summary['winner_hp']}/{summary['winner_max_hp']}")
        elif summary["type"] == "all_destroyed":
            self.broadcast_public_log("所有角色同归于尽！")
        else:
            self.broadcast_public_log("游戏平局。")
            self.broadcast_public_log(f"存活角色：{summary['alive_names']}")
        self.broadcast_public_log(f"总回合数：{summary['round_count']}")
        self.broadcast_public_log("最终状态：")
        for char in summary["final_status"]:
            status = "存活" if char["alive"] else "已阵亡"
            self.broadcast_public_log(f"  {char['name']}: {char['current_hp']}/{char['max_hp']} HP [{status}]")
        self.broadcast_public_log("=" * 60)

    def _wait_for_actor_submit(self, actor_session: PlayerSession) -> Optional[dict]:
        while not self.stop_event.is_set() and not self.room_broken.is_set():
            if not actor_session.connected:
                return None
            try:
                return actor_session.submit_queue.get(timeout=0.5)
            except queue.Empty:
                continue
        return None

    @staticmethod
    def _drain_submit_queue(session: PlayerSession):
        while True:
            try:
                session.submit_queue.get_nowait()
            except queue.Empty:
                break
    def _process_submit(self, actor_session: PlayerSession, actor, payload: dict) -> str:
        intent = payload.get("intent") or {}
        category = intent.get("category")
        if category == "formal_action":
            return self._process_formal_action(actor_session, actor, intent)
        if category == "behavior":
            return self._process_behavior(actor_session, actor, intent)
        self.broadcast_public_log(f"{actor.name} 提交了未知动作，本回合重新猜拳。")
        return "illegal_retry"

    def _process_formal_action(self, actor_session: PlayerSession, actor, intent: dict) -> str:
        raw_action = str(intent.get("action", "")).strip()
        if not raw_action:
            self.broadcast_public_log(f"{actor.name} 没有提交有效招式，本回合重新猜拳。")
            return "illegal_retry"
        base_action = self._strip_action_suffix(raw_action)
        target = self._get_character_by_session_id(intent.get("target_id"))
        if self.backend is None:
            return "illegal_retry"
        ui_meta = self._build_action_ui_meta(actor, raw_action)
        if ui_meta["auto_multi"]:
            target_info = self.backend.get_action_targets(actor, base_action)
            selected_targets = target_info.get("targets", []) if not target_info.get("error") else []
            if not selected_targets:
                self.broadcast_public_log(f"{actor.name} 尝试使用 {base_action}，但判定为非法。")
                return "illegal_retry"
            success = self.backend.execute_player_action(actor, base_action, selected_targets=selected_targets)
            if success:
                self._apply_skill_cooldown_modifier(actor, base_action)
                names = "、".join(target_obj.name for target_obj in selected_targets)
                self.broadcast_public_log(f"{actor.name} 使用了 {base_action}，目标：{names}")
                return "advance"
            self.broadcast_public_log(f"{actor.name} 尝试使用 {base_action}，但判定为非法。")
            return "illegal_retry"
        if ui_meta["requires_target"]:
            if target is None or not target.is_alive():
                self.broadcast_public_log(f"{actor.name} 尝试使用 {base_action}，但目标无效。")
                return "illegal_retry"
            success = self.backend.execute_player_action(actor, base_action, target=target)
            if success:
                self._apply_skill_cooldown_modifier(actor, base_action)
                self.broadcast_public_log(f"{actor.name} 对 {target.name} 使用了 {base_action}")
                return "advance"
            self.broadcast_public_log(f"{actor.name} 对 {target.name} 尝试使用 {base_action}，但判定为非法。")
            return "illegal_retry"
        success = self.backend.execute_player_action(actor, base_action)
        if success:
            self._apply_skill_cooldown_modifier(actor, base_action)
            self.broadcast_public_log(f"{actor.name} 使用了 {base_action}")
            return "advance"
        self.broadcast_public_log(f"{actor.name} 尝试使用 {base_action}，但判定为非法。")
        return "illegal_retry"

    def _process_behavior(self, actor_session: PlayerSession, actor, intent: dict) -> str:
        behavior = intent.get("behavior")
        target = self._get_character_by_session_id(intent.get("target_id"))
        if self.backend is None:
            return "illegal_retry"
        if behavior == "taunt":
            self.broadcast_public_log(f"{actor.name} 嘲讽了一番，什么也没有发生。")
            return "advance"
        if behavior == "away":
            if self.backend.count_characters_in_block(actor.block_id) <= 1:
                self.broadcast_public_log(f"{actor.name} 试图远离所有人，但本来就独处。")
                return "advance"
            success = self.backend.execute_player_action(actor, "行为:离你远点")
            if success:
                self.broadcast_public_log(f"{actor.name} 远离了所有人。")
            else:
                self.broadcast_public_log(f"{actor.name} 试图远离所有人，但没有发生变化。")
            return "advance"
        if behavior == "approach":
            if target is None or not target.is_alive():
                self.broadcast_public_log(f"{actor.name} 试图靠近一个无效目标，什么也没有发生。")
                return "advance"
            if target is actor:
                self.broadcast_public_log(f"{actor.name} 试图靠近自己，什么也没有发生。")
                return "advance"
            success = self.backend.execute_player_action(actor, "行为:到你身边", target=target)
            if success:
                self.broadcast_public_log(f"{actor.name} 来到了 {target.name} 身边。")
            else:
                self.broadcast_public_log(f"{actor.name} 试图靠近 {target.name}，但没有发生变化。")
            return "advance"
        if behavior == "search":
            if target is None or not target.is_alive():
                self.broadcast_public_log(f"{actor.name} 试图寻找一个无效目标，什么也没有发生。")
                return "advance"
            if not isinstance(target, Ninja) or not target.in_stealth:
                self.broadcast_public_log(f"{actor.name} 试图寻找 {target.name}，但对方并不处于隐身状态。")
                return "advance"
            with redirect_stdout(io.StringIO()):
                found = target.be_searched(actor)
            if found:
                self.broadcast_public_log(f"{actor.name} 成功找出了隐身中的 {target.name}。")
            else:
                self.broadcast_public_log(f"{actor.name} 试图寻找 {target.name}，但没有成功。")
            return "advance"
        self.broadcast_public_log(f"{actor.name} 提交了未知行动，什么也没有发生。")
        return "advance"

    def _build_state_payload(self, session: PlayerSession) -> dict:
        with self.game_lock:
            players = []
            for active in self.active_sessions:
                if active.character is None or active.character_id is None:
                    continue
                char = active.character
                players.append({
                    "id": active.character_id,
                    "role_name": char.name,
                    "owner_name": active.name,
                    "team": active.team,
                    "current_hp": char.current_hp,
                    "max_hp": char.max_hp,
                    "alive": char.is_alive(),
                    "is_current_actor": active.character_id == self.current_actor_id,
                })
            can_act = self.game_active.is_set() and session.connected and session.character_id == self.current_actor_id and session.character is not None and session.character.is_alive()
            formal_actions: List[dict] = []
            if can_act and self.backend is not None and session.character is not None:
                action_context = self.backend.get_action_context(session.character)
                for entry in action_context["actions"]:
                    action = entry["action"]
                    base_action = self._strip_action_suffix(action)
                    if base_action in ("行为:到你身边", "行为:离你远点"):
                        continue
                    meta = self._build_action_ui_meta(session.character, action)
                    formal_actions.append({
                        "action": action,
                        "label": action.replace("技能:", "", 1).replace("行为:", "", 1),
                        "requires_target": meta["requires_target"],
                        "auto_multi": meta["auto_multi"],
                    })
            return {
                "game_active": self.game_active.is_set(),
                "round": self.backend.round_count if self.backend is not None else 0,
                "turn_id": self.current_turn_id,
                "current_actor_id": self.current_actor_id,
                "self_player_id": session.character_id,
                "can_view": self.game_active.is_set(),
                "can_act": can_act,
                "players": players,
                "formal_actions": formal_actions,
            }

    def _send_private_view(self, session: PlayerSession, target_id):
        with self.game_lock:
            if self.backend is None:
                self.send_private_log(session, "当前还没有进行中的对局。")
                return
            target_session = self._get_session_by_character_id(target_id)
            if target_session is None or target_session.character is None:
                self.send_private_log(session, "查看目标不存在。")
                return
            target = target_session.character
            self.send_private_log(session, f"[查看] {target.name}")
            self.send_private_log(session, f"操控玩家：{target_session.name} / 队伍：{target_session.team}")
            self.send_private_log(session, f"生命值：{target.current_hp}/{target.max_hp} ({'存活' if target.is_alive() else '阵亡'})")
            if target.skills:
                self.send_private_log(session, "技能冷却：")
                for skill_name, skill in target.skills.items():
                    self.send_private_log(session, f"  - {skill_name}: CD {skill.get_cooldown()} / 基础 {skill.get_base_cooldown()}")
            self.send_private_log(session, f"控制效果：{dict(target.control) if target.control else '无'}")
            self.send_private_log(session, f"印记：{dict(target.imprints) if target.imprints else '无'}")
            self.send_private_log(session, f"积累：{dict(target.accumulations) if target.accumulations else '无'}")
            self.send_private_log(session, f"所在位置块：{target.block_id}")

    def _apply_skill_cooldown_modifier(self, actor, action: str):
        if not action.startswith("技能:"):
            return
        skill_name = action.replace("技能:", "", 1)
        skill = actor.get_skill(skill_name) if hasattr(actor, "get_skill") else None
        if skill is None:
            return
        current_cd = skill.get_cooldown()
        if self.match_modifiers.cd_multiplier == 0:
            skill.set_cooldown(0)
            return
        if current_cd > 0 and self.match_modifiers.cd_multiplier != 1:
            skill.set_cooldown(current_cd * self.match_modifiers.cd_multiplier)

    @staticmethod
    def _strip_action_suffix(action: str) -> str:
        prefix = "技能:" if action.startswith("技能:") else "行为:" if action.startswith("行为:") else None
        if prefix is None:
            return action
        content = action[len(prefix):]
        return prefix + content.split("(", 1)[0].strip()

    def _build_action_ui_meta(self, character, action: str) -> dict:
        base_action = self._strip_action_suffix(action)
        if base_action.startswith("行为:"):
            return {"requires_target": False, "auto_multi": False}
        if base_action in NO_TARGET_SKILLS:
            return {"requires_target": False, "auto_multi": False}
        if self.backend is None:
            return {"requires_target": True, "auto_multi": False}
        target_info = self.backend.get_action_targets(character, base_action)
        if target_info.get("multi_select"):
            return {"requires_target": False, "auto_multi": True}
        if not target_info.get("requires_target", False):
            return {"requires_target": False, "auto_multi": False}
        return {"requires_target": True, "auto_multi": False}

    def _get_session_by_character_id(self, character_id) -> Optional[PlayerSession]:
        if character_id is None:
            return None
        for session in self.active_sessions:
            if session.character_id == character_id:
                return session
        return None

    def _get_character_by_session_id(self, character_id):
        session = self._get_session_by_character_id(character_id)
        return None if session is None else session.character

def main():
    parser = argparse.ArgumentParser(description="Quanzhi 联网服务端")
    parser.add_argument("--host", default=DEFAULT_HOST, help="监听地址，默认 0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口")
    args = parser.parse_args()
    server = NetworkGameServer(host=args.host, port=args.port)
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n[服务端] 收到中断信号，准备退出。")
    finally:
        server.shutdown()

if __name__ == "__main__":
    main()
