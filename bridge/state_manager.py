import json
from collections import defaultdict
import math
import numpy as np
from nmmo.lib import utils
from constant import (
    MATERIAL_NAME_TO_ID,
    ITEM_NAME_TO_ID,
    AREA_SPACE,
    NPC_TYPE_ID_TO_NAME,
    DIRECTION_TO_INDEX,
    ATTACK_STYLE_TO_INDEX,
    PASSABLE_TILE,
    RESOURCE_TILE,
    IMPASSABLE_TILE,
)
from utils.path_utils import a_star_bounded as aStar
from utils.path_utils import l1


def which_part(start, end, x):
    if not (start <= x <= end):
        raise ValueError(f"x is not in the range [{start}, {end}]")

    n = end - start + 1
    base = n // 3
    remainder = n % 3

    if remainder == 0:
        L1 = L2 = base
    elif remainder == 1:
        L1 = base
        L2 = base + 1
    else:  # remainder == 2
        L1 = base + 1
        L2 = base

    b1_end = start + L1 - 1
    b2_end = b1_end + L2

    if x <= b1_end:
        return 0
    elif x <= b2_end:
        return 1
    else:
        return 2


class StateManager:
    def __init__(self, env):
        self.env = env
        self.add_tick_info = True
        self.config = env.config
        self.material_name_to_id = MATERIAL_NAME_TO_ID
        self.material_id_to_name = {v: k for k, v in self.material_name_to_id.items()}
        self.item_name_to_index = ITEM_NAME_TO_ID
        self.item_index_to_name = {v: k for k, v in self.item_name_to_index.items()}
        self.attack_range = {
            "melee": self.config.COMBAT_MELEE_REACH,
            "range": self.config.COMBAT_RANGE_REACH,
            "mage": self.config.COMBAT_MAGE_REACH,
        }
        self.npc_type_id_to_name = NPC_TYPE_ID_TO_NAME
        self.passable_tile = PASSABLE_TILE
        self.resource_tile = RESOURCE_TILE

        self.position_to_areas = None
        self.area_table = {
            (0, 0): "northwest",
            (0, 1): "north",
            (0, 2): "northeast",
            (1, 0): "west",
            (1, 1): "center",
            (1, 2): "east",
            (2, 0): "southwest",
            (2, 1): "south",
            (2, 2): "southeast",
        }
        self.areas = AREA_SPACE
        # self.entity_id_to_index = None

    def get_map_region(self, obs):
        """
        根据agent位置获取所在区域和与地图中心的距离
        """
        min_map_x = self.config.MAP_BORDER
        min_map_y = self.config.MAP_BORDER
        max_map_x = self.config.MAP_CENTER + self.config.MAP_BORDER
        max_map_y = self.config.MAP_CENTER + self.config.MAP_BORDER
        x = obs.agent.row
        y = obs.agent.col
        x_part = which_part(min_map_x, max_map_x, x)
        y_part = which_part(min_map_y, max_map_y, y)
        center = (self.config.MAP_SIZE // 2, self.config.MAP_SIZE // 2)
        dist_to_center = l1((x, y), center)
        return self.area_table[(x_part, y_part)], dist_to_center

    def get_obs_area(self, obs, x, y):
        tiles = obs.tiles
        min_map_x = np.min(tiles[:, 0])
        min_map_y = np.min(tiles[:, 1])
        max_map_x = np.max(tiles[:, 0])
        max_map_y = np.max(tiles[:, 1])
        x_part = which_part(min_map_x, max_map_x, x)
        y_part = which_part(min_map_y, max_map_y, y)
        return self.area_table[(x_part, y_part)]

    def get_ego_agent_info(self, obs):
        """
        agent info示例如下:
        "id": 2,
        "npc_type": 0,
        "row": 43,
        "col": 144,
        "tile_type": "Foliage",
        "water_around":False,
        "region": "southeast",
        "dist_to_center": 101,
        "dist_to_safety_zone": 0,
        "damage": 0,
        "time_alive": 1,
        "freeze": 0,
        "item_level": 0,
        "attacker_id": 0,
        "latest_combat_tick": 0,
        "message": 0,
        "gold": 0,
        "health": 100,
        "food": 95,
        "water": 95,
        "melee_level": 1,
        "melee_exp": 0,
        "range_level": 1,
        "range_exp": 0,
        "mage_level": 1,
        "mage_exp": 0,
        "fishing_level": 1,
        "fishing_exp": 0,
        "herbalism_level": 1,
        "herbalism_exp": 0,
        "prospecting_level": 1,
        "prospecting_exp": 0,
        "carving_level": 1,
        "carving_exp": 0,
        "alchemy_level": 1,
        "alchemy_exp": 0,
        "current_tick": 1,
        "agent_in_combat": false,
        "attacker": 1,
        "target_of_attack": 5,
        "ego_damage": 20,
        "attacker_damage": 20
        """

        # print(obs.tiles)
        agent = vars(obs.agent)
        ego_agent_info = {}
        for key, value in agent.items():
            ego_agent_info[key] = value
        tile = self.env.realm.map.tiles[ego_agent_info["row"], ego_agent_info["col"]]
        tile_resource = self.material_id_to_name[tile.state.index]
        ego_agent_info["title_type"] = tile_resource
        ego_agent_info["water_around"] = False
        ego_agent_info["fish_around"] = False
        four_directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for direction in four_directions:
            neighbor_pos = (ego_agent_info["row"] + direction[0], ego_agent_info["col"] + direction[1])
            if self.env.realm.map.is_valid_pos(neighbor_pos[0], neighbor_pos[1]):
                neighbor_tile = self.env.realm.map.tiles[neighbor_pos[0], neighbor_pos[1]]
                neighbor_tile_resource = self.material_id_to_name[neighbor_tile.state.index]
                if neighbor_tile_resource == "Water":
                    ego_agent_info["water_around"] = True
                if neighbor_tile_resource == "Fish":
                    ego_agent_info["fish_around"] = True
                if ego_agent_info["fish_around"] or ego_agent_info["water_around"]:
                    break

        ego_agent_info["name"] = f"Player {obs.agent.id}"
        ego_agent_info["region"], ego_agent_info["dist_to_center"] = self.get_map_region(obs)
        if self.config.DEATH_FOG_ONSET:
            ego_agent_info["dist_to_safety_zone"] = max(
                ego_agent_info["dist_to_center"] - self.config.DEATH_FOG_FINAL_SIZE // 2, 0
            )
        else:
            ego_agent_info["dist_to_safety_zone"] = 0
        ego_agent_info["current_tick"] = obs.current_tick
        ego_agent_info["agent_in_combat"] = obs.agent_in_combat

        # 注意：由于环境设定的问题，该字段有时候并不准确
        ego_agent_info["attacker"] = None
        ego_agent_info["target_of_attack"] = None
        ego_agent_info["ego_damage"] = None
        ego_agent_info["attacker_damage"] = None
        if obs.agent_in_combat:
            if obs.agent.attacker_id != 0:
                ego_agent_info["attacker"] = (
                    f"NPC {-obs.agent.attacker_id}" if obs.agent.attacker_id < 0 else f"Player {obs.agent.attacker_id}"
                )
                ego_agent_info["attacker_damage"] = obs.agent.damage
            for entity in obs.entities.values:
                if entity[8] == ego_agent_info["id"]:  # 攻击者为ego agent
                    ego_agent_info["target_of_attack"] = f"NPC {-entity[0]}" if entity[0] < 0 else f"Player {entity[0]}"
                    ego_agent_info["ego_damage"] = entity[4]
        return ego_agent_info

    def get_fog_info(self, obs):
        """
        fog_info示例如下:
        "status": "in_fog",
        "postion": 1.0,
        "damage": 1.0
        """
        assert self.config.DEATH_FOG_ONSET
        pos_r = obs.agent.row
        pos_c = obs.agent.col
        fog_info = {area: {"status": "out_of_fog", "damage": 0} for area in self.areas}
        for tile in obs.tiles:
            area = self.get_obs_area(obs, tile[0], tile[1])
            fog_value = float(self.env.realm.fog_map[tile[0], tile[1]])
            if fog_value > 0.5:
                if fog_info[area]["status"] != "in_safety":
                    fog_info[area]["status"] = "in_fog"
                    fog_info[area]["damage"] = abs(fog_value)
            elif math.isclose(fog_value, 0.0, abs_tol=1e-10):
                if fog_info[area]["status"] != "in_fog":
                    fog_info[area]["status"] = "on_the_edge"
                    fog_info[area]["damage"] = 0
            elif fog_value < 0 and fog_value > -self.config.MAP_SIZE:
                fog_info[area]["status"] = "in_safety"
                fog_info[area]["damage"] = 0

        # fog_value = float(self.env.realm.fog_map[pos_r, pos_c])
        # if fog_value > 0.5:
        #     fog_info["center"]["status"] = "in_fog"
        #     fog_info["center"]["damage"] = abs(fog_value)
        # elif math.isclose(fog_value, 0.0, abs_tol=1e-10):
        #     if fog_info["center"]["status"] != "in_fog":
        #         fog_info["center"]["status"] = "on_the_edge"
        #         fog_info["center"]["damage"] = 0
        # elif fog_value < 0 and fog_value == -self.config.MAP_SIZE:
        #     if fog_info["center"]["status"] != "in_fog":
        #         fog_info["center"]["status"] = "in_safety"
        #         fog_info["center"]["damage"] = 0

        return fog_info

    def get_resource_info(self, obs):
        resource_info = {area: [] for area in self.areas}
        resource_visible_count = {area: defaultdict(int) for area in self.areas}
        resource_access_count = {area: None for area in self.areas}
        # resource_distance = {}

        for tile in obs.tiles:
            resource_name = self.material_id_to_name[tile[2]]
            area = self.get_obs_area(obs, tile[0], tile[1])

            if resource_name in self.resource_tile:
                resource_visible_count[area][resource_name] += 1
            if resource_name == "Void":  # 只用于统计边界
                resource_visible_count[area][resource_name] += 1

        for area in self.areas:
            resource_access_count[area] = {k: v for k, v in resource_visible_count[area].items() if v > 0}

        start_pos = (obs.agent.row, obs.agent.col)

        tiles = obs.tiles
        min_map_x = np.min(tiles[:, 0])
        min_map_y = np.min(tiles[:, 1])
        max_map_x = np.max(tiles[:, 0])
        max_map_y = np.max(tiles[:, 1])
        bounds = (min_map_x, max_map_x, min_map_y, max_map_y)

        for resource_name in resource_visible_count.keys():
            if resource_name == "Void":
                resource_access_count[area][resource_name] = resource_visible_count[area][resource_name]
                continue

            # distance_list = []
            for tile in obs.tiles:
                area = self.get_obs_area(obs, tile[0], tile[1])
                # resource_access_count[area]["tile_num"] += 1
                target_pos_list = []
                if self.material_id_to_name[tile[2]] == resource_name:
                    if resource_name in self.passable_tile:
                        target_pos_list.append((tile[0], tile[1]))
                    else:
                        # 处理水和鱼等不可通行的资源
                        four_direction = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                        for direction in four_direction:
                            candidate_pos = (tile[0] + direction[0], tile[1] + direction[1])
                            if (
                                self.env.realm.map.is_valid_pos(candidate_pos)
                                and not self.env.realm.map.tiles[candidate_pos].impassible
                            ):
                                target_pos_list.append(candidate_pos)
                    if target_pos_list:
                        distances = []
                        for target_pos in target_pos_list:
                            _, distance = aStar(self.env.realm.map, start_pos, target_pos, bounds=bounds)
                            distances.append(distance)
                        min_distance = min(distances)
                        if min_distance != float("inf"):
                            resource_access_count[area][resource_name] += 1
        for area in self.areas:
            for resource_name in resource_access_count[area].keys():
                resource_info[area].append(
                    {
                        # "id": self.material_name_to_id[resource_name],
                        "name": resource_name,
                        # "count": resource_visible_count[resource_name],
                        "access_count": resource_access_count[area][resource_name],
                        # "distance": resource_distance[resource_name],
                    }
                )
        return resource_info

    def get_reachable_area_info(self, obs):
        
        tiles = obs.tiles
        min_map_x = np.min(tiles[:, 0])
        min_map_y = np.min(tiles[:, 1])
        max_map_x = np.max(tiles[:, 0])
        max_map_y = np.max(tiles[:, 1])
        bounds = (min_map_x, max_map_x, min_map_y, max_map_y)
    
        reachable_area_info = {area: True for area in self.areas}
        unreachable_tile_count = {area: 0 for area in self.areas}
        all_tile_count = {area: 0 for area in self.areas}
        for tile in obs.tiles:
            resource_name = self.material_id_to_name[tile[2]]
            area = self.get_obs_area(obs, tile[0], tile[1])
            all_tile_count[area] += 1
            if resource_name in IMPASSABLE_TILE or resource_name == "Void":
                unreachable_tile_count[area] += 1
            else:
                start_pos = (obs.agent.row, obs.agent.col)
                target_pos = (tile[0], tile[1])
                _, distance = aStar(self.env.realm.map, start_pos, target_pos, bounds=bounds)
                if distance == float("inf"):
                    unreachable_tile_count[area] += 1
        for area in self.areas:
            if unreachable_tile_count[area] / all_tile_count[area] >= 0.8:
                reachable_area_info[area] = False
        return reachable_area_info

    def get_entity_info(self, obs):
        entity_info = {area: [] for area in self.areas}
        ego_pos = (obs.agent.row, obs.agent.col)

        if obs.entities:
            for i, entity in enumerate(obs.entities.values):
                assert entity[0] == obs.entities.ids[i]
                if entity[0] == obs.agent.id:
                    continue

                damage = entity[4]
                melee_level = entity[15]
                range_level = entity[17]
                mage_level = entity[19]

                if melee_level > range_level and melee_level > mage_level:
                    style = "melee"
                elif range_level > melee_level and range_level > mage_level:
                    style = "range"
                elif mage_level > melee_level and mage_level > range_level:
                    style = "mage"
                else:
                    style = "melee"

                # 添加战斗状态信息
                in_combat = False
                attacker = None
                target_of_attack = None
                if entity[8] != 0:
                    in_combat = True
                    attacker = f"NPC {-entity[8]}" if entity[8] < 0 else f"Player {entity[8]}"
                for other_entity in obs.entities.values:
                    if other_entity[0] != entity[0] and other_entity[8] == entity[0]:
                        in_combat = True
                        target_of_attack = f"NPC {-other_entity[0]}" if other_entity[0] < 0 else f"Player {other_entity[0]}"

                entity_pos = (entity[2], entity[3])
                entity_area = self.get_obs_area(obs, entity[2], entity[3])

                # _, distance = aStar(self.env.realm.map, ego_pos, entity_pos)

                entity_attackable = False
                player_attackable = False

                straight_dis = utils.linf_single(ego_pos, entity_pos)
                if straight_dis <= self.attack_range[style]:
                    player_attackable = True
                for style in ["melee", "range", "mage"]:
                    if straight_dis <= self.attack_range[style]:
                        entity_attackable = True
                entity_info[entity_area].append(
                    {
                        "id": entity[0],
                        "name": f"NPC {-entity[0]}" if entity[0] < 0 else f"Player {entity[0]}",
                        "type": self.npc_type_id_to_name[entity[1]],
                        "style": style,
                        "damage": damage,
                        "position": entity_pos,
                        "health": entity[12],
                        "level": max(melee_level, range_level, mage_level),
                        # "distance": distance,
                        "player_attackable": player_attackable,
                        "entity_attackable": entity_attackable,
                        # 添加战斗状态信息
                        "in_combat": in_combat,
                        "attacker": attacker,
                        "target_of_attack": target_of_attack,
                    }
                )
        return entity_info

    def get_armor_info(self, obs):
        armor_info = []
        item_type = "Armor"
        if obs.inventory:
            for item in obs.inventory.values:
                item_id = item[0]
                item_name = self.item_index_to_name[item[1]]
                item_level = item[3]
                if item_name in ["Hat", "Top", "Bottom"]:
                    is_equipped = item[14]
                    melee_defense = item[9]
                    range_defense = item[10]
                    mage_defense = item[11]
                    armor = {
                        "id": item_id,
                        "name": item_name,
                        "type": item_type,
                        "level": item_level,
                        "is_equipped": is_equipped,
                        "melee_defense": melee_defense,
                        "range_defense": range_defense,
                        "mage_defense": mage_defense,
                    }
                    armor_info.append(armor)
        return armor_info

    def get_weapon_info(self, obs):
        weapon_info = []
        item_type = "Weapon"
        if obs.inventory:
            for item in obs.inventory.values:
                item_id = item[0]
                item_name = self.item_index_to_name[item[1]]
                item_level = item[3]
                if item_name in ["Spear", "Bow", "Wand"]:
                    is_equipped = item[14]
                    melee_attack = item[6]
                    range_attack = item[7]
                    mage_attack = item[8]
                    weapon = {
                        "id": item_id,
                        "name": item_name,
                        "type": item_type,
                        "level": item_level,
                        "is_equipped": is_equipped,
                        "melee_attack": melee_attack,
                        "range_attack": range_attack,
                        "mage_attack": mage_attack,
                    }
                    weapon_info.append(weapon)
        return weapon_info

    def get_tool_info(self, obs):
        tool_info = []
        item_type = "Tool"
        if obs.inventory:
            for item in obs.inventory.values:
                item_id = item[0]
                item_name = self.item_index_to_name[item[1]]
                item_level = item[3]

                if item_name in ["Rod", "Gloves", "Pickaxe", "Axe", "Chisel"]:
                    is_equipped = item[14]
                    melee_defense = item[9]
                    range_defense = item[10]
                    mage_defense = item[11]
                    tool = {
                        "id": item_id,
                        "name": item_name,
                        "type": item_type,
                        "level": item_level,
                        "is_equipped": is_equipped,
                        "melee_defense": melee_defense,
                        "range_defense": range_defense,
                        "mage_defense": mage_defense,
                    }
                    tool_info.append(tool)
        return tool_info

    def get_ammunition_info(self, obs):
        ammunition_info = []
        item_type = "Ammunition"
        if obs.inventory:
            for item in obs.inventory.values:
                item_id = item[0]
                item_name = self.item_index_to_name[item[1]]
                item_level = item[3]
                if item_name in ["Whetstone", "Arrow", "Runes"]:
                    is_equipped = item[14]
                    quantity = item[5]
                    melee_attack = item[6]
                    range_attack = item[7]
                    mage_attack = item[8]
                    ammunition = {
                        "id": item_id,
                        "name": item_name,
                        "type": item_type,
                        "level": item_level,
                        "is_equipped": is_equipped,
                        "quantity": quantity,
                        "range_attack": range_attack,
                        "melee_attack": melee_attack,
                        "mage_attack": mage_attack,
                    }
                    ammunition_info.append(ammunition)
        return ammunition_info

    def get_consumable_info(self, obs):
        consumable_info = []
        item_type = "Consumable"
        if obs.inventory:
            for item in obs.inventory.values:
                item_id = item[0]
                item_name = self.item_index_to_name[item[1]]
                item_level = item[3]

                if item_name in ["Ration", "Potion"]:
                    consumable = {
                        "id": item_id,
                        "name": item_name,
                        "type": item_type,
                        "level": item_level,
                    }
                    if item_name == "Ration":
                        consumable["resource_restore"] = 50 + 5 * item_level
                    elif item_name == "Potion":
                        consumable["health_restore"] = 50 + 5 * item_level
                    consumable_info.append(consumable)
        return consumable_info

    def get_state_info(self, obs):
        state_info = {}
        state_info["agent"] = self.get_ego_agent_info(obs)
        if self.config.DEATH_FOG_ONSET and obs.current_tick >= int(self.config.DEATH_FOG_ONSET):
            state_info["fog"] = self.get_fog_info(obs)
        else:
            state_info["fog"] = None
        state_info["resource"] = self.get_resource_info(obs)
        state_info["reachable_area"] = self.get_reachable_area_info(obs)
        state_info["entity"] = self.get_entity_info(obs)
        state_info["armor"] = self.get_armor_info(obs)
        state_info["weapon"] = self.get_weapon_info(obs)
        state_info["tool"] = self.get_tool_info(obs)
        state_info["ammunition"] = self.get_ammunition_info(obs)
        state_info["consumable"] = self.get_consumable_info(obs)
        state_info["capacity"] = len(obs.inventory.values)

        return state_info
