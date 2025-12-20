import copy
from collections import defaultdict
import random
import re
import string
import sys
import os

current_dir = os.path.abspath(__file__)
sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

import numpy as np
import tqdm
import tiktoken

from llm_client import OpenAIClient, LlamaClient
import nmmo
from nmmo.core.tile import TileState
from nmmo.entity.entity import Entity
from nmmo.systems.item import Item

from nmmo.render.replay_helper import FileReplayHelper
import nmmo.core.config as nc
from nmmo.lib import utils
from nmmo.lib import material
import openai
import os
import json
from datetime import datetime

from bridge.state_manager import StateManager
from bridge.action_manager import ActionManager

# from strategy_manager import StrategyManager

# from agent.modules.planning_module import PlanningModule
from agent.modules.game_rule_module import GameRuleModule
from agent.modules.memory_module import MemoryModule
from agent.modules.action_module import ActionModule
from agent.modules.planning_module import PlanningModule
from agent.modules.perception_module import PerceptionModule
from agent.modules.verify_module import VerifyModule
from api_key import openai_base_url, openai_api_key, llama_base_url, llama_api_key


def save_ml_action(file_path, tick, ml_action):
    with open(file_path, "a") as f:
        f.write(
            f"{tick}, {ml_action['Move']}, {ml_action['Attack']}, {ml_action['Use']}, {ml_action['Destroy']}, {ml_action['Give']}\n"
        )


class LLMPlayer:
    def __init__(
        self,
        model_name,
        config,
        env,
        horizon,
        file_save_path,
        player_role="task",
        goal=None,
        use_information_reduction=False,  # 是否压缩信息
        strategy_manager=None,  # 传入的strategy
        use_strategy=False,  # 是否使用策略
        run_task=True,
        allow_give_action=False,
        use_interaction_memory=False,
        max_verify_time=5,
        max_execute_step=10,  # 最大执行步数
        add_action_history=False,
        enable_llm_thinking=False,
        debug=False,
    ):
        ##### 参数 #####
        self.player_role = player_role
        self.use_information_reduction = use_information_reduction
        self.allow_give_action = allow_give_action
        self.run_task = run_task
        self.use_interaction_memory = use_interaction_memory
        # self.use_strategy = use_strategy
        # self.use_verify = use_verify
        self.max_verify_time = max_verify_time  # 验证次数
        self.debug = debug
        self.model_name = model_name
        self.config = config
        if "gpt" in model_name.lower():
            self.llm_client = OpenAIClient(
                base_url=openai_base_url, api_key=openai_api_key, model=model_name, enable_thinking=enable_llm_thinking
            )
        elif "llama" in model_name.lower():
            self.llm_client = LlamaClient(
                base_url=llama_base_url, api_key=llama_api_key, model=model_name, enable_thinking=enable_llm_thinking
            )
        else:
            raise ValueError(f"Invalid model name: {model_name}")

        self.file_save_path = file_save_path
        self.file_name_simple = f"{self.file_save_path}/state_prompt_{self.model_name}.txt"  # 简单提示文件保存路径
        self.file_name_full = f"{self.file_save_path}/prompt_{self.model_name}.txt"  # 完整提示文件保存路径
        self.file_name_action = f"{self.file_save_path}/ml_action.csv"

        os.makedirs(self.file_save_path, exist_ok=True)

        ##### 属性 #####
        self.state_manager = StateManager(env)
        self.action_manager = ActionManager(env)
        # self.strategy_manager = strategy_manager
        self.game_rule_module = GameRuleModule(config)
        self.memory_module = MemoryModule(max_history=20)
        self.perceive_module = PerceptionModule(config, self.llm_client, self.file_name_full, debug=debug)
        self.plan_module = PlanningModule(config, self.llm_client, self.file_name_full, debug=debug)
        self.action_module = ActionModule(config, self.llm_client, self.file_name_full, debug=debug)
        self.verify_module = VerifyModule(config, self.llm_client, self.file_name_full, debug=debug)
        self.state_description = None
        self.action_space = None

        self.goal = goal
        self.horizon = horizon

        self.current_execute_step = 0
        self.max_execute_step = max_execute_step  # 最大执行步数

        self.should_get_ml_action = True
        self.should_get_use_action = False
        self.should_get_destroy_action = False
        self.should_get_give_action = False
        self.state_when_act = None

        self.ml_action = None
        self.current_use_action = None
        self.current_destroy_action = None
        self.current_give_action = None

        self.add_action_history = add_action_history
        if self.add_action_history:
            self.action_history = []
        self.executed_ml_action_number = 0

    def update_memory(self, tick, event):
        self.memory_module.update(tick, event, self.ml_action)

    def update_strategy(self, obs, tick):
        pass
        # state_description = self.state_manager.get_state_description(obs, tick, self.horizon)
        # game_mechanics = acclimate(
        #     self.llm_client,
        #     tick,
        #     self.config,
        #     self.goal,
        #     state_description,
        #     self.file_name_full,
        #     use_information_reduction=self.use_information_reduction,
        #     debug=self.debug,
        # )

        # update(
        #     self.llm_client,
        #     self.strategy_manager,
        #     state_description,
        #     tick,
        #     game_mechanics,
        #     self.file_name_full,
        #     debug=self.debug,
        # )

    def act(self, obs, tick):

        game_mechanics = self.game_rule_module.get_game_rule_overview() 
        # if self.use_information_reduction:
        #     game_mechanics = self.game_rule_module.get_detail_game_rule(task=self.goal)
        # else:
        #     game_mechanics = self.game_rule_module.get_detail_game_rule() 
        state_info = self.state_manager.get_state_info(obs)
        state_description = self.perceive_module.perceive(state_info, tick, self.horizon)

        # if self.executed_ml_action_number % 10 == 0:
        #     self.plan = self.plan_module.plan(self.goal, game_mechanics, state_description)
        self.plan = None

        # print("=== State Description ===" f"{state_description}")
        # print(action_space)
        if self.use_interaction_memory and tick > 1:
            recent_event = self.memory_module.get_recent_description(10)
            if recent_event:
                state_description = state_description + "\n\n# Interaction Memory\n" + recent_event

        if tick == 1:
            self.should_get_ml_action = True
        else:
            last_record = self.memory_module.get_last_tick_record(tick)
            self.should_get_ml_action = self.action_module.should_get_ml_action(
                tick, state_info, self.state_when_act, self.current_action, last_record
            )

        if self.current_execute_step >= self.max_execute_step:
            self.should_get_ml_action = True

        self.should_get_use_action = self.action_module.should_get_use_action(state_info)
        self.should_get_destroy_action = self.action_module.should_get_destroy_action(state_info)
        self.should_get_give_action = self.allow_give_action and self.action_module.should_get_give_action(state_info)

        # 获取ml action
        if self.should_get_ml_action:
            ml_action_space = self.action_module.generate_available_ml_action(state_info)
            candidate_action = None
            feed_back = None
            verify_time = 0
            while verify_time <= self.max_verify_time:
                if candidate_action:
                    evaluation, feed_back = self.verify_module.verify(
                        "ml_action",
                        self.player_role,
                        tick,
                        game_mechanics,
                        state_description,
                        ml_action_space,
                        goal=self.goal,
                        plan=self.plan,
                        action_history=self.action_history if self.add_action_history else None,
                        feedback=feed_back,
                        candidate_action=candidate_action,
                        verify_time=verify_time,
                    )
                    if evaluation == "yes":
                        break
                candidate_action = self.action_module.act(
                    "ml_action",
                    self.player_role,
                    tick,
                    game_mechanics,
                    state_description,
                    ml_action_space,
                    goal=self.goal,
                    plan=self.plan,
                    action_history=self.action_history if self.add_action_history else None,
                    feedback=feed_back,
                    candidate_action=candidate_action,
                )
                verify_time += 1
            # self.last_action = candidate_action
            self.ml_action = candidate_action
            if self.add_action_history:
                self.action_history.append(candidate_action)
                if len(self.action_history) > 10:
                    self.action_history = self.action_history[-10:]  # 写死10条历史记录
            self.current_execute_step = 0
            self.state_when_act = state_info
        else:
            self.current_execute_step += 1
        # print(f"ML Action at tick {tick}: {self.ml_action}")
        # 获取 use action
        if self.should_get_use_action:
            use_action_space = self.action_module.generate_available_item_use(state_info)
            candidate_action = None
            feed_back = None
            verify_time = 0
            while verify_time <= self.max_verify_time:
                if candidate_action:
                    evaluation, feed_back = self.verify_module.verify(
                        "use",
                        self.player_role,
                        tick,
                        game_mechanics,
                        state_description,
                        goal=self.goal,
                        plan=self.plan,
                        action_history=self.action_history if self.add_action_history else None,
                        candidate_action=candidate_action,
                        verify_time=verify_time,
                    )
                    if evaluation == "yes":
                        break
                candidate_action = self.action_module.act(
                    "use",
                    self.player_role,
                    tick,
                    game_mechanics,
                    state_description,
                    use_action_space,
                    goal=self.goal,
                    plan=self.plan,
                    action_history=self.action_history if self.add_action_history else None,
                    feedback=feed_back,
                    candidate_action=candidate_action,
                )
                verify_time += 1

            use_action = candidate_action
        else:
            use_action = None

        # 获取 destroy action
        if self.should_get_destroy_action:
            destroy_action_space = self.action_module.generate_available_destroy(state_info)
            candidate_action = None
            feed_back = None
            verify_time = 0
            while verify_time <= self.max_verify_time:
                if candidate_action:
                    evaluation, feed_back = self.verify_module.verify(
                        "destroy",
                        self.player_role,
                        tick,
                        game_mechanics,
                        state_description,
                        goal=self.goal,
                        plan=self.plan,
                        action_history=self.action_history if self.add_action_history else None,
                        candidate_action=candidate_action,
                        verify_time=verify_time,
                    )
                    if evaluation == "yes":
                        break
                candidate_action = self.action_module.act(
                    "destroy",
                    self.player_role,
                    tick,
                    game_mechanics,
                    state_description,
                    destroy_action_space,
                    goal=self.goal,
                    plan=self.plan,
                    action_history=self.action_history if self.add_action_history else None,
                    feedback=feed_back,
                    candidate_action=candidate_action,
                )
                verify_time += 1

            destroy_action = candidate_action
        else:
            destroy_action = None

        # 获取give action
        if self.should_get_give_action:
            give_action_space = self.action_module.generate_available_give(state_info)
            candidate_action = None
            feed_back = None
            verify_time = 0
            while verify_time <= self.max_verify_time:
                if candidate_action:
                    evaluation, feed_back = self.verify_module.verify(
                        "give",
                        self.player_role,
                        tick,
                        game_mechanics,
                        state_description,
                        goal=self.goal,
                        plan=self.plan,
                        action_history=self.action_history if self.add_action_history else None,
                        candidate_action=candidate_action,
                        verify_time=verify_time,
                    )
                    if evaluation == "yes":
                        break
                candidate_action = self.action_module.act(
                    "give",
                    self.player_role,
                    tick,
                    game_mechanics,
                    state_description,
                    give_action_space,
                    goal=self.goal,
                    plan=self.plan,
                    action_history=self.action_history if self.add_action_history else None,
                    feedback=feed_back,
                    candidate_action=candidate_action,
                )
                verify_time += 1

            give_action = candidate_action
        else:
            give_action = None

        # print(self.current_action)
        self.current_action = self.action_module.merge_action(self.ml_action, use_action, destroy_action, give_action)
        save_ml_action(self.file_name_action, tick, self.current_action)
        mdp_action = self.action_manager.execute(obs, self.current_action)
        self.executed_ml_action_number += 1
        self.mdp_action = mdp_action

        return mdp_action
