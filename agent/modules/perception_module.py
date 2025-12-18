import sys
import os
import re

current_dir = os.path.abspath(__file__)
sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

from nmmo.lib import utils
from constant import AREA_SPACE


class PerceptionModule:
    def __init__(self, config, llm_client, save_path, add_tick_info=True, debug=False):
        self.config = config
        self.llm_client = llm_client
        self.save_path = save_path
        self.add_tick_info = add_tick_info
        self.debug = debug
        self.attack_range = {
            "melee": self.config.COMBAT_MELEE_REACH,
            "range": self.config.COMBAT_RANGE_REACH,
            "mage": self.config.COMBAT_MAGE_REACH,
        }
        self.areas = AREA_SPACE
        self.directions_to_center = {
            "north": ["south"],
            "northeast": ["southwest", "west", "south"],
            "east": ["west"],
            "southeast": ["northwest", "west", "north"],
            "south": ["north"],
            "southwest": ["northeast", "north", "east"],
            "west": ["east"],
            "northwest": ["southeast", "east", "south"],
        }

    def perceive(self, state_info, tick, horizon):

        description = "## Basic Information\n"

        if self.add_tick_info:
            description += f"Now is tick {tick}/{horizon}. \n"

        description += self.generate_position_description(state_info["agent"])

        # 添加健康信息
        description += self.generate_health_description(state_info["agent"]) + "\n"

        # 添加观察信息
        description += (
            "## Observation Information\n"
            + self.generate_observation_description(
                state_info["agent"],
                state_info["resource"],
                state_info["entity"],
                state_info["reachable_area"],
                state_info["fog"],
            )
            + "\n"
        )

        # available_action["Move"] = self.generate_available_move(state_info["resource"], state_info["entity"])
        # 添加NPC和敌人信息
        if self.config.COMBAT_SYSTEM_ENABLED:
            description += "## Ego's Combat Information\n" + self.generate_ego_combat_description(state_info["agent"]) + "\n"
            description += (
                "## Other's Combat Information\n"
                + self.generate_other_combat_description(state_info["agent"], state_info["entity"])
                + "\n"
            )
            # available_action["Attack"] = self.generate_available_attack(state_info["agent"], state_info["entity"])

        if self.config.ITEM_SYSTEM_ENABLED:
            description += (
                "## Inventory Information\n"
                + self.generate_inventory_description(
                    state_info["capacity"],
                    state_info["agent"],
                    state_info["armor"],
                    state_info["weapon"],
                    state_info["tool"],
                    state_info["ammunition"],
                    state_info["consumable"],
                )
                + "\n"
            )

            if self.config.EQUIPMENT_SYSTEM_ENABLED:
                description += "## Equipment Information\n" + (
                    self.generate_equipment_description(
                        state_info["armor"],
                        state_info["weapon"],
                        state_info["tool"],
                        state_info["ammunition"],
                    )
                    + "\n"
                )

        if self.config.PROGRESSION_SYSTEM_ENABLED:
            description += "## Skill Information\n" + self.generate_skill_description(state_info["agent"])
        return description

    def generate_position_description(self, ego_agent_info):
        region = ego_agent_info["region"]
        dist_to_center = ego_agent_info["dist_to_center"]
        description = f"I am currently located in the {region} region of the map. My distance to the center point of the map is {dist_to_center}. \n"
        if self.config.DEATH_FOG_ONSET:
            if ego_agent_info["current_tick"] >= int(self.config.DEATH_FOG_ONSET):
                description += "The fog area is expanding. "
            else:
                description += "The fog area has not started to expand yet. "
            if ego_agent_info["dist_to_safety_zone"] <= 0:
                description += "I am currently in the safety zone. "
            else:
                description += f"My distance to the safety zone is {ego_agent_info['dist_to_safety_zone']}. "
        description += "\n"
        return description

    def generate_observation_description(self, ego_agent_info, resource_info, entity_info, reachable_area_info, fog_info):
        region = ego_agent_info["region"]
        description = "I am in the center area. The information of the surrounding areas is as follows: \n"
        if not resource_info and not entity_info and not fog_info:
            return description + "No detailed area information is available.\n"

        def format_resource(area):
            if not resource_info[area]:
                return None
            description = ""
            for resource in resource_info[area]:
                if resource["name"] == "Void":
                    continue
                if description == "":
                    description += f"{resource['access_count']} {resource['name']} tiles"
                else:
                    description += f", {resource['access_count']} {resource['name']} tiles"
            if description == "":
                description += "No resource is in this area"
            description += ". "
            return description

        def format_entity(area):
            if not entity_info[area]:
                return None
            description = ""
            for entity in entity_info[area]:
                description += f"{entity['name']}, Type: {entity['type']}, Style: {entity['style']}, Health: {entity['health']}, Level: {entity['level']}. "
                if entity["type"] == "aggressive":
                    description += f" NOTE: This NPC is dangerous."
                # if entity["entity_attackable"]:
                #     description += f" {entity['name']} is in my attack range. "
            return description

        def format_reachable(area):
            if not reachable_area_info[area]:
                return "No path leads to this area as it is blocked by water or stones, or located beyond the map boundary. "
            else:
                return None

        def format_fog(area):
            if not fog_info:
                return None
            description = ""
            if fog_info[area]["status"] == "out_of_fog":
                description += f"This area has not yet been covered by fog. "
            elif fog_info[area]["status"] == "in_fog":
                description += f"This area is currently covered by fog. "
                if area == "center" and fog_info[area]["damage"] > 0:
                    description += f"My health decreases by {int(fog_info[area]['damage'])} per tick. "
            elif fog_info[area]["status"] == "on_the_edge":
                description += f"This area is on the edge of the fog. "
            elif fog_info[area]["status"] == "in_safety":
                description += f"This area is in the safe zone. "
            return description

        def format_direction_to_center(area):
            if region == "center":
                return None
            if area in self.directions_to_center[region]:
                return f"Moving to this area will bring you closer to the center of the map."
            else:
                return None

        for area in self.areas:
            area_description = f"The {area} area: \n"
            if not reachable_area_info[area]:
                area_description += (
                    "No path leads to this area as it is blocked by water or stones, or located beyond the map boundary. "
                )
                description += area_description + "\n"
                continue
            fog_description = format_fog(area)
            resource_description = format_resource(area)
            entity_description = format_entity(area)
            direction_description = format_direction_to_center(area)
            # reachable_description = format_reachable(area)
            if fog_description:
                area_description += "Fog Status: \n"
                area_description += fog_description + "\n"
            if resource_description:
                area_description += "Resources: \n"
                area_description += resource_description + "\n"
            else:
                area_description += "No resource is in this area. \n"
            if entity_description:
                area_description += "NPCs or Players: \n"
                area_description += entity_description + "\n"
            else:
                area_description += "No NPC or Player is in this area. \n"
            # if reachable_description:
            #     area_description += reachable_description + "\n"
            if direction_description:
                area_description += direction_description + "\n"

            description += area_description + "\n"
        return description

    def generate_ego_combat_description(self, ego_agent_info):
        if ego_agent_info["agent_in_combat"]:
            description = "I am in a combat. \n"
            if ego_agent_info["target_of_attack"]:
                description += (
                    f"I am attacking {ego_agent_info['target_of_attack']} with damage {ego_agent_info['attacker_damage']}. \n"
                )
            if ego_agent_info["attacker"]:
                description += f"I am attacked by {ego_agent_info['attacker']} with damage {ego_agent_info['ego_damage']}.\n"

            if not ego_agent_info["attacker"] and not ego_agent_info["target_of_attack"]:
                description += f"I just finished a combat\n"
        else:
            description = f"I am not currently in combat. \n"
        return description

    def generate_other_combat_description(self, ego_agent_info, entity_info):
        description = ""
        for area in self.areas:
            for entity in entity_info[area]:
                if entity["in_combat"]:
                    description += f"{entity['name']} is in combat.\n"
                    if entity["target_of_attack"]:
                        if entity["target_of_attack"] == f"Player {ego_agent_info['id']}":
                            description += f"{entity['name']} is attacking me.\n"
                        else:
                            description += f"{entity['name']} is attacking {entity['target_of_attack']}.\n"
                    if entity["attacker"]:
                        if entity["attacker"] == f"Player {ego_agent_info['id']}":
                            description += f"{entity['name']} is attacked by me.\n"
                        else:
                            description += f"{entity['name']} is attacked by {entity['attacker']}.\n"
        if description == "":
            description = "No combat information observed. \n"
        return description

    def generate_health_description(self, ego_agent_info):
        description = f"My health is {ego_agent_info['health']}/100, my food is {ego_agent_info['food']}/100, my water is {ego_agent_info['water']}/100. \n"
        return description

    def generate_skill_description(self, ego_agent_info):
        description = f"My skill levels are: \n"
        for k, v in ego_agent_info.items():
            if "level" in k and k != "item_level":
                skill_name = k.split("_level")[0].capitalize()
                description += f"{skill_name} Level: {v}. \n"
        return description

    def generate_armor_description(self, armor_info):
        if armor_info:
            description = ""
            equipped_armor = [armor for armor in armor_info if armor["is_equipped"]]

            if equipped_armor:
                description += f"My equipped armor is: \n"
                for armor in equipped_armor:
                    description += f"item id: {armor['id']}, name: {armor['name']},  level: {armor['level']}, melee defense: {armor['melee_defense']}, range defense: {armor['range_defense']}, mage defense: {armor['mage_defense']}. \n"

            unequipped_armor = [armor for armor in armor_info if not armor["is_equipped"]]
            if unequipped_armor:
                description += f"My unequipped armor is: \n"
                for armor in unequipped_armor:
                    description += f"item id: {armor['id']},{armor['name']}, level: {armor['level']}, melee defense: {armor['melee_defense']}, range defense: {armor['range_defense']}, mage defense: {armor['mage_defense']}. \n"
        else:
            description = "I don't have any armor. \n"
        return description

    def generate_equipment_description(self, armor_info, weapon_info, tool_info, ammunition_info):
        equipped_hat = [armor for armor in armor_info if armor["name"] == "Hat" and armor["is_equipped"]]
        equipped_top = [armor for armor in armor_info if armor["name"] == "Top" and armor["is_equipped"]]
        equipped_bottom = [armor for armor in armor_info if armor["name"] == "Bottom" and armor["is_equipped"]]
        equipped_weapon = [weapon for weapon in weapon_info if weapon["is_equipped"]]
        equipped_tool = [tool for tool in tool_info if tool["is_equipped"]]
        equipped_ammunition = [ammunition for ammunition in ammunition_info if ammunition["is_equipped"]]
        description = ""

        if equipped_hat:
            armor = equipped_hat[0]
            description += f"My Hat slot is equipped with: \nitem id: {armor['id']}, name: {armor['name']}, level: {armor['level']}, melee defense: {armor['melee_defense']}, range defense: {armor['range_defense']}, mage defense: {armor['mage_defense']}. \n"
        else:
            description += "My Hat slot is empty. \n"

        if equipped_top:
            armor = equipped_top[0]
            description += f"My Top slot is equipped with: \nitem id: {armor['id']}, name: {armor['name']}, level: {armor['level']}, melee defense: {armor['melee_defense']}, range defense: {armor['range_defense']}, mage defense: {armor['mage_defense']}. \n"
        else:
            description += "My Top slot is empty. \n"

        if equipped_bottom:
            armor = equipped_bottom[0]
            description += f"My Bottom slot is equipped with: \nitem id: {armor['id']}, name: {armor['name']}, level: {armor['level']}, melee defense: {armor['melee_defense']}, range defense: {armor['range_defense']}, mage defense: {armor['mage_defense']}. \n"
        else:
            description += "My Bottom slot is empty. \n"

        if equipped_weapon or equipped_tool:
            if equipped_weapon:
                weapon = equipped_weapon[0]
                description += f"My Weapon/Tool slot is equipped with: \nitem id: {weapon['id']}, name: {weapon['name']}, level: {weapon['level']}, melee attack: {weapon['melee_attack']}, range attack: {weapon['range_attack']}, mage attack: {weapon['mage_attack']}. \n"

            if equipped_tool:
                tool = equipped_tool[0]
                description += f"My Weapon/Tool slot is equipped with: \nitem id: {tool['id']}, name: {tool['name']}, level: {tool['level']}, melee defense: {tool['melee_defense']}, range defense: {tool['range_defense']}, mage defense: {tool['mage_defense']}. \n"
        else:
            description += "My Weapon/Tool slot is empty. \n"

        if equipped_ammunition:
            ammunition = equipped_ammunition[0]
            description += f"My Ammunition slot is equipped with: \nitem id: {ammunition['id']}, name: {ammunition['name']}, level: {ammunition['level']}, quantity: {ammunition['quantity']}, range attack: {ammunition['range_attack']}, melee attack: {ammunition['melee_attack']}, mage attack: {ammunition['mage_attack']}. \n"
        else:
            description += "My Ammunition slot is empty. \n"
        return description

    def generate_inventory_description(
        self,
        capacity,
        ego_agent_info,
        armor_info,
        weapon_info,
        tool_info,
        ammunition_info,
        consumable_info,
    ):
        if capacity > 0:
            description = f"My inventory capacity is {capacity}/12 and contains the following items: \n"
        else:
            description = f"My inventory is empty. \n"
        if armor_info:
            for armor in armor_info:
                description += f"item id: {armor['id']}, name: {armor['name']}, level: {armor['level']}, melee defense: {armor['melee_defense']}, range defense: {armor['range_defense']}, mage defense: {armor['mage_defense']}. "
                if not self.check_level(ego_agent_info, armor):
                    description += "I cannot currently equip this armor due to level restriction. "
                description += "\n"
        if weapon_info:
            for weapon in weapon_info:
                description += f"item id: {weapon['id']}, name: {weapon['name']}, level: {weapon['level']}, melee attack: {weapon['melee_attack']}, range attack: {weapon['range_attack']}, mage attack: {weapon['mage_attack']}. "
                if not self.check_level(ego_agent_info, weapon):
                    description += "I cannot currently equip this weapon due to level restriction. "
                description += "\n"
        if tool_info:
            for tool in tool_info:
                description += f"item id: {tool['id']}, name: {tool['name']}, level: {tool['level']}, melee defense: {tool['melee_defense']}, range defense: {tool['range_defense']}, mage defense: {tool['mage_defense']}. "
                if not self.check_level(ego_agent_info, tool):
                    description += "I cannot currently equip this tool due to level restriction. "
                description += "\n"
        if ammunition_info:
            for ammunition in ammunition_info:
                description += f"item id: {ammunition['id']}, name: {ammunition['name']}, level: {ammunition['level']}, quantity: {ammunition['quantity']}, range attack: {ammunition['range_attack']}, melee attack: {ammunition['melee_attack']}, mage attack: {ammunition['mage_attack']}. "
                if not self.check_level(ego_agent_info, ammunition):
                    description += "I cannot currently equip this ammunition due to level restriction. "
                description += "\n"
        if consumable_info:
            for consumable in consumable_info:
                if consumable["name"] == "Ration":
                    description += f"item id: {consumable['id']}, name: {consumable['name']}, level: {consumable['level']}, resource restore: {consumable['resource_restore']}. "
                elif consumable["name"] == "Potion":
                    description += f"item id: {consumable['id']}, name: {consumable['name']}, level: {consumable['level']}, health restore: {consumable['health_restore']}. "
                if not self.check_level(ego_agent_info, consumable):
                    description += "I cannot currently use this consumable due to level restriction. "
                description += "\n"
        return description

    def get_attackable_entity(self, ego_agent_info, entity_info, attack_range):
        # 视野与攻击的范围不同
        attackable_entity = []
        agent_pos = (ego_agent_info["row"], ego_agent_info["col"])

        for entity in entity_info:
            if entity["id"] == ego_agent_info["id"]:  # 跳过自己
                continue

            entity_pos = entity["position"]  # 实体的位置
            distance = utils.linf_single(agent_pos, entity_pos)
            if distance <= attack_range:
                attackable_entity.append(
                    {
                        "id": entity["id"],
                        "distance": distance,
                    }
                )

        return attackable_entity

    def generate_available_attack(self, ego_agent_info, entity_info):
        available_attack = []

        for style, attack_range in self.attack_range.items():
            attackable_entity = self.get_attackable_entity(ego_agent_info, entity_info, attack_range)
            for entity in attackable_entity:
                if entity["id"] < 0 and self.config.NPC_SYSTEM_ENABLED:
                    available_attack.append(f"Attack NPC {entity['id']} with {style}.")
                else:
                    available_attack.append(f"Attack Player {entity['id']} with {style}.")
        available_attack.append("Attack nothing.")
        return available_attack

    def generate_available_item_use(self, ego_agent_info, item_info):
        if not item_info or ego_agent_info["agent_in_combat"]:
            return ""

        available_item_use = []
        for item in item_info:
            if item["type"] in ["Armor", "Weapon", "Tool", "Ammunition"]:
                if not item["is_equipped"]:
                    if self.check_level(ego_agent_info, item):
                        available_item_use.append(f"Equip level {item['level']} {item['name']} with id {item['id']}.")
                elif item["is_equipped"]:
                    available_item_use.append(f"Unequip level {item['level']} {item['name']} with id {item['id']}.")
            elif item["type"] == "Consumable":
                if self.check_level(ego_agent_info, item):
                    available_item_use.append(f"Use level {item['level']} {item['name']} with id {item['id']}.")
            else:
                raise ValueError(f"Unknown item type: {item['type']}")
        return available_item_use

    def generate_available_destroy(self, ego_agent_info, item_info):
        if not item_info or ego_agent_info["agent_in_combat"]:
            return ""

        available_item_destroy = []
        for item in item_info:
            if item["type"] in ["Armor", "Weapon", "Tool", "Ammunition"]:
                if not item["is_equipped"]:
                    available_item_destroy.append(f"Destroy level {item['level']} {item['name']} with id {item['id']}.")
            elif item["type"] == "Consumable":
                available_item_destroy.append(f"Destroy level {item['level']} {item['name']} with id {item['id']}.")
            else:
                raise ValueError(f"Unknown item type: {item['type']}")
        return available_item_destroy

    def generate_available_give(self, ego_agent_info, entity_info, item_info):
        if not item_info or ego_agent_info["agent_in_combat"]:
            return ""

        available_item_give = []
        for item in item_info:
            if item["type"] in ["Armor", "Weapon", "Tool", "Ammunition"] and item["is_equipped"]:
                continue
            for entity in entity_info:
                if entity["id"] != ego_agent_info["id"] and entity["id"] > 0:
                    available_item_give.append(
                        f"Give level {item['level']} {item['name']} with id {item['id']} to Player {entity['id']}."
                    )
        return available_item_give

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
