import sys
import os
import re
import json

current_dir = os.path.abspath(__file__)
sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

from nmmo.lib import utils
from constant import AREA_SPACE
from game_rule import RESOURCE_TABLE, NPC_TABLE, COMBAT_TABLE, ITEM_TABLE, SKILL_TABLE


class PerceptionModule:
    def __init__(self, config, llm_client, save_path, add_tick_info=True, only_use_resource_tile=False, debug=False):
        self.config = config
        self.llm_client = llm_client
        self.save_path = save_path
        self.add_tick_info = add_tick_info
        self.only_use_resource_tile = only_use_resource_tile
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
        description = ""
        state_description = {}

        if self.add_tick_info:
            state_description["tick"] = f"{tick}/{horizon}"
        description += json.dumps(state_description) + "\n"
        # 添加健康信息
        meta_description = (
            "Player has Health, Food, and Water, each with a maximum value of 100. Food/Water drop 10 each tick. If Water or Food is 0, the player loses 10 Health per tick; if both are 0, Health loses 20 per tick. Health regenerates 10 per tick if food and water are above 50. Here is my current health status:\n"
            + self.generate_health_description(state_info["agent"])
        )
        description += meta_description + "\n"

        # 添加宏观位置信息
        position_description = f"The tile is the basic unit that makes up the map. The game map has a total size of {self.config.MAP_CENTER} × {self.config.MAP_CENTER} tiles. Each tile corresponds to a coordinate. My character can move only one tile per tick. The entire game map is roughly divided into nine regions: the central region, eastern region, western region, northern region, southern region, northeastern region, southeastern region, northwestern region, and southwestern region. Players are informed of the coordinate and region they are in to clarify their macro-level position on the map. "

        if self.config.DEATH_FOG_ONSET:
            position_description += f"Additionally, there is a death fog mechanism in the game. The fog area appears at time {self.config.DEATH_FOG_ONSET} and gradually expands from the edges of the map toward the center. The fog can damage player within it. A permanent safety area exists at the center of the map, which is never covered by the fog. The position information includes the distance to the safety zone. \n Here is my current position information:\n"

        position_description += self.generate_position_description(state_info["agent"])
        description += position_description + "\n"

        # 添加资源、实体、战斗等观测信息
        resource_description = "There are various types of resources on the map. Players can obtain corresponding items and improve related skills by harvesting resources. Equipping related tools can improve the quality of harvested items. The harvested item level is the related tool's level + 1. Here is the information about different resources and their corresponding output items, skills, and tools.\n"
        resource_description += json.dumps(RESOURCE_TABLE, indent=4)
        description += resource_description + "\n"

        if self.config.NPC_SYSTEM_ENABLED:
            entity_description = "Entities on the map include NPCs and other players. NPCs are divided into passive, neutral, and aggressive types. Here is the information about different NPC types:\n"
            entity_description += json.dumps(NPC_TABLE, indent=4)
            description += entity_description + "\n"

        if self.config.COMBAT_SYSTEM_ENABLED:
            commbat_description = "Combat may occur between entities. The outcome of combat depends on the entities' attack and defense values. The game has three combat styles: Melee, Range, and Mage. Players can use any combat style, while NPCs can only use one combat style. Equipping specific weapons and ammunition, improving combat skills, and using a combat style that counters the enemy will all increase the attack value of the corresponding style. The weapons, ammunition, skills, and countered combat styles for each combat style are as follows:\n"

            commbat_description += json.dumps(COMBAT_TABLE, indent=4)

            description += commbat_description + "\n"
        view_size = 15
        description += f"In this game, players can only view an area of {view_size} × {view_size} tiles centered on themselves, which is also divided into nine areas: center, eastern, western, northern, southern, northeastern, southeastern, northwestern, and the southwestern area. Players can only directly harvest resources or attack other entities in the center area. Moving to another area makes that area the new center area. Some areas are difficult to traverse. This may be because they contain many impassable tiles (such as rock tiles), or because many tiles are unreachable from the character's current position (for example, blocked by water or stone tiles). Here is information about the resources, entities, fog, and passability of the nine areas in the observation space: \n"

        description += (
            self.generate_observation_description(
                state_info["resource"],
                state_info["entity"],
                state_info["passible"],
                state_info["fog"],
            )
            + "\n"
        )
        if self.config.ITEM_SYSTEM_ENABLED:

            item_description = "Items are very helpful for player survival and combat. Based on their functions, acquisition methods, and skill requirements, items are divided into weapons, ammunition, armor, tools, and consumables. Armor and tools can only be obtained by killing other NPCs or players as drops. Weapons, ammunition, armor, and tools must be equipped to take effect. High-level items require the corresponding skills to reach the same level in order to be used. The names, functions, acquisition methods, and corresponding skill of all items are listed below:\n"

            item_description += json.dumps(ITEM_TABLE, indent=4)
            description += item_description + "\n" + "Here is my current inventory information:\n"
            description += (
                self.generate_item_description(
                    state_info["capacity"],
                    state_info["armor"],
                    state_info["weapon"],
                    state_info["tool"],
                    state_info["ammunition"],
                    state_info["consumable"],
                )
                + "\n"
            )

        if self.config.PROGRESSION_SYSTEM_ENABLED:
            skill_description = "Higher skill levels allow players to obtain better yields when harvesting resources, use higher-level equipment, and deal greater damage. The maximum level of items that a player can harvest or use is equal to the relevant skill level plus one. Below are the resources affected by each skill, the items they enable, and the ways in which the skills are leveled up:\n"
            skill_description += json.dumps(SKILL_TABLE, indent=4)
            description += skill_description + "\nHere is my current skill levels:\n"
            description += self.generate_skill_description(state_info["agent"]) + "\n"

        # print(description)
        return description

    def generate_health_description(self, ego_agent_info):
        return json.dumps(
            {"health": ego_agent_info["health"], "food": ego_agent_info["food"], "water": ego_agent_info["water"]}
        )

    def generate_position_description(self, ego_agent_info):
        description = {}
        description["region"] = ego_agent_info["region"]
        description["map_coordinates"] = f"({ego_agent_info['row']}, {ego_agent_info['col']})"
        if self.config.DEATH_FOG_ONSET:
            if ego_agent_info["dist_to_safety_zone"] <= 0:
                description["in_safety_zone"] = True
            else:
                description["in_safety_zone"] = False
                description["dist_to_safety_zone"] = ego_agent_info["dist_to_safety_zone"]
        return json.dumps(description, indent=4)

    def generate_observation_description(self, resource_info, entity_info, passible_info, fog_info):

        description = {area: {} for area in self.areas}
        for area in self.areas:
            # 补充资源信息
            if resource_info[area]:
                description[area]["resources"] = []
                for resource_name, this_resource_info in resource_info[area].items():
                    if self.only_use_resource_tile and not this_resource_info["is_resource"]:
                        continue
                    single_resource_info = {
                        "name": resource_name,
                        "count": int(this_resource_info["count"]),
                        "is_resource": bool(this_resource_info["is_resource"]),
                        "passible": bool(this_resource_info["passible"]),
                    }
                    if "original_resource" in this_resource_info:
                        single_resource_info["original_resource"] = this_resource_info["original_resource"]
                    description[area]["resources"].append(single_resource_info)
                description[area]["resources"] = sorted(description[area]["resources"], key=lambda x: x["count"], reverse=True)

            # 补充实体信息
            if self.config.NPC_SYSTEM_ENABLED and entity_info[area]:
                description[area]["entities"] = []
                for entity in entity_info[area]:
                    single_entity_info = {
                        "name": entity["name"],
                        "type": entity["type"],
                        "combat_style": entity["style"],
                        "health": int(entity["health"]),
                        "level": int(entity["level"]),
                        "in_combat": bool(entity["in_combat"]),
                    }
                    if entity["in_combat"]:
                        single_entity_info["attacked_by"] = entity["attacker"]
                        single_entity_info["attack_target"] = entity["target_of_attack"]
                    description[area]["entities"].append(single_entity_info)

            # 补充迷雾信息
            if self.config.DEATH_FOG_ONSET and fog_info[area]:
                description[area]["fog"] = {
                    "out_of_fog_tile_count": int(fog_info[area]["out_of_fog_count"]),
                    "in_fog_tile_count": int(fog_info[area]["in_fog_count"]),
                    "on_edge_tile_count": int(fog_info[area]["on_edge_count"]),
                }
            # 补充可通行性信息
            description[area]["visited_tile_count"] = passible_info[area]["visited_tile_count"]
            description[area]["passible_tile_count"] = passible_info[area]["passible_tile_count"]
            description[area]["reachable_tile_count"] = passible_info[area]["reachable_tile_count"]
        return json.dumps(description, indent=4)

    def generate_item_description(
        self,
        capacity,
        armor_info,
        weapon_info,
        tool_info,
        ammunition_info,
        consumable_info,
    ):
        description = {}
        description["item_number"] = capacity
        description["capacity"] = 12
        description["items"] = []
        if armor_info:
            for armor in armor_info:
                single_item_info = {
                    "id": int(armor["id"]),
                    "name": armor["name"],
                    "type": armor["type"],
                    "level": int(armor["level"]),
                    "defense": int(armor["melee_defense"]),
                    "is_equipped": bool(armor["is_equipped"]),
                }
                description["items"].append(single_item_info)
        if weapon_info:
            for weapon in weapon_info:
                single_item_info = {
                    "id": int(weapon["id"]),
                    "name": weapon["name"],
                    "type": weapon["type"],
                    "level": int(weapon["level"]),
                    "melee_attack": int(weapon["melee_attack"]),
                    "range_attack": int(weapon["range_attack"]),
                    "mage_attack": int(weapon["mage_attack"]),
                    "is_equipped": bool(weapon["is_equipped"]),
                }
                description["items"].append(single_item_info)
        if tool_info:
            for tool in tool_info:
                single_item_info = {
                    "id": int(tool["id"]),
                    "name": tool["name"],
                    "type": tool["type"],
                    "level": int(tool["level"]),
                    "defense": int(tool["melee_defense"]),
                    "is_equipped": bool(tool["is_equipped"]),
                }
                description["items"].append(single_item_info)
        if ammunition_info:
            for ammunition in ammunition_info:
                single_item_info = {
                    "id": int(ammunition["id"]),
                    "name": ammunition["name"],
                    "type": ammunition["type"],
                    "level": int(ammunition["level"]),
                    "quantity": int(ammunition["quantity"]),
                    "melee_attack": int(ammunition["melee_attack"]),
                    "range_attack": int(ammunition["range_attack"]),
                    "mage_attack": int(ammunition["mage_attack"]),
                    "is_equipped": bool(ammunition["is_equipped"]),
                }
                description["items"].append(single_item_info)
        if consumable_info:
            for consumable in consumable_info:
                single_item_info = {
                    "id": int(consumable["id"]),
                    "name": consumable["name"],
                    "type": consumable["type"],
                    "level": int(consumable["level"]),
                }
                if consumable["name"] == "Ration":
                    single_item_info["resource_restore"] = int(consumable["resource_restore"])
                elif consumable["name"] == "Potion":
                    single_item_info["health_restore"] = int(consumable["health_restore"])
                description["items"].append(single_item_info)

        return json.dumps(description, indent=4)

    def generate_skill_description(self, ego_agent_info):
        description = {}
        for k, v in ego_agent_info.items():
            if "level" in k and k != "item_level":
                skill_name = k.split("_level")[0].capitalize()
                description[skill_name] = int(v)
        return json.dumps(description, indent=4)
