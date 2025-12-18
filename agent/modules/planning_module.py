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
from agent.prompt_template import generate_plan_system_prompt, generate_plan_user_prompt
from utils.io_utils import write_to_file

plan_response_format = {
    "reason": "reason for generating plan. ",
    "plan": "plan for achieving long-term goal. Please create the plan in the format: (1) step 1 (2) step 2 (3) step 3..., and organize the plan in chronological order based on the timeline of the goals I should achieve.",
}


class PlanningModule:
    def __init__(self, config, llm_client, save_path, debug=False):
        self.config = config
        self.llm_client = llm_client
        self.save_path = save_path
        self.debug = debug

    def plan(
        self,
        goal,
        game_mechanics,
        game_state=None,
    ):
        input_message = self.generate_input_message(goal, game_mechanics, game_state=game_state)
        write_to_file(
            self.save_path,
            [
                f"=== plan ===",
                f"=== system message ===\n{input_message[0]['content']}",
                f"=== user message ===\n{input_message[1]['content']}",
            ],
        )
        if self.debug:
            response = {
                "reason": "Fake reason for generating plan.",
                "plan": "Fake plan",
            }
        else:
            response = self.llm_client.generate(input_message, plan_response_format)
        if response:
            write_to_file(
                self.save_path,
                [
                    f"=== plan ===",
                    json.dumps(response, indent=4),
                ],
            )
            return response["plan"]
        else:
            write_to_file(
                self.save_path,
                [
                    f"=== plan ===",
                    "Fail to get plan response.",
                ],
            )
        return None

    def generate_input_message(self, goal, game_mechanics, game_state=None):
        # ========= System Message =========

        system_prompt = generate_plan_system_prompt(plan_response_format, game_state=game_state)

        system_message = {
            "role": "system",
            "content": system_prompt,
        }

        # ========= User Message =========

        user_prompt = generate_plan_user_prompt(
            goal,
            game_mechanics,
            game_state=game_state,
        )

        user_message = {
            "role": "user",
            "content": user_prompt,
        }

        return [system_message, user_message]
