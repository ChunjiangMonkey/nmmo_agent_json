import argparse
import concurrent.futures
import os
import sys

current_dir = os.path.abspath(__file__)
sys.path.append(current_dir)
sys.path.append(f"{current_dir}/task")
# parent_dir = os.path.dirname(current_dir)
# sys.path.append(parent_dir)
# grandparent_dir = os.path.dirname(parent_dir)
# sys.path.append(grandparent_dir)


import pytz
import time
import numpy as np
from tqdm import tqdm
import yaml
import numpy as np

# from random_agent import LLMPlayer as RandomPlayer

import nmmo
from nmmo.task.task_spec import make_task_from_spec

from nmmo.render.replay_helper import FileReplayHelper
import nmmo.core.config as nc
from nmmo.lib import utils
from nmmo.systems import skill as nmmo_skill

from agent.agent import LLMPlayer
from bridge.state_manager import StateManager
from bridge.action_manager import ActionManager
from strategy_manager import StrategyManager
from bridge.event_manager import EventManager
from task.create_task import (
    create_AttainSkill_task,
    create_DefeatEntity_task,
    create_Survive_task,
    create_EquipItem_task,
)

from utils.multi_task_support import apply_multi_task_support
from utils.event_record_support import apply_event_record_support

import openai
import os
import textwrap
import json
from datetime import datetime
from task.create_task import task_map, readable_task_name


def provide_item(realm, ent_id: int, item, level: int, quantity: int):
    for _ in range(quantity):
        realm.players[ent_id].inventory.receive(item(realm, level=level))


def save_progress(data, save_path):
    with open(save_path, "w") as f:
        f.write(json.dumps(data, indent=4))


def load_config(config_path):
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config


def save_config_file(config, save_dir, filename="config.yaml"):
    os.makedirs(save_dir, exist_ok=True)
    config_path = os.path.join(save_dir, filename)
    with open(config_path, "w") as file:
        yaml.safe_dump(config, file, sort_keys=False)
    return config_path


def main(args):
    data_time = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d_%H-%M-%S")  # 实验开始时间
    # 应用补丁
    apply_multi_task_support()
    apply_event_record_support()
    # print(args)
    run_survive = args.run_survive
    run_task = not run_survive
    # exp_name = f"{args.exp_name}_{data_time}"
    exp_name = args.exp_name
    goal = args.goal
    debug = args.debug
    pid = args.pid
    config_name = args.config_name
    config = load_config(f"configs/{config_name}.yaml")

    episode_num = config["experiment"]["episode_num"]
    map_size = config["env"]["map_size"]
    player_num = config["env"]["player_num"]
    # player_role包括任务型(task)、生存型(individual)、竞争型(competitive)、合作型(cooperative)

    individual_num = config["env"]["individual_num"]
    competitive_num = config["env"]["competitive_num"]
    cooperative_num = config["env"]["cooperative_num"]

    npc_num = config["env"]["npc_num"]
    horizon = config["env"]["horizon"]

    model_name = config["agent"]["model_name"]
    enable_llm_thinking = config["agent"]["enable_llm_thinking"]
    replay_save_interval = config["experiment"]["replay_save_interval"]
    if "fog_onset" in config["env"]:
        fog_onset = config["env"]["fog_onset"]
        fog_speed = float(config["env"]["fog_speed"])
        fog_final_size = config["env"]["fog_final_size"]

    disable_stone = config["env"]["disable_stone"]

    use_interaction_memory = config["agent"]["use_interaction_memory"]
    allow_give_action = config["agent"]["allow_give_action"]
    use_strategy = config["agent"]["use_strategy"]  # 是否使用strategy
    use_information_reduction = config["agent"]["use_information_reduction"]  # 是否使用信息缩减
    max_verify_time = config["agent"]["max_verify_time"]  # 是否使用验证
    max_execute_step = config["agent"]["max_execute_step"]  # 最大执行步数
    share_strategy = config["agent"]["share_strategy"]  # 是否共享策略池
    if run_task:
        file_save_path = f"llm_io/{exp_name}/{goal}/{pid}"
    else:
        file_save_path = f"llm_io/{exp_name}/{pid}"
    # 保存本次运行使用的配置
    save_config_file(config, file_save_path)
    # 根据任务类型选择对应的任务
    # print(task_map)
    goals = []
    player_types = []
    if run_survive:
        goals.append(create_Survive_task(horizon)[2])  # 添加生存任务
        for skill in nmmo_skill.COMBAT_SKILL + nmmo_skill.HARVEST_SKILL:
            goals.append(create_AttainSkill_task(skill, 10, 1)[2])
        goals.append(create_DefeatEntity_task("npc", 1, 50)[2])
        goal_description = None
        for i in range(individual_num):
            player_types.append("individual")
        for i in range(competitive_num):
            player_types.append("competitive")
        for i in range(cooperative_num):
            player_types.append("cooperative")
        np.random.shuffle(player_types)

    else:
        _, goal_description, goal_fun = task_map[goal]
        goals.append(goal_fun)
        for i in range(player_num):
            player_types.append("task")
    # for goal in goals:
    #     print(readable_task_name[goal.name])

    # 创建配置
    if map_size < 40:
        Implemented_Map_Config = nc.Small
    elif map_size < 200:
        Implemented_Map_Config = nc.Medium
    else:
        Implemented_Map_Config = nc.Large

    class CustomConfig(
        Implemented_Map_Config,
        nc.Terrain,
        nc.Resource,
        nc.Combat,
        nc.NPC,
        nc.Progression,
        nc.Item,
        nc.Equipment,
        nc.Profession,
    ):

        PATH_MAPS = None
        MAP_FORCE_GENERATION = True
        MAP_GENERATE_PREVIEWS = True
        MAP_PREVIEW_DOWNSCALE = 4
        ALLOW_MULTI_TASKS_PER_AGENT = True
        MAP_CENTER = map_size
        MAP_SIZE = map_size + 16
        HORIZON = horizon
        PLAYER_N = player_num
        NPC_N = npc_num
        DEATH_FOG_ONSET = fog_onset
        DEATH_FOG_SPEED = fog_speed
        DEATH_FOG_FINAL_SIZE = fog_final_size
        TERRAIN_DISABLE_STONE = disable_stone

    map_config = CustomConfig()
    strategy_managers = []
    if run_survive and use_strategy:
        if share_strategy:
            strategy_manager = StrategyManager(model_name, debug=debug)
            strategy_managers = [strategy_manager] * player_num
        else:
            strategy_managers = [StrategyManager(model_name, debug=debug) for _ in range(player_num)]
    # print(len(strategy_managers))
    with tqdm(total=episode_num * horizon, desc="Running steps") as pbar:
        for episode in range(episode_num):
            # 创建保存路径
            episode_save_path = f"{file_save_path}/{episode}/"
            prompt_path = f"{episode_save_path}/prompt"
            replay_path = f"{episode_save_path}/replays"
            task_path = f"{episode_save_path}/tasks"
            map_path = f"{episode_save_path}/maps"

            os.makedirs(prompt_path, exist_ok=True)
            os.makedirs(replay_path, exist_ok=True)
            os.makedirs(task_path, exist_ok=True)
            os.makedirs(map_path, exist_ok=True)

            map_config.PATH_MAPS = map_path
            # strategy_manager.reset(strategy_path, data_time)

            env = nmmo.Env(config=map_config)

            event_manager = EventManager(player_num)

            if run_survive and use_strategy:
                if share_strategy:
                    strategy_path = f"{episode_save_path}/strategies"
                    os.makedirs(strategy_path, exist_ok=True)
                    strategy_managers[0].reset(strategy_path)
                else:
                    for i in range(player_num):
                        strategy_path = f"{episode_save_path}/{i+1}/strategies"
                        os.makedirs(strategy_path, exist_ok=True)
                        strategy_managers[i].reset(strategy_path)

            # 定义任务
            env_tasks = []
            for goal in goals:
                for task in make_task_from_spec(env.possible_agents, [goal] * len(env.possible_agents)):
                    env_tasks.append(task)

            env.tasks = env_tasks
            env.reset()
            env._map_task_to_agent()

            # 设置replay helper
            replay_helper = FileReplayHelper()
            players = []

            task_progress = {a: {} for a in env.agents}
            game_status_all = {}

            for i in range(player_num):
                save_path = f"{prompt_path}/{i+1}"
                os.makedirs(save_path, exist_ok=True)
                player = LLMPlayer(
                    model_name,
                    map_config,
                    env,
                    horizon,
                    save_path,
                    player_role=player_types[i],
                    goal=goal_description,
                    run_task=run_task,
                    use_information_reduction=use_information_reduction,
                    allow_give_action=allow_give_action,
                    use_interaction_memory=use_interaction_memory,
                    enable_llm_thinking=enable_llm_thinking,
                    max_execute_step=max_execute_step,
                    max_verify_time=max_verify_time,
                    debug=debug,
                )
                players.append(player)
                env.realm.players[i + 1].name = f"player_{i+1}_{player_types[i]}"

            alive_players = list(range(1, player_num + 1))

            env.realm.record_replay(replay_helper)
            replay_helper.reset()

            # 用于记录任务完成状态

            # for a in env.agents:
            #     provide_item(env.realm, a, Hat, level=1, quantity=1)
            #     provide_item(env.realm, a, Bottom, level=1, quantity=1)
            #     provide_item(env.realm, a, Top, level=1, quantity=1)

            start_time = time.time()
            for step in range(1, horizon + 1):  # 使用命令行参数中的步数
                # a is the id of player
                if True:
                    # try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        action_seq = list(
                            executor.map(
                                lambda player_id: players[player_id - 1].act(env.obs[player_id], step),
                                alive_players,
                            )
                        )
                    actions = {a: action_seq[i] for i, a in enumerate(alive_players)}
                    obs, rewards, terminated, truncated, infos = env.step(actions)
                    current_events = env.realm.event_log.get_data(tick=env.realm.tick)
                    record = event_manager.update_record(current_events)
                    for player_id in alive_players:
                        players[player_id - 1].update_memory(step, record[player_id])

                # except Exception as e:
                #     print(e)
                #     game_status["status"] = "bug"
                #     game_status["bug_reason"] = str(e)
                #     save_progress(
                #         task_progress,
                #         f"{task_path}/task_progress_{model_name}.json",
                #     )
                #     save_progress(
                #         game_status, f"{task_path}/game_status_{model_name}.json"
                #     )
                #     break
                end_time = time.time()
                if step % replay_save_interval == 0:
                    replay_helper.save(f"{replay_path}/{step}_{model_name}", compress=True)

                # 更新任务完成状态
                task_mean = {}
                game_status = {}

                for agent_id in env.agents:
                    # task_progress[agent_id]["current_tick"] = step
                    for task in env.agent_task_map[agent_id]:
                        # 转换成可读的任务名称
                        if task.spec_name in readable_task_name.keys():
                            task_name = readable_task_name[task.spec_name]
                        else:
                            task_name = task.spec_name
                        if task_name not in task_progress[agent_id].keys():
                            task_progress[agent_id][task_name] = {}
                        task_progress[agent_id][task_name]["progress"] = task._progress
                        if task.completed:
                            task_progress[agent_id][task_name]["completed"] = True
                            task_progress[agent_id][task_name]["completed_tick"] = step
                        else:
                            task_progress[agent_id][task_name]["completed"] = False
                            task_progress[agent_id][task_name]["completed_tick"] = -1
                        if task_name in task_mean.keys():
                            task_mean[task_name].append(task._progress)
                        else:
                            task_mean[task_name] = [task._progress]

                all_task_completed = all(
                    task_progress[agent_id][task_name]["completed"]
                    for agent_id in task_progress.keys()
                    for task_name in task_progress[agent_id].keys()
                )

                # 更新游戏状态
                game_status["program_run_time"] = f"{end_time - start_time:.4f}s"
                for task_name in task_mean.keys():
                    game_status[task_name] = np.mean(task_mean[task_name])
                game_status["current_time"] = step
                all_agent_dead = all(terminated.values())
                game_end = all(truncated.values())
                # print(json.dumps(task_progress, indent=4))

                alive_players = []
                for agent_id in terminated.keys():
                    if terminated[agent_id]:
                        players[agent_id - 1].update_strategy(env.obs[agent_id], step)
                    else:
                        alive_players.append(agent_id)
                game_status["alive_player_num"] = len(alive_players)

                game_status["prompt_tokens"] = np.mean([player.token_usage["prompt_tokens"] for player in players])
                game_status["completion_tokens"] = np.mean([player.token_usage["completion_tokens"] for player in players])
                game_status["total_tokens"] = np.mean([player.token_usage["total_tokens"] for player in players])

                if all_agent_dead or game_end or (run_task and all_task_completed):
                    if all_agent_dead:
                        game_status["status"] = "all player dead"
                    elif run_task and all_task_completed:
                        game_status["status"] = "all task completed"
                    elif game_end:
                        game_status["status"] = "game end"
                    else:
                        game_status["status"] = "running"
                    save_progress(
                        task_progress,
                        f"{task_path}/task_progress_{model_name}.json",
                    )
                    game_status_all[step] = game_status
                    save_progress(game_status_all, f"{task_path}/game_status_{model_name}.json")
                    break
                else:
                    game_status["status"] = "running"
                    save_progress(
                        task_progress,
                        f"{task_path}/task_progress_{model_name}.json",
                    )
                    game_status_all[step] = game_status
                    save_progress(game_status_all, f"{task_path}/game_status_{model_name}.json")
                pbar.update(1)
            replay_helper.save(f"{replay_path}/finish_{model_name}", compress=True)
    pbar.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--exp_name",
        type=str,
    )

    parser.add_argument(
        "--run_survive",
        action="store_true",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
    )

    parser.add_argument(
        "--config_name",
        default="single_task",
        type=str,
    )

    parser.add_argument(
        "--pid",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--goal",
        type=str,
        default="defeat_npc_level_1_20",
        choices=[
            "survive_1024",
            "player_kill_20",
            "go_farthest_20",
            "earn_gold_20",
            "buy_item_20",
            "defeat_npc_level_1_20",
            "defeat_npc_level_3_20",
            "occupy_central_tile",
            "attain_Melee_level_10",
            "attain_Range_level_10",
            "attain_Mage_level_10",
            "attain_Fishing_level_10",
            "attain_Herbalism_level_10",
            "attain_Prospecting_level_10",
            "attain_Carving_level_10",
            "attain_Alchemy_level_10",
            "harvest_Whetstone_level_1_20",
            "harvest_Whetstone_level_3_20",
            "harvest_Arrow_level_1_20",
            "harvest_Arrow_level_3_20",
            "harvest_Runes_level_1_20",
            "harvest_Runes_level_3_20",
            "consume_Ration_level_1_20",
            "consume_Ration_level_3_20",
            "consume_Potion_level_1_20",
            "consume_Potion_level_3_20",
            "equip_Hat_level_1",
            "equip_Hat_level_3",
            "equip_Top_level_1",
            "equip_Top_level_3",
            "equip_Bottom_level_1",
            "equip_Bottom_level_3",
            "equip_Spear_level_1",
            "equip_Spear_level_3",
            "equip_Bow_level_1",
            "equip_Bow_level_3",
            "equip_Wand_level_1",
            "equip_Wand_level_3",
            "equip_Rod_level_1",
            "equip_Rod_level_3",
            "equip_Gloves_level_1",
            "equip_Gloves_level_3",
            "equip_Pickaxe_level_1",
            "equip_Pickaxe_level_3",
            "equip_Axe_level_1",
            "equip_Axe_level_3",
            "equip_Chisel_level_1",
            "equip_Chisel_level_3",
            "equip_Whetstone_level_1",
            "equip_Whetstone_level_3",
            "equip_Arrow_level_1",
            "equip_Arrow_level_3",
            "equip_Runes_level_1",
            "equip_Runes_level_3",
            "fully_armed_Melee_level_1",
            "fully_armed_Melee_level_3",
            "fully_armed_Range_level_1",
            "fully_armed_Range_level_3",
            "fully_armed_Mage_level_1",
            "fully_armed_Mage_level_3",
            "earn_gold_100",
            "hoard_gold_100",
            "make_profit_100",
        ],
    )

    args = parser.parse_args()
    main(args)
