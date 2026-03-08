# -*- coding: utf-8 -*-
# game_cli.py
import time

from backend.game_backend import GameBackend
from characters.scientist import Scientist


class GameCLI:
    def __init__(self, backend: GameBackend):
        self.backend = backend

    def display_battle_status(self, status_data):
        print(f"\n{'=' * 60}")  # Target: All Players
        print(
            f"第 {self.backend.round_count} 回合开始".center(60)
        )  # Target: All Players
        print("=" * 60)  # Target: All Players
        for row in status_data:
            status = "存活" if row["alive"] else "已摧毁"
            print(
                f"{row['name']:10} [{status:4}] {row['hp_bar']} {row['current_hp']:2}/{row['max_hp']:2} HP"
            )  # Target: All Players
            if row["status_info"]:
                print(
                    f"           {' | '.join(row['status_info'])}"
                )  # Target: All Players
        print("=" * 60)  # Target: All Players

    def choose_action(self, action_context):
        print(f"\n{'=' * 60}")  # Target: Current Player
        print(f"{action_context['name']} 的回合".center(60))  # Target: Current Player
        print("=" * 60)  # Target: Current Player
        print(
            f"当前状态: HP {action_context['current_hp']}/{action_context['max_hp']}"
        )  # Target: Current Player

        if action_context["controls"]:
            print(f"控制效果: {action_context['controls']}")  # Target: Current Player
        if action_context["imprints"]:
            print(f"印记: {action_context['imprints']}")  # Target: Current Player
        if action_context["accumulations"]:
            print(f"积累: {action_context['accumulations']}")  # Target: Current Player
        if action_context["shield_charges"] is not None:
            print(
                f"盾次数: {action_context['shield_charges']}"
            )  # Target: Current Player

        print("\n可用动作：")  # Target: Current Player
        for entry in action_context["actions"]:
            if entry["is_unavailable"]:
                print(
                    f"{entry['index']}. {entry['action']} [不可用]"
                )  # Target: Current Player
            else:
                print(f"{entry['index']}. {entry['action']}")  # Target: Current Player

        while True:
            try:
                choice = input("\n请输入动作编号: ").strip()
                if choice.isdigit():
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(action_context["actions"]):
                        selected = action_context["actions"][choice_num - 1]
                        if selected["is_unavailable"]:
                            print("该动作当前无法使用！")  # Target: Current Player
                            continue
                        return selected["action"]
                    print(
                        f"请输入1-{len(action_context['actions'])}之间的数字！"
                    )  # Target: Current Player
                    continue
                print("无效的输入，请重新选择！")  # Target: Current Player
            except Exception as e:
                print(f"输入错误：{e}，请重新输入！")  # Target: Current Player

    def choose_target(self, actor, targets):
        print("\n可用目标：")  # Target: Current Player
        for i, target in enumerate(targets, 1):
            info = f"{target.name} (HP: {target.current_hp}/{target.max_hp})"
            if target.imprints:
                info += f" 印记:{target.imprints}"
            if target.control:
                info += f" 控制:{list(target.control.keys())}"
            nearby = "[近]" if actor.is_nearby(target) else "[远]"
            print(f"{i}. {nearby} {info}")  # Target: Current Player

        while True:
            try:
                target_choice = input("请选择目标编号: ").strip()
                if target_choice.isdigit():
                    target_num = int(target_choice)
                    if 1 <= target_num <= len(targets):
                        return targets[target_num - 1]
                print(f"请输入1-{len(targets)}之间的数字！")  # Target: Current Player
            except Exception as e:
                print(f"输入错误：{e}，请重新输入！")  # Target: Current Player

    def choose_multiple_targets(self, actor, targets):
        """多目标选择：玩家用空格分隔编号，至少选1个。"""
        print("\n可用目标（输入编号，多个目标用空格分隔）：")  # Target: Current Player
        for i, target in enumerate(targets, 1):
            info = f"{target.name} (HP: {target.current_hp}/{target.max_hp})"
            if target.imprints:
                info += f" 印记:{target.imprints}"
            if target.control:
                info += f" 控制:{list(target.control.keys())}"
            nearby = "[近]" if actor.is_nearby(target) else "[远]"
            print(f"{i}. {nearby} {info}")  # Target: Current Player

        while True:
            try:
                choice_str = input("请选择目标编号（空格分隔，至少1个）: ").strip()
                if not choice_str:
                    print("请至少选择1个目标！")  # Target: Current Player
                    continue
                parts = choice_str.split()
                chosen = []
                valid = True
                seen_ids = set()
                for part in parts:
                    if not part.isdigit():
                        print(
                            f"无效输入：{part}，请输入数字编号！"
                        )  # Target: Current Player
                        valid = False
                        break
                    n = int(part)
                    if not (1 <= n <= len(targets)):
                        print(
                            f"编号 {n} 超出范围，请输入 1-{len(targets)} 之间的数字！"
                        )  # Target: Current Player
                        valid = False
                        break
                    t = targets[n - 1]
                    if id(t) not in seen_ids:
                        seen_ids.add(id(t))
                        chosen.append(t)
                if not valid:
                    continue
                if not chosen:
                    print("请至少选择1个目标！")  # Target: Current Player
                    continue
                return chosen
            except Exception as e:
                print(f"输入错误：{e}，请重新输入！")  # Target: Current Player

    def display_round_end(self, round_end):
        print(f"\n{'=' * 60}")  # Target: All Players
        print(
            f"第 {round_end['round_count']} 回合结束".center(60)
        )  # Target: All Players
        print("=" * 60)  # Target: All Players
        for char in round_end["characters"]:
            if char["alive"]:
                print(
                    f"{char['name']}: {char['hp_bar']} {char['current_hp']}/{char['max_hp']} HP"
                )  # Target: All Players
            else:
                print(f"{char['name']}: [已摧毁]")  # Target: All Players
        print("=" * 60)  # Target: All Players

    def display_game_over(self, summary):
        print("\n" + "=" * 60)  # Target: All Players
        print("=== 游戏结束 ===")  # Target: All Players
        print("=" * 60)  # Target: All Players

        if summary["max_rounds_reached"]:
            print("\n达到最大回合数限制！")  # Target: All Players

        if summary["type"] == "winner":
            print(f"\n>>> 获胜者: {summary['winner_name']}")  # Target: All Players
            print(
                f"    剩余生命值: {summary['winner_hp']}/{summary['winner_max_hp']}"
            )  # Target: All Players
        elif summary["type"] == "all_destroyed":
            print("\n所有角色同归于尽！")  # Target: All Players
        else:
            print("\n游戏平局！")  # Target: All Players
            print(f"存活角色: {summary['alive_names']}")  # Target: All Players

        print(f"\n总回合数: {summary['round_count']}")  # Target: All Players
        print("\n最终状态:")  # Target: All Players
        for char in summary["final_status"]:
            status = "存活" if char["alive"] else "已摧毁"
            print(
                f"  {char['name']}: {char['current_hp']}/{char['max_hp']} HP [{status}]"
            )  # Target: All Players

        print("=" * 60)  # Target: All Players

    def run(self):
        print("=" * 60)  # Target: All Players
        print("欢迎来到角色战斗游戏！".center(60))  # Target: All Players
        print("=" * 60)  # Target: All Players
        print("\n参战角色:")  # Target: All Players
        for char in self.backend.all_characters:
            print(f"  - {char.name}: {char.max_hp} HP")  # Target: All Players
        print("\n游戏规则:")  # Target: All Players
        print("  1. 每回合通过石头剪刀布决定先手")  # Target: All Players
        print("  2. 使用技能攻击对手或执行战术动作")  # Target: All Players
        print("  3. 最后存活的角色获胜")  # Target: All Players
        print("=" * 60)  # Target: All Players

        while not self.backend.is_game_over():
            try:
                round_data = self.backend.start_round()
                self.display_battle_status(round_data["battle_status"])
                for line in round_data["rps_logs"]:
                    print(line)  # Target: All Players

                winner = round_data["winner"]
                if winner is None:
                    print("没有角色可以行动！")  # Target: All Players
                    self.display_round_end(self.backend.finish_round(None))
                    time.sleep(self.backend.config.round_delay)
                    continue

                print(f"\n>>> {round_data['winner_message']}")  # Target: All Players
                action_context = self.backend.get_action_context(winner)
                action = self.choose_action(action_context)

                target_info = self.backend.get_action_targets(winner, action)
                if target_info.get("error"):
                    print(
                        f"\n[警告] {winner.name} 的动作未能成功执行（{target_info['error']}）"
                    )  # Target: All Players
                    success = False
                else:
                    target = None
                    selected_targets = None
                    # 科学家制造机器人：先为机器人命名
                    if action == "技能:制造机器人" and isinstance(winner, Scientist):
                        robot_name = input(
                            "请为你的小机器人起名: "
                        ).strip()  # Target: Current Player
                        if not robot_name:
                            robot_name = f"机器人{winner.robot_count + 1}"
                        winner.set_pending_robot_name(robot_name)
                    if target_info.get("requires_target"):
                        if target_info.get("multi_select"):
                            selected_targets = self.choose_multiple_targets(
                                winner, target_info.get("targets", [])
                            )
                        else:
                            target = self.choose_target(
                                winner, target_info.get("targets", [])
                            )
                    success = self.backend.execute_player_action(
                        winner, action, target, selected_targets
                    )

                if not success:
                    print(
                        f"\n[警告] {winner.name} 的动作未能成功执行（废步）"
                    )  # Target: All Players

                self.display_round_end(self.backend.finish_round(winner))
                time.sleep(self.backend.config.round_delay)
            except KeyboardInterrupt:
                print("\n\n游戏被中断！")  # Target: Current Player
                choice = input("是否退出游戏？(y/n): ").strip().lower()
                if choice == "y":
                    print("游戏已退出。")  # Target: Current Player
                    return
            except Exception as e:
                print(f"\n发生错误: {e}")  # Target: Current Player
                import traceback

                traceback.print_exc()
                choice = input("是否继续游戏？(y/n): ").strip().lower()
                if choice != "y":
                    return

        self.display_game_over(self.backend.get_game_over_summary())
        choice = input("\n是否重新开始游戏？(y/n): ").strip().lower()
        if choice == "y":
            self.backend.reset_game()
            self.run()
