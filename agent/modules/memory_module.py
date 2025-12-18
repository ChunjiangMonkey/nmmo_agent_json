# agent/modules/memory.py
from collections import deque
from copy import deepcopy
from typing import Deque, Dict, List, Optional, Tuple

MemoryEntry = Dict[str, object]


class MemoryModule:
    def __init__(
        self,
        max_history=20,
    ):
        if max_history <= 0:
            raise ValueError("max_history must be positive")

        self.max_history = max_history
        self._history = []

    def summarize(self):
        pass

    def update(self, tick, event_record, executing_action):
        # 目前该方法只记录交互事件
        interaction_event_description = self.generate_interaction_event_description(event_record)
        if interaction_event_description == "":
            return
        entry = {
            "tick": tick,
            "executing_action": executing_action,
            "record": event_record,
            "description": interaction_event_description,
        }
        self._history.append(entry)

    # def update(self, tick, event_record, state_info, executing_action):
    #     # event_record其实记录了两个tick的事件
    #     # 需要拆分harvest和其他事件
    #     pre_action_event_description = self.generate_pre_action_event_description(event_record)
    #     if pre_action_event_description:
    #         if self._history:
    #             if self._history[-1]["tick"] == tick - 1:
    #                 self._history[-1]["description"] += pre_action_event_description
    #             else:
    #                 entry = {
    #                     "tick": tick - 1,
    #                     "food": state_info["agent"]["food"],
    #                     "water": state_info["agent"]["water"],
    #                     "health": state_info["agent"]["health"],
    #                     "executing_action": executing_action,
    #                     "record": event_record,
    #                     "description": pre_action_event_description,
    #                 }
    #                 self._history.append(entry)
    #         else:
    #             entry = {
    #                 "tick": tick - 1,
    #                 "food": state_info["agent"]["food"],
    #                 "water": state_info["agent"]["water"],
    #                 "health": state_info["agent"]["health"],
    #                 "executing_action": executing_action,
    #                 "record": event_record,
    #                 "description": pre_action_event_description,
    #             }
    #             self._history.append(entry)

    #     post_action_event_description = self.generate_interaction_event_description(event_record)
    #     if post_action_event_description == "":
    #         return
    #     entry = {
    #         "tick": tick,
    #         "food": state_info["agent"]["food"],
    #         "water": state_info["agent"]["water"],
    #         "health": state_info["agent"]["health"],
    #         "executing_action": executing_action,
    #         "record": event_record,
    #         "description": post_action_event_description,
    #     }
    #     self._history.append(entry)

    def get_last_tick_record(self, tick):
        assert tick > 1
        for entry in self._history:
            if entry["tick"] == tick - 1:
                return entry["record"]
        return None

    def get_recent_description(self, limit=10):
        if not self._history:
            return None
        if limit is None or limit >= len(self._history):
            entries = list(self._history)
        else:
            entries = self._history[-limit:]
        recent_memory = ""
        for entry in entries:
            recent_memory += f"Interaction event at tick {entry['tick']}: \n"
            # recent_memory += f"My food: {entry['food']}, water: {entry['water']}, health: {entry['health']}\n"
            # recent_memory += f"My action at that time: {entry['executing_action']}\n"
            recent_memory += f"{entry['description']}"
        recent_memory += "\n"
        return recent_memory

    def generate_individual_event_description(self, record):
        description = ""
        if record["harvest"]:
            for harvest_item in record["harvest"]:
                item_name = harvest_item["item"]
                item_level = harvest_item["level"]
                item_number = harvest_item["number"]
                item_res = harvest_item["item_res"]
                description += f"I harvest {item_number} level {item_level} {item_name} from {item_res} tile. \n"

        # 升级事件
        if record["skill_level_up"]:
            for skill_level_up_record in record["skill_level_up"]:
                skill_name = skill_level_up_record["skill"]
                level = skill_level_up_record["level"]
                description += f"Your {skill_name} level has increased to level {level}. \n"

            # 消耗物品事件
        if record["consume"]:
            item_name = record["consume"]["item"]
            item_level = record["consume"]["level"]
            item_number = record["consume"]["number"]
            restore_value = record["consume"]["restore_value"]
            if item_name == "Ration":
                description += (
                    f"I consume {item_number} level {item_level} {item_name}, restoring {restore_value} Food and Water. \n"
                )
            elif item_name == "Potion":
                description += f"I consume {item_number} level {item_level} {item_name}, restoring {restore_value} Health. \n"
        return description

    def generate_interaction_event_description(self, record):
        # 战斗事件, 获取物品事件, 给予事件, 死亡事件, 技能升级事件
        description = ""

        # 战斗事件
        if record["attack"]:
            target_name = record["attack"]["target"]
            attack_style = record["attack"]["style"]
            damage = record["attack"]["damage"]
            description += f"I attacked {target_name} with {attack_style} style, dealing {damage} damage. \n"

        if record["being_attacked"]:
            for being_attacked_record in record["being_attacked"]:
                attacker_name = being_attacked_record["attacker"]
                attack_style = being_attacked_record["style"]
                damage = being_attacked_record["damage"]
                description += f"I was attacked by {attacker_name} with {attack_style} style, dealing {damage} damage. \n"

        # 击杀事件
        if record["kill"]:
            # print("record:", record)
            target_name = record["kill"]["target"]
            # if "NPC" in target_name:
            #     assert record["loot"]
            level = record["kill"]["level"]

            description += f"I killed {target_name} with level {level}. "
            if record["loot"]:
                description += "Therefore, I looted the following items: "
                for i, loot_item in enumerate(record["loot"]):
                    item_name = loot_item["item"]
                    item_level = loot_item["level"]
                    item_number = loot_item["number"]
                    if i == len(record["loot"]) - 1:
                        description += f"and {item_number} level {item_level} {item_name}. \n"
                    else:
                        description += f"{item_number} level {item_level} {item_name},"
            else:
                description += "But I didn't loot any items because your inventory is full. \n"

        # 被击杀事件
        if record["being_killed"]:
            assert record["dead"] == True
            killer_name = record["being_killed"]["killer"]
            description += f"I was killed by {killer_name}, who is level {record['being_killed']['level']}. \n"

        # 给予物品事件
        if record["give"]:
            item_name = record["give"]["item"]
            item_level = record["give"]["level"]
            item_number = record["give"]["number"]
            target_name = record["give"]["target"]
            description += f"I gave {item_number} level {item_level} {item_name} to {target_name}. \n"

        # 被给予物品事件
        if record["being_given"]:
            for being_given_record in record["being_given"]:
                item_name = being_given_record["item"]
                item_level = being_given_record["level"]
                item_number = being_given_record["number"]
                giver_name = being_given_record["giver"]
                description += f"I was given {item_number} level {item_level} {item_name} by {giver_name}. \n"

        # print(description)
        return description

    def clear(self):
        """Remove all stored entries."""
        self._history = []
