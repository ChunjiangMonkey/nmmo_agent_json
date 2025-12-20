import sys, os

current_dir = os.path.abspath(__file__)
sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

import re
import string
import random
import json
import copy

from agent.prompt_template import (
    generate_action_system_prompt,
    generate_action_user_prompt,
)

from nmmo.lib import utils
from utils.io_utils import write_to_file
from constant import AREA_SPACE, DEFAULT_ACTION


action_response_format = {
    "reason": "reason for selecting Give action. ",
    "choice": "*Only* return the action you select. Do not add extra text",
}


class ActionModule:
    def __init__(self, config, llm_client, save_path, debug=False):
        self.config = config
        self.llm_client = llm_client
        self.save_path = save_path
        self.debug = debug

        self.areas = AREA_SPACE
        self.attack_range = {
            "melee": self.config.COMBAT_MELEE_REACH,
            "range": self.config.COMBAT_RANGE_REACH,
            "mage": self.config.COMBAT_MAGE_REACH,
        }
        self.default_action = DEFAULT_ACTION
        self.pos_last_step = None

    def act(
        self,
        action_type,  # move, attack, use, destroy, give
        player_role,
        tick,
        game_mechanics,
        state_description,
        action_space,
        goal=None,
        plan=None,
        action_history=None,
        candidate_action=None,
        feedback=None,
    ):
        assert action_type in ["ml_action", "use", "destroy", "give"], f"Invalid action type: {action_type}"

        input_message = self.generate_input_message(
            action_type,  # ml_action, use, destroy, give
            player_role,
            game_mechanics,
            state_description,
            action_space,
            goal=goal,
            plan=plan,
            action_history=action_history,
            candidate_action=candidate_action,
            feedback=feedback,
        )

        write_to_file(
            self.save_path,
            [
                f"=== tick: {tick} {action_type} action input ===",
                f"=== system message ===\n{input_message[0]['content']}",
                f"=== user message ===\n{input_message[1]['content']}",
            ],
        )

        if self.debug:
            random_choice = random.choice(action_space)
            response = {
                "choice": random_choice,
                "reason": f"Fake reason for choosing {random_choice}.",
            }
        else:
            response = self.llm_client.generate(input_message, action_response_format, action_space)
        # print("response in act:", response)
        if response:
            # print("Action Response:", response)
            action = response["choice"]

            write_to_file(
                self.save_path,
                [
                    f"=== tick: {tick} {action_type} action output ===",
                    json.dumps(response, indent=4),
                ],
            )
        else:
            action = self.act_randomly(action_space)
            write_to_file(
                self.save_path,
                [
                    f"=== tick: {tick} {action_type} action output ===",
                    "Fail to get action response. So act randomly. ",
                ],
            )

        return action

    # def _check_action_response(self, response, action_space):
    #     if set(response.keys()) != action_response_format.keys():
    #         raise ValueError("Invalid action response")
    #     for action_type in response.keys():
    #         if set(response[action_type].keys()) != action_response_format[action_type].keys():
    #             raise ValueError(f"Invalid action response!")
    #         if response[action_type]["choice"].rstrip(string.punctuation).lower() not in [
    #             action.rstrip(string.punctuation).lower() for action in action_space[action_type]
    #         ]:
    #             raise ValueError(f"Invalid action response!")

    def generate_input_message(
        self,
        action_type,
        player_role,
        game_mechanics,
        state_description,
        action_space,
        goal=None,
        plan=None,
        action_history=None,
        candidate_action=None,
        feedback=None,
    ):
        # ========= System Message =========
        system_prompt = generate_action_system_prompt(
            action_response_format,
            action_type,
            player_role,
            use_fog=self.config.DEATH_FOG_ONSET,
            goal=goal,
            plan=plan,
            feedback=feedback,
        )

        system_message = {
            "role": "system",
            "content": system_prompt,
        }

        # ========= User Message =========
        user_prompt = generate_action_user_prompt(
            game_mechanics,
            state_description,
            action_space,
            goal=goal,
            plan=plan,
            action_history=action_history,
            candidate_action=candidate_action,
            feedback=feedback,
        )
        user_message = {
            "role": "user",
            "content": user_prompt,
        }

        return [system_message, user_message]

    def act_randomly(self, action_space):
        return random.choice(action_space)

    def should_get_ml_action(self, tick, state_info, old_state_info, ml_action, last_record=None):
        # print("last record:", last_record)
        # 与危险entity战斗
        # pos = (state_info["agent"]["row"], state_info["agent"]["col"])

        # if tick > 1 and pos == self.pos_last_step:
        #     self.pos_last_step = pos
        #     return True

        # self.pos_last_step = pos
        if state_info["agent"]["agent_in_combat"]:
            for entity in state_info["entity"]["center"]:
                if entity["in_combat"] and entity["type"] != "passive":
                    if state_info["agent"]["name"] == entity["attacker"]:
                        return True
                    if state_info["agent"]["name"] == entity["target_of_attack"]:
                        return True

        # 开始出现死亡迷雾
        if tick == self.config.DEATH_FOG_ONSET:
            return True

        # 智能体生命垂危
        if state_info["agent"]["food"] < 30:
            return True
        if state_info["agent"]["water"] < 30:
            return True
        if state_info["agent"]["health"] < 30:
            return True

        # 出现了新的NPC
        old_state_entity_id = [entity["id"] for entity in old_state_info["entity"]["center"]]
        new_state_entity_id = [entity["id"] for entity in state_info["entity"]["center"]]
        if set(new_state_entity_id) != set(old_state_entity_id):
            return True

        # 过去的动作已经完成
        # if not last_record:
        #     return False
        if ml_action["Move"] == "Stay":
            return True
        tile_resource = state_info["agent"]["title_type"]

        move_action = ml_action["Move"]
        if move_action == "Move to the nearest Foliage tile":
            if tile_resource == "Foliage":
                return True
        if move_action == "Move to the nearest Water tile":
            if state_info["agent"]["water_around"]:
                return True

        # if not last_record["harvest"]:
        #     return False
        if "Move to the nearest" in move_action:
            res_name = move_action.split("Move to the nearest ")[1].split(" tile")[0]
            if res_name != "Foliage" and res_name != "Water" and res_name != "Fish":
                if tile_resource == res_name:
                    return True
            elif res_name == "Fish":
                if state_info["agent"]["fish_around"]:
                    return True
                # for harvest_item in last_record["harvest"]:
                #     if harvest_item["item_res"] == res_name:
                #         print(f"上一次动作完成，采集了{res_name}")
                #         return True

        if ml_action["Attack"] != "Attack nothing":
            if last_record:
                if last_record["kill"]:
                    kill_target = last_record["kill"]["target"]
                    attack_target = ml_action["Attack"].split(" with ")[0].split("Attack ")[1]
                    print(f"动作是攻击{attack_target}")
                    if kill_target == attack_target:
                        print(f"上一次动作完成，击杀了{attack_target}")
                        return True

        #  到达了新area
        new_pos = (state_info["agent"]["row"], state_info["agent"]["col"])
        old_pos = (old_state_info["agent"]["row"], old_state_info["agent"]["col"])

        if utils.linf_single(new_pos, old_pos) >= 5:
            return True
        return False

    def check_level(self, agent_info, item):
        melee_level = agent_info["melee_level"]
        range_level = agent_info["range_level"]
        mage_level = agent_info["mage_level"]
        fishing_level = agent_info["fishing_level"]
        herbalism_level = agent_info["herbalism_level"]
        prospecting_level = agent_info["prospecting_level"]
        carving_level = agent_info["carving_level"]
        alchemy_level = agent_info["alchemy_level"]
        agent_highest_level = max(
            melee_level,
            range_level,
            mage_level,
            fishing_level,
            herbalism_level,
            prospecting_level,
            carving_level,
            alchemy_level,
        )

        # 检查防具等级
        if item["type"] == "Armor":
            return agent_highest_level >= item["level"]
        # 检查武器和弹药等级
        elif item["type"] == "Weapon" or item["type"] == "Ammunition":
            if item["name"] == "Spear" or item["name"] == "Whetstone":
                return melee_level >= item["level"]
            elif item["name"] == "Bow" or item["name"] == "Arrow":
                return range_level >= item["level"]
            elif item["name"] == "Wand" or item["name"] == "Runes":
                return mage_level >= item["level"]
            else:
                raise ValueError(f"Unknown Weapon or Ammunition: {item['name']}")
        # 检查工具等级
        elif item["type"] == "Tool":
            if item["name"] == "Rod":
                return fishing_level >= item["level"]
            elif item["name"] == "Gloves":
                return herbalism_level >= item["level"]
            elif item["name"] == "Axe":
                return carving_level >= item["level"]
            elif item["name"] == "Chisel":
                return alchemy_level >= item["level"]
            elif item["name"] == "Pickaxe":
                return prospecting_level >= item["level"]
            else:
                raise ValueError(f"Unknown tool: {item['name']}")
        # 检查消耗品等级
        elif item["type"] == "Consumable":
            return agent_highest_level >= item["level"]
        else:
            return False

    def should_get_use_action(self, state_info):
        if not self.config.ITEM_SYSTEM_ENABLED:
            return False
        if state_info["agent"]["agent_in_combat"]:
            return False
        # 背包有消耗品（若生命值不满）、未穿戴的武器、工具、防具、弹药
        if state_info["agent"]["health"] != 100 or state_info["agent"]["food"] != 100 or state_info["agent"]["water"] != 100:
            consumable_item_name = [
                consumable["name"]
                for consumable in state_info["consumable"]
                if self.check_level(state_info["agent"], consumable)
            ]
            if state_info["agent"]["food"] != 100 or state_info["agent"]["water"] != 100:
                if "Ration" in consumable_item_name:
                    return True
            if state_info["agent"]["health"] != 100:
                if "Potion" in consumable_item_name:
                    return True
        unequipped_weapon = [
            weapon
            for weapon in state_info["weapon"]
            if (not weapon["is_equipped"] and self.check_level(state_info["agent"], weapon))
        ]
        if len(unequipped_weapon) > 0:
            return True
        unequipped_tool = [
            tool for tool in state_info["tool"] if (not tool["is_equipped"] and self.check_level(state_info["agent"], tool))
        ]
        if len(unequipped_tool) > 0:
            return True
        unequipped_armor = [
            armor
            for armor in state_info["armor"]
            if (not armor["is_equipped"] and self.check_level(state_info["agent"], armor))
        ]
        if len(unequipped_armor) > 0:
            return True
        unequipped_ammunition = [
            ammunition
            for ammunition in state_info["ammunition"]
            if (not ammunition["is_equipped"] and self.check_level(state_info["agent"], ammunition))
        ]
        if len(unequipped_ammunition) > 0:
            return True
        return False

    def should_get_destroy_action(self, state_info):
        if not self.config.ITEM_SYSTEM_ENABLED:
            return False
        if state_info["agent"]["agent_in_combat"]:
            return False
        if not self.generate_available_destroy(state_info):
            return False
        # 背包已满
        if state_info["capacity"] == self.config.ITEM_INVENTORY_CAPACITY:
            return True
        else:
            return False

    def should_get_give_action(self, state_info):
        if not self.config.ITEM_SYSTEM_ENABLED:
            return False

        entity_info = state_info["entity"]
        ego_id = state_info["agent"]["id"]

        has_other_player = False
        for area_entities in entity_info.values():
            for entity in area_entities:
                if entity["id"] > 0 and entity["id"] != ego_id:
                    has_other_player = True
                    break
            if has_other_player:
                break

        if not has_other_player:
            return False

        unequipped_weapon = [
            weapon
            for weapon in state_info["weapon"]
            if (not weapon["is_equipped"] and self.check_level(state_info["agent"], weapon))
        ]
        if len(unequipped_weapon) > 0:
            return True
        unequipped_tool = [
            tool for tool in state_info["tool"] if (not tool["is_equipped"] and self.check_level(state_info["agent"], tool))
        ]
        if len(unequipped_tool) > 0:
            return True
        unequipped_armor = [
            armor
            for armor in state_info["armor"]
            if (not armor["is_equipped"] and self.check_level(state_info["agent"], armor))
        ]
        if len(unequipped_armor) > 0:
            return True
        unequipped_ammunition = [
            ammunition
            for ammunition in state_info["ammunition"]
            if (not ammunition["is_equipped"] and self.check_level(state_info["agent"], ammunition))
        ]
        if len(unequipped_ammunition) > 0:
            return True
        return False

    def generate_available_ml_action(self, state_info):
        resource_info = state_info["resource"]
        entity_info = state_info["entity"]
        available_move = self.generate_available_move()
        available_harvest = self.generate_available_harvest(resource_info)
        available_safe_attack = self.generate_available_passive_NPC_attack(entity_info)
        available_dangerous_attack = self.generate_available_dangerous_entity_attack(entity_info)

        self.available_ml_action_dict = {
            **available_move,
            **available_harvest,
            **available_safe_attack,
            **available_dangerous_attack,
        }
        return list(self.available_ml_action_dict.keys())

    def generate_available_move(self):
        available_move = {}
        for area in self.areas:
            if area != "center":
                action_dict = {}
                action_dict["Move"] = f"Move to the {area} area"
                action_dict["Attack"] = self.default_action["Attack"]
                available_move[f"Move to the {area} area"] = action_dict
        action_dict = {}
        action_dict["Move"] = "Stay"
        action_dict["Attack"] = self.default_action["Attack"]
        available_move["Stay"] = action_dict
        return available_move

    def generate_available_harvest(self, resource_info):
        # print("resource_info in generate_available_harvest:", resource_info)
        available_harvest = {}
        for resource_name, resource_info in resource_info["center"].items():
            if not resource_info["is_resource"]:
                continue
            action_dict = {}
            action_dict["Move"] = f"Move to the nearest {resource_name} tile"
            action_dict["Attack"] = self.default_action["Attack"]
            available_harvest[f"Harvest {resource_name} in the center area"] = action_dict
        return available_harvest

    def generate_available_passive_NPC_attack(self, entity_info):
        available_attack = {}
        for entity in entity_info["center"]:
            if entity["type"] == "passive" and entity["entity_attackable"]:
                for attack_style in self.attack_range.keys():
                    action_dict = {}
                    action_dict["Move"] = f"Chase {entity['name']}"
                    action_dict["Attack"] = f"Attack {entity['name']} with {attack_style}"
                    available_attack[f"Attack {entity['name']} with {attack_style}"] = action_dict
        return available_attack

    def generate_available_dangerous_entity_attack(self, entity_info):
        available_attack = {}
        for entity in entity_info["center"]:
            if entity["type"] != "passive" and entity["entity_attackable"]:
                for attack_style in self.attack_range.keys():
                    action_dict = {}
                    action_dict["Move"] = f"Chase {entity['name']}"
                    action_dict["Attack"] = f"Attack {entity['name']} with {attack_style}"
                    available_attack[f"Attack {entity['name']} with {attack_style}"] = action_dict
        return available_attack

    def generate_available_item_use(self, state_info):
        ego_agent_info = state_info["agent"]
        item_info = (
            state_info["armor"]
            + state_info["weapon"]
            + state_info["tool"]
            + state_info["ammunition"]
            + state_info["consumable"]
        )

        available_item_use = [self.default_action["Use"]]
        for item in item_info:
            if item["type"] in ["Armor", "Weapon", "Tool", "Ammunition"]:
                if not item["is_equipped"]:
                    if self.check_level(ego_agent_info, item):
                        available_item_use.append(f"Equip level {item['level']} {item['name']} with id {item['id']}")
                elif item["is_equipped"]:
                    available_item_use.append(f"Unequip level {item['level']} {item['name']} with id {item['id']}")
            elif item["type"] == "Consumable":
                if self.check_level(ego_agent_info, item):
                    available_item_use.append(f"Use level {item['level']} {item['name']} with id {item['id']}")
            else:
                raise ValueError(f"Unknown item type: {item['type']}")
        available_item_use = sorted(available_item_use)
        return available_item_use

    def generate_available_destroy(self, state_info):
        item_info = (
            state_info["armor"]
            + state_info["weapon"]
            + state_info["tool"]
            + state_info["ammunition"]
            + state_info["consumable"]
        )

        available_item_destroy = [self.default_action["Destroy"]]
        for item in item_info:
            if item["type"] in ["Armor", "Weapon", "Tool", "Ammunition"]:
                if not item["is_equipped"]:
                    available_item_destroy.append(f"Destroy level {item['level']} {item['name']} with id {item['id']}")
            elif item["type"] == "Consumable":
                available_item_destroy.append(f"Destroy level {item['level']} {item['name']} with id {item['id']}")
            else:
                raise ValueError(f"Unknown item type: {item['type']}")
        available_item_destroy = sorted(available_item_destroy)
        return available_item_destroy

    def generate_available_give(self, state_info):
        ego_agent_info = state_info["agent"]
        entity_info = state_info["entity"]
        item_info = (
            state_info["armor"]
            + state_info["weapon"]
            + state_info["tool"]
            + state_info["ammunition"]
            + state_info["consumable"]
        )
        available_item_give = [self.default_action["Give"]]
        for item in item_info:
            if item["type"] in ["Armor", "Weapon", "Tool", "Ammunition"] and item["is_equipped"]:
                continue
            for entities in entity_info.values():
                for entity in entities:
                    if entity["id"] != ego_agent_info["id"] and entity["id"] > 0:
                        available_item_give.append(
                            f"Give level {item['level']} {item['name']} with id {item['id']} to Player {entity['id']}"
                        )
        available_item_give = sorted(available_item_give)
        return available_item_give

    def merge_action(self, ml_action, use_action=None, destroy_action=None, give_action=None):
        ml_action = self.available_ml_action_dict[ml_action]
        action = copy.deepcopy(self.default_action)
        action["Move"] = ml_action["Move"]
        action["Attack"] = ml_action["Attack"]
        if use_action:
            action["Use"] = use_action
        if destroy_action:
            action["Destroy"] = destroy_action
        if give_action:
            action["Give"] = give_action
        return action
