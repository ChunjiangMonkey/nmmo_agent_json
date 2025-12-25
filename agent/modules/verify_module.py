import sys
import os
import re
import json
import numpy as np

current_dir = os.path.abspath(__file__)
sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

from agent.prompt_template import (
    generate_action_verify_system_prompt,
    generate_action_verify_user_prompt,
)
from utils.io_utils import write_to_file

verifier_response_format = {
    "reason": "The reason for evaluation. ",
    "evaluation": "Yes or No. ",
}


class VerifyModule:
    def __init__(self, config, llm_client, save_path, debug=False):
        self.config = config
        self.llm_client = llm_client
        self.save_path = save_path
        self.debug = debug

    def verify(
        self,
        verify_type,
        player_role,
        tick,
        game_mechanics,
        state_description,
        goal=None,
        plan=None,
        action_history=None,
        candidate_action=None,
        verify_time=None,
    ):
        input_message = self.generate_input_message(
            verify_type, player_role, goal, game_mechanics, state_description, candidate_action, plan=plan, strategies=action_history
        )
        write_to_file(
            self.save_path,
            [
                f"=== tick: {tick} {verify_type} input verify_time:{verify_time} ===",
                f"=== system message ===\n{input_message[0]['content']}",
                f"=== user message ===\n{input_message[1]['content']}",
            ],
        )
        if self.debug:
            np.random.seed()
            response = {
                "reason": "Fake reason",
                "evaluation": np.random.choice(["yes", "no"]),
            }
        else:
            response = self.llm_client.generate(input_message, verifier_response_format)
        if response:
            write_to_file(
                self.save_path,
                [
                    f"=== tick: {tick} action output verify_time:{verify_time} ===",
                    json.dumps(response, indent=4),
                ],
            )
        else:
            write_to_file(
                self.save_path,
                [
                    f"=== tick: {tick} action output verify_time:{verify_time} ===",
                    "Fail to get action response.",
                ],
            )
        return response["evaluation"].lower(), response["reason"]

    def generate_input_message(
        self,
        verify_type,
        player_role,
        goal,
        game_mechanics,
        state_description,
        candidate_action,
        plan=None,
        action_history=None,
        strategies=None,
    ):
        # ========= System Message =========

        system_prompt = generate_action_verify_system_prompt(
            verifier_response_format, verify_type, player_role, action_history=action_history, strategies=strategies
        )

        system_message = {
            "role": "system",
            "content": system_prompt,
        }

        # ========= User Message =========

        user_prompt = generate_action_verify_user_prompt(
            goal,
            game_mechanics,
            state_description,
            candidate_action,
            plan=plan,
            action_history=action_history,
            strategies=strategies,
        )

        user_message = {
            "role": "user",
            "content": user_prompt,
        }

        return [system_message, user_message]
