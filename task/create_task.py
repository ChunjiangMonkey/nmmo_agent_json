import copy
from collections import defaultdict
import re
import argparse  # 添加argparse导入

import numpy as np
import tqdm
import nmmo
from nmmo.core.tile import TileState
from nmmo.entity.entity import Entity
from nmmo.systems.item import Item
from nmmo.task.task_spec import TaskSpec, make_task_from_spec
from nmmo.task.group import Group
from nmmo.task.game_state import GameState
from nmmo.systems import skill as nmmo_skill
from nmmo.systems import item as nmmo_item
from nmmo.lib import utils
from nmmo.task.base_predicates import (
    AttainSkill,
    ConsumeItem,
    CountEvent,
    DefeatEntity,
    EarnGold,
    EquipItem,
    FullyArmed,
    HarvestItem,
    HoardGold,
    MakeProfit,
    OccupyTile,
    TickGE,
)
from nmmo.systems.skill import (
    Melee,
    Range,
    Mage,
    Fishing,
    Herbalism,
    Prospecting,
    Carving,
    Alchemy,
)
from nmmo.systems.item import (
    Hat,
    Top,
    Bottom,
    Spear,
    Bow,
    Wand,
    Rod,
    Gloves,
    Pickaxe,
    Axe,
    Chisel,
    Whetstone,
    Arrow,
    Runes,
    Ration,
    Potion,
)

task_map = {}
SURVIVE_TIME = 1024
EVENT_GOAL = 20
ITEM_LEVEL_GOAL = [1, 3]
SKILL_LEVEL_GOAL = 10
GOLD_GOAL = 100

goal_text = "In this game, my goal is to "


# ========== 生存任务 ==========
def create_Survive_task(num_tick):
    task_description = f"{goal_text}Survive for as long as possible. "
    task = TaskSpec(
        eval_fn=TickGE,
        eval_fn_kwargs={"num_tick": num_tick},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 计数任务 ==========
def create_CountEvent_task(event, event_goal):
    event = event.upper()
    if event == "PLAYER_KILL":
        task_description = f"{goal_text}defeat Players or NPCs as many as possible. "
    elif event == "GO_FARTHEST":
        task_description = f"{goal_text}explore the map as much as possible. "
    elif event == "EARN_GOLD":
        task_description = f"{goal_text}earn {event_goal} golds. "
        event_goal = 64
    elif event == "BUY_ITEM":
        task_description = f"{goal_text}buy items as many as possible. "
    task = TaskSpec(
        eval_fn=CountEvent,
        eval_fn_kwargs={"event": event, "N": event_goal},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 击败实体任务 ==========
def create_DefeatEntity_task(agent_type, level, num_agent):
    if agent_type == "npc":
        task_description = f"{goal_text}defeat as many level {level} or higher NPC as possible. "
    elif agent_type == "player":
        task_description = f"{goal_text}defeat as many level {level} or higher Player as possible. "
    task = TaskSpec(
        eval_fn=DefeatEntity,
        eval_fn_kwargs={
            "agent_type": agent_type,
            "level": level,
            "num_agent": num_agent,
        },
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 占据格子任务 ==========


def create_OccupyTile_task(row, col):
    task_description = f"{goal_text}occupy the central tile. "
    task = TaskSpec(
        eval_fn=OccupyTile,
        eval_fn_kwargs={"row": row, "col": col},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 升级技能任务 ==========
def create_AttainSkill_task(skill, level, num_agent):
    task_description = f"{goal_text}reach {skill.__name__} skill level {level} or higher. "
    task = TaskSpec(
        eval_fn=AttainSkill,
        eval_fn_kwargs={"skill": skill, "level": level, "num_agent": num_agent},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 采集任务 ==========


def create_HarvestItem_task(item, level, quantity):
    task_description = (
        f"{goal_text}harvest as much level {level} or higher {item.__name__} as possible. "
    )
    task = TaskSpec(
        eval_fn=HarvestItem,
        eval_fn_kwargs={"item": item, "level": level, "quantity": quantity},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 消耗物品任务 ==========


def create_ConsumeItem_task(item, level, quantity):
    task_description = (
        f"{goal_text}consume as much level {level} or higher {item.__name__} as possible. "
    )
    task = TaskSpec(
        eval_fn=ConsumeItem,
        eval_fn_kwargs={"item": item, "level": level, "quantity": quantity},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 装备物品任务 ==========


def create_EquipItem_task(item, level, num_agent):
    task_description = f"{goal_text}equip {item.__name__} of level {level} or higher. "
    task = TaskSpec(
        eval_fn=EquipItem,
        eval_fn_kwargs={"item": item, "level": level, "num_agent": num_agent},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 全副武装任务 ==========
def create_FullyArmed_task(combat_style, level, num_agent):
    task_description = f"{goal_text}equip Hat of level {level} or higher, Top of level {level} or higher, Bottom of level {level} or higher, "
    if combat_style == Melee:
        task_description += (
            f"Spear of level {level} or higher, and Whetstone of level {level} or higher. "
        )
    elif combat_style == Range:
        task_description += (
            f"Bow of level {level} or higher, and Arrow of level {level} or higher. "
        )
    elif combat_style == Mage:
        task_description += (
            f"a Wand of level {level} or higher, and Runes of level {level} or higher. "
        )
    else:
        raise ValueError(f"Invalid combat style: {combat_style}")
    task = TaskSpec(
        eval_fn=FullyArmed,
        eval_fn_kwargs={
            "combat_style": combat_style,
            "level": level,
            "num_agent": num_agent,
        },
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 赚取金钱任务  ==========


def create_EarnGold_task(amount):
    task_description = f"{goal_text}earn at least {amount} gold by trading. "
    task = TaskSpec(
        eval_fn=EarnGold,
        eval_fn_kwargs={"amount": amount},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 持有金钱任务 ==========
def create_HoardGold_task(amount):
    task_description = f"{goal_text}own at least {amount} gold. "
    task = TaskSpec(
        eval_fn=HoardGold,
        eval_fn_kwargs={"amount": amount},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 赚取利润任务 ==========


def create_MakeProfit_task(amount):
    task_description = f"{goal_text}own at least {amount} gold. "
    task = TaskSpec(
        eval_fn=MakeProfit,
        eval_fn_kwargs={"amount": amount},
    )
    task_name = task.name
    return task_name, task_description, task


# ========== 创建任务 ==========
# 生存任务
task_name, task_description, task = create_Survive_task(num_tick=SURVIVE_TIME)
task_map[f"survive_{SURVIVE_TIME}"] = (task_name, task_description, task)

# 计数任务
for event in ["player_kill", "go_farthest", "earn_gold", "buy_item"]:
    task_name, task_description, task = create_CountEvent_task(event, event_goal=EVENT_GOAL)
    task_map[f"{event}_{EVENT_GOAL}"] = (task_name, task_description, task)

# 击败实体任务
for agent_type in ["npc"]:
    for level in ITEM_LEVEL_GOAL:
        name = f"defeat_{agent_type}_level_{level}_{EVENT_GOAL}"
        task_name, task_description, task = create_DefeatEntity_task(agent_type, level, EVENT_GOAL)
        task_map[name] = (task_name, task_description, task)

# 占据格子任务
task_name, task_description, task = create_OccupyTile_task(row=80, col=80)
task_map["occupy_central_tile"] = (task_name, task_description, task)

# 升级技能任务
for skill in nmmo_skill.COMBAT_SKILL + nmmo_skill.HARVEST_SKILL:
    task_name, task_description, task = create_AttainSkill_task(
        skill, level=SKILL_LEVEL_GOAL, num_agent=1
    )
    task_map[f"attain_{skill.__name__}_level_{SKILL_LEVEL_GOAL}"] = (
        task_name,
        task_description,
        task,
    )

# 采集任务
for item in nmmo_item.AMMUNITION:
    for level in [1, 3]:
        task_name, task_description, task = create_HarvestItem_task(
            item, level, quantity=EVENT_GOAL
        )
        task_map[f"harvest_{item.__name__}_level_{level}_{EVENT_GOAL}"] = (
            task_name,
            task_description,
            task,
        )

# 消耗物品任务
for item in nmmo_item.CONSUMABLE:
    for level in ITEM_LEVEL_GOAL:
        task_name, task_description, task = create_ConsumeItem_task(
            item, level, quantity=EVENT_GOAL
        )
        task_map[f"consume_{item.__name__}_level_{level}_{EVENT_GOAL}"] = (
            task_name,
            task_description,
            task,
        )

# 装备物品任务
for item in nmmo_item.ARMOR + nmmo_item.WEAPON + nmmo_item.TOOL + nmmo_item.AMMUNITION:
    for level in ITEM_LEVEL_GOAL:
        task_name, task_description, task = create_EquipItem_task(item, level, num_agent=1)
        task_map[f"equip_{item.__name__}_level_{level}"] = (task_name, task_description, task)

# 全副武装任务
for combat_style in nmmo_skill.COMBAT_SKILL:
    for level in ITEM_LEVEL_GOAL:
        task_name, task_description, task = create_FullyArmed_task(combat_style, level, num_agent=1)
        task_map[f"fully_armed_{combat_style.__name__}_level_{level}"] = (
            task_name,
            task_description,
            task,
        )

# 赚取金钱任务
task_name, task_description, task = create_EarnGold_task(amount=GOLD_GOAL)
task_map[f"earn_gold_{GOLD_GOAL}"] = (task_name, task_description, task)

# 持有金钱任务
task_name, task_description, task = create_HoardGold_task(amount=GOLD_GOAL)
task_map[f"hoard_gold_{GOLD_GOAL}"] = (task_name, task_description, task)

# 赚取利润任务
task_name, task_description, task = create_MakeProfit_task(amount=GOLD_GOAL)
task_map[f"make_profit_{GOLD_GOAL}"] = (task_name, task_description, task)

readable_task_name = {v[0]: k for k, v in task_map.items()}

if __name__ == "__main__":

    # 打印所有任务名称
    for k, v in task_map.items():
        print(f'"{k}",')
        # print(v[0])
        # print("==================")
