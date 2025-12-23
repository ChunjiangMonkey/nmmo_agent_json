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

from agent.prompt_template import (
    generate_assistant_system_prompt,
    generate_assistant_user_prompt,
)


import numpy as np
import tqdm
import tiktoken

from llm_client import LLMClient
import nmmo
from nmmo.core.tile import TileState
from nmmo.entity.entity import Entity
from nmmo.systems.item import Item

import nmmo.core.config as nc
from nmmo.lib import utils
from nmmo.lib import material
import openai
import os
import json
from utils.io_utils import write_to_file

assistant_response_format = {
    "reason": "reason for selecting Give action. ",
    "choice": "*Only* return the action you select. Do not add extra text",
}


class Assistant:
    def __init__(
        self,
        llm_client,
        config,
        env,
        horizon,
        assistant_role,
        save_path,
        player_role="task",
        debug=False,
    ):
        ##### 参数 #####
        self.llm_client = llm_client
        self.config = config
        self.env = env
        self.horizon = horizon
        self.assistant_role = assistant_role
        self.save_path = save_path
        self.player_role = player_role
        self.debug = debug

    def generate_input_message(
        self,
        game_mechanics,
        state_description,
        action_space,
        goal=None,
    ):
        # ========= System Message =========
        system_prompt = generate_assistant_system_prompt(
            assistant_response_format,
            self.player_role,
            self.assistant_role,
            use_fog=self.config.DEATH_FOG_ONSET,
        )

        system_message = {
            "role": "system",
            "content": system_prompt,
        }

        # ========= User Message =========
        user_prompt = generate_assistant_user_prompt(
            game_mechanics,
            state_description,
            action_space,
            goal=goal,
        )
        user_message = {
            "role": "user",
            "content": user_prompt,
        }

        return [system_message, user_message]

    def act_randomly(self, action_space):
        response = assistant_response_format
        response["choice"] = random.choice(action_space)
        response["reason"] = "Act randomly."
        return response

    def propose(self, tick, game_mechanics, state_description, action_space, goal=None):

        input_message = self.generate_input_message(
            self.player_role,
            game_mechanics,
            state_description,
            action_space,
            goal=goal,
        )

        if self.debug:
            random_choice = random.choice(action_space)
            response = {
                "choice": random_choice,
                "reason": f"Fake reason for choosing {random_choice}.",
            }
        else:
            response = self.llm_client.generate(input_message, assistant_response_format, action_space)
        # print("response in act:", response)
        if response:

            write_to_file(
                self.save_path,
                [
                    f"=== tick: {tick} {self.assistant_role} action output ===",
                    json.dumps(response, indent=4),
                ],
            )

        else:
            random_choice = random.choice(action_space)
            response = {
                "choice": random_choice,
                "reason": f"Fake reason for choosing {random_choice}.",
            }
            write_to_file(
                self.save_path,
                [
                    f"=== tick: {tick} {self.assistant_role} action output ===",
                    "Fail to get action response. So act randomly.  ",
                ],
            )

            return None
