from collections import defaultdict
from collections.abc import Iterable
import re

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
)

from utils.path_utils import a_star_bounded as aStar


# pylint: disable=invalid-name


def range_midpoints(start, end):
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

    # 计算每段的范围
    s1, e1 = start, start + L1 - 1
    s2, e2 = e1 + 1, e1 + L2
    s3, e3 = e2 + 1, end

    # 计算中点
    mid1 = (s1 + e1) / 2
    mid2 = (s2 + e2) / 2
    mid3 = (s3 + e3) / 2

    return mid1, mid2, mid3


class ActionManager:
    def __init__(self, env, path_find_depth=2):
        self.env = env
        self.config = env.config
        self.map_size = env.config.MAP_CENTER
        self.direction_to_index = DIRECTION_TO_INDEX
        self.material_name_to_id = MATERIAL_NAME_TO_ID
        self.material_id_to_name = {v: k for k, v in self.material_name_to_id.items()}
        self.item_index_to_name = ITEM_NAME_TO_ID
        self.item_name_to_index = {v: k for k, v in self.item_index_to_name.items()}
        self.attack_range = {
            "melee": self.config.COMBAT_MELEE_REACH,
            "range": self.config.COMBAT_RANGE_REACH,
            "mage": self.config.COMBAT_MAGE_REACH,
        }
        self.area_space = AREA_SPACE
        self.npc_type_id_to_name = NPC_TYPE_ID_TO_NAME
        self.attack_style_to_index = ATTACK_STYLE_TO_INDEX
        self.passable_tile = PASSABLE_TILE
        self.resource_tile = RESOURCE_TILE

        self.path_find_depth = path_find_depth

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
        self.area_index = {v: k for k, v in self.area_table.items()}

    def move_to_area(self, obs, target_area):
        tiles = obs.tiles
        min_map_x = np.min(tiles[:, 0])
        min_map_y = np.min(tiles[:, 1])
        max_map_x = np.max(tiles[:, 0])
        max_map_y = np.max(tiles[:, 1])
        bounds = (min_map_x, max_map_x, min_map_y, max_map_y)

        x_index = self.area_index[target_area][0]
        y_index = self.area_index[target_area][1]
        target_x = int(range_midpoints(min_map_x, max_map_x)[x_index])
        target_y = int(range_midpoints(min_map_y, max_map_y)[y_index])

        current_x = obs.agent.row
        current_y = obs.agent.col
        four_direction = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        target_pos_list = [(target_x, target_y)]
        for eu_dis in range(1, self.path_find_depth + 1):
            for one_direction in four_direction:
                target_pos_list.append((target_x + eu_dis * one_direction[0], target_y + eu_dis * one_direction[1]))
        for target_pos in target_pos_list:
            if (
                self.env.realm.map.is_valid_pos(target_pos[0], target_pos[1])
                and not self.env.realm.map.tiles[target_pos[0], target_pos[1]].impassible
            ):
                direction, true_distance = aStar(self.env.realm.map, (current_x, current_y), target_pos, bounds=bounds)
                if true_distance != float("inf"):
                    return self.direction_to_index[direction]
        return self.direction_to_index[(0, 0)]

    def execute(self, obs, ml_action):
        action = {}

        move_action = self.move(obs, ml_action["Move"])
        action["Move"] = {"Direction": move_action}

        entity_id, style = self.attack(obs, ml_action["Attack"])
        action["Attack"] = {"Target": entity_id, "Style": style}

        item_id = self.use(obs, ml_action["Use"])
        action["Use"] = {"InventoryItem": item_id}

        item_id = self.destroy(obs, ml_action["Destroy"])
        action["Destroy"] = {"InventoryItem": item_id}

        item_id, entity_id = self.give(obs, ml_action["Give"])
        action["Give"] = {"InventoryItem": item_id, "Target": entity_id}

        return action

    def move_to_nearest_resource(self, obs, resource_name):
        # resource_index = self.resource_name_to_id[resource_name]
        tiles = obs.tiles
        min_map_x = np.min(tiles[:, 0])
        min_map_y = np.min(tiles[:, 1])
        max_map_x = np.max(tiles[:, 0])
        max_map_y = np.max(tiles[:, 1])
        bounds = (min_map_x, max_map_x, min_map_y, max_map_y)
        resource_dis = []
        start_pos = (obs.agent.row, obs.agent.col)
        for tile in obs.tiles:
            if self.material_id_to_name[tile[2]] == resource_name:
                if resource_name in self.passable_tile:
                    target_pos_list = [(tile[0], tile[1])]
                else:
                    # 处理水和鱼等不可接近的资源
                    four_direction = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    target_pos_list = [
                        (tile[0] + direction[0], tile[1] + direction[1])
                        for direction in four_direction
                        if self.env.realm.map.is_valid_pos(tile[0] + direction[0], tile[1] + direction[1])
                        and not self.env.realm.map.tiles[tile[0] + direction[0], tile[1] + direction[1]].impassible
                    ]
                if target_pos_list:
                    one_resource_dis = []
                    for target_pos in target_pos_list:
                        direction, distance = aStar(self.env.realm.map, start_pos, target_pos, bounds=bounds)
                        one_resource_dis.append((direction, distance))
                    # print(resource_name)
                    # print(distances)
                    one_resource_dis.sort(key=lambda x: x[1])
                    min_direction = one_resource_dis[0][0]
                    min_distance = one_resource_dis[0][1]
                    resource_dis.append((min_direction, min_distance))
        if resource_dis:
            resource_dis.sort(key=lambda x: x[1])
            direction = resource_dis[0][0]
            min_distance = resource_dis[0][1]
        else:
            direction = (0, 0)
        # assert min_distance != float("inf")
        return self.direction_to_index[direction]

    def move_to_chase_target(self, obs, entity_id):

        tiles = obs.tiles
        min_map_x = np.min(tiles[:, 0])
        min_map_y = np.min(tiles[:, 1])
        max_map_x = np.max(tiles[:, 0])
        max_map_y = np.max(tiles[:, 1])
        bounds = (min_map_x, max_map_x, min_map_y, max_map_y)

        start_pos = (obs.agent.row, obs.agent.col)
        target_pos = (
            obs.entities.values[entity_id][2],
            obs.entities.values[entity_id][3],
        )

        # 使用A*算法计算最短路径
        direction, _ = aStar(self.env.realm.map, start_pos, target_pos, bounds=bounds)
        return self.direction_to_index[direction]

    def move(self, obs, ml_action):
        if not ml_action:
            return self.direction_to_index[(0, 0)]
        if "Stay" in ml_action:
            return self.direction_to_index[(0, 0)]
        if "Move to" in ml_action:
            resource_name = self._get_resource_name_from_response(ml_action)
            if resource_name:
                direction_index = self.move_to_nearest_resource(obs, resource_name)
                if direction_index is None:
                    raise ValueError(f"Invalid move action: {ml_action}")
                return direction_index
            area_target = self._get_area_target_from_response(ml_action)
            if area_target:
                direction_index = self.move_to_area(obs, area_target)
                return direction_index
        elif "Chase" in ml_action or "Evade" in ml_action:
            if obs.entities:
                entity_id_to_index = {entity[0]: i for i, entity in enumerate(obs.entities.values)}
            entity_id = self._get_chase_entity_id_from_response(ml_action)
            if entity_id:
                direction_index = self.move_to_chase_target(obs, entity_id_to_index[entity_id])
                if direction_index is None:
                    raise ValueError(f"Invalid move action: {ml_action}")
                return direction_index
            entity_id = self._get_evade_entity_id_from_response(ml_action)
            if entity_id:
                direction_index = self.move_to_evade_target(obs, entity_id_to_index[entity_id])
                if direction_index is None:
                    raise ValueError(f"Invalid move action: {ml_action}")
                return direction_index
        else:
            raise ValueError(f"Invalid move action: {ml_action}")
        return self.direction_to_index[(0, 0)]

    def attack(self, obs, ml_action):
        if not ml_action:
            return 100, 0
        if "Attack nothing" in ml_action:
            return 100, 0
        entity_id, style = self._get_attack_entity_id_and_style_from_response(ml_action, obs)
        if entity_id is None or style is None:
            raise ValueError(f"Invalid attack action: {ml_action}")
        return entity_id, style

    def use(self, obs, ml_action):
        if not ml_action:
            return 12
        if "Use nothing" in ml_action:
            return 12
        item_id = self._get_use_item_id_from_response(ml_action, obs)
        if item_id is None:
            raise ValueError(f"Invalid use action: {ml_action}")
        return item_id

    def destroy(self, obs, ml_action):
        if not ml_action:
            return 12
        if "Destroy nothing" in ml_action:
            return 12
        item_id = self._get_destroy_item_id_from_response(ml_action, obs)
        if item_id is None:
            raise ValueError(f"Invalid destroy action: {ml_action}")
        return item_id

    def give(self, obs, ml_action):
        if "Give nothing to anyone" in ml_action:
            return 12, 100
        if not ml_action:
            raise ValueError
        item_id, entity_id = self._get_give_item_id_from_response(ml_action, obs)
        if item_id is None or entity_id is None:
            raise ValueError(f"Invalid give action: {ml_action}")
        return item_id, entity_id

    # Move action
    def _get_resource_name_from_response(self, ml_action):
        resource_pattern = r"Move to the nearest (Void|Water|Grass|Scrub|Foliage|Stone|Slag|Ore|Stump|Tree|Fragment|Crystal|Weeds|Herb|Ocean|Fish) tile"
        match = re.search(resource_pattern, ml_action)
        if match:
            resource_type = match.group(1)
            return resource_type
        else:
            return None

    def _get_chase_entity_id_from_response(self, ml_action):
        entity_pattern = r"Chase (Player|NPC) (-?\d+)"
        match = re.search(entity_pattern, ml_action)
        if match:
            entity_type = match.group(1)
            entity_id = int(match.group(2)) if entity_type == "Player" else -int(match.group(2))
            return entity_id
        return None

    def _get_evade_entity_id_from_response(self, ml_action):
        entity_pattern = r"Evade (Player|NPC) (-?\d+)"
        match = re.search(entity_pattern, ml_action)
        if match:
            entity_type = match.group(1)
            entity_id = int(match.group(2)) if entity_type == "Player" else -int(match.group(2))
            return entity_id
        return None

    def _get_area_target_from_response(self, ml_action):
        area_pattern = r"Move to the (center|north|south|west|east|northeast|southeast|southwest|northwest) area"
        match = re.search(area_pattern, ml_action)
        if match:
            area_target = match.group(1)
            return area_target
        return None

    def _get_attack_entity_id_and_style_from_response(self, ml_action, obs):
        entity_id_to_index = {entity[0]: i for i, entity in enumerate(obs.entities.values)}
        attack_pattern = r"Attack (Player|NPC) (-?\d+) with (\w+)"
        match = re.search(attack_pattern, ml_action)
        if match:
            entity_type = match.group(1)
            entity_id = int(match.group(2)) if entity_type == "Player" else -int(match.group(2))
            style = match.group(3)
            return entity_id_to_index[entity_id], self.attack_style_to_index[style]
        return None, None

    def _get_use_item_id_from_response(self, ml_action, obs):
        item_id_to_index = {item[0]: i for i, item in enumerate(obs.inventory.values)}
        # print(ml_action)
        # print(item_id_to_index)
        # print(vars(obs.agent)["id"])
        use_pattern = r"(?:Equip|Unequip|Use) level \d+ \w+ with id (\d+)"
        match = re.search(use_pattern, ml_action)
        if match:
            item_id = int(match.group(1))  # 获取捕获的id
            return item_id_to_index[item_id]
        return None

    def _get_destroy_item_id_from_response(self, ml_action, obs):
        item_id_to_index = {item[0]: i for i, item in enumerate(obs.inventory.values)}
        destroy_pattern = r"Destroy level \d+ \w+ with id (\d+)"
        # print(ml_action)
        # print(item_id_to_index)
        # print(vars(obs.agent)["id"])

        match = re.search(destroy_pattern, ml_action)
        if match:
            item_id = int(match.group(1))  # 获取捕获的id
            return item_id_to_index[item_id]
        return None

    def _get_give_item_id_from_response(self, ml_action, obs):
        item_id_to_index = {item[0]: i for i, item in enumerate(obs.inventory.values)}
        entity_id_to_index = {entity[0]: i for i, entity in enumerate(obs.entities.values)}
        # print(item_id_to_index)
        # print(entity_id_to_index)
        # print(ml_action)
        print(vars(obs.agent)["id"])
        give_pattern = r"Give level \d+ \w+ with id (\d+) to Player (\d+)"
        match = re.search(give_pattern, ml_action)
        if match:
            item_id = int(match.group(1))  # 获取物品id
            entity_id = int(match.group(2))  # 获取玩家id
            return item_id_to_index[item_id], entity_id_to_index[entity_id]
        return None, None
