import sys
import os
import re
import json
import random

current_dir = os.path.abspath(__file__)
sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

from nmmo.lib import utils
from constant import AREA_SPACE
from game_rule import RESOURCE_TABLE, NPC_TABLE, COMBAT_TABLE, ITEM_TABLE, SKILL_TABLE
from utils.io_utils import write_to_file

from agent.prompt_template import (
    generate_reduction_system_prompt,
    generate_reduction_user_prompt,
)

reduction_response_format = {
    "reduced_game_information": "the filtered information from the raw game mechanics and game state",
}


class ReductionModule:
    def __init__(self, config, llm_client, save_path, use_reduction=False, debug=False):
        self.config = config
        self.llm_client = llm_client
        self.save_path = save_path
        self.use_reduction = use_reduction
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

    def reduce(
        self,
        tick,
        game_mechanics,
        state_description,
        action_space,
        goal=None,
    ):

        input_message = self.generate_input_message(
            game_mechanics,
            state_description,
            action_space,
            goal=goal,
        )

        write_to_file(
            self.save_path,
            [
                f"=== tick: {tick} reduction action input ===",
                f"=== system message ===\n{input_message[0]['content']}",
                f"=== user message ===\n{input_message[1]['content']}",
            ],
        )

        if self.debug:
            response = {
                "reduced_game_information": "fake reduced game information for testing.",
            }
        else:
            response = self.llm_client.generate(input_message, reduction_response_format)
        # print("response in act:", response)
        if response:
            write_to_file(
                self.save_path,
                [
                    f"=== tick: {tick} reduction action output ===",
                    json.dumps(response, indent=4),
                ],
            )
            return response["reduced_game_information"]
        else:
            write_to_file(
                self.save_path,
                [
                    f"=== tick: {tick} reduction action output ===",
                    "Fail to get the reduced game information. ",
                ],
            )

        return None

    def generate_input_message(
        self,
        game_mechanics,
        state_description,
        action_space,
        goal=None,
    ):
        # ========= System Message =========
        system_prompt = generate_reduction_system_prompt(
            reduction_response_format,
        )

        system_message = {
            "role": "system",
            "content": system_prompt,
        }

        # ========= User Message =========
        user_prompt = generate_reduction_user_prompt(
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
