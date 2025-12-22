import re
from llm_client import LLMClient

from utils.io_utils import write_to_file


INIT_STRATEGY = [
    "If you are running low on food or water, you should prioritize finding Foliage or Water tiles, because food and water drop each tick, and lacking them will cause continuous health loss. ",
    "If you want better harvests from resource tiles, you should equip appropriate tools like Rod, Gloves, Axe, Pickaxe, or Chisel, because they increase your chances of getting high-quality or rare items. ",
    "If you are in combat, you should use a combat style that counters your enemy's style, because Melee > Range, Range > Mage, and Mage > Melee deals increased damage. ",
    "If your food and water levels are above 50, you should avoid combat and maintain the condition, because health will regenerate, helping you survive longer. ",
    "If the fog is expanding, you should move toward the center of the map quickly, because the fog causes damage over time, and the center is a permanent safe zone. ",
    "If your inventory is full, you should discard lower-tier items and keep equipment that matches your skill levels, because you can only carry 12 items, and high-level gear is more helpful. ",
    "If you want to equip higher-level tool or weapon, you should level up the relevant skill through combat or harvesting, because each item has a required skill level to equip. ",
    "If you lack equipment or have low skill levels, you should still target Passive NPCs, because they don't retaliate, making them safe practice targets early on. ",
    "If you are well-equipped and have high enough skill levels, you should initiate combat with Neutral NPCs to obtain better equipment, because they are mid-tier threats and drop better gear, only fighting back when provoked. ",
    "If you are fully equipped and skilled, you should consider fighting Aggressive NPCs for top-tier loot, because they spawn near the center and drop the highest-level gear, which is crucial late-game. ",
]

STRATEGY_MERGE_SYSTEM_TEMPLATE = "You are an AI assitant in an open-world survival game. I have summarized some strategies to help me play this game. However, these strategies may be redundant or incorrect. I need you to reorganize my strategy pool based on the game mechanics. You may merge redundant strategies or remove incorrect ones. Return a refined strategy pool after your reorganizing.\nThe format of your reply should be:\n# Strategy\n{your streamlined strategies}\nKeep the original format of the strategies, and separate different strategies with '\n'. Do not add any other text. "

STRATEGY_MERGE_USER_TEMPLATE = "Game Mechanics\n{game_mechanics}\n\nStrategy Pool\n{strategies}"


class StrategyManager:
    def __init__(self, model_name, debug=False):
        self.strategy_pool = set(INIT_STRATEGY)
        self.model_name = model_name
        self.llm_client = LLMClient(model=model_name)
        self.save_path = None
        self.data_time = None
        self.new_adding_strategy_this_episode = 0
        self.debug = debug

    def reset(self, save_path):
        self.save_path = f"{save_path}/strategy_{self.model_name}.txt"
        self.new_adding_strategy_this_episode = 0

    def set_game_mechanics(self, game_mechanics):
        self.game_mechanics = game_mechanics

    def add(self, strategy):
        self.strategy_pool.add(strategy)
        self.new_adding_strategy_this_episode += 1
        if self.new_adding_strategy_this_episode % 5 == 0:
            self.update_strategy_pool()

    # def remove(self, strategy):
    #     self.strategy_pool.remove(strategy)

    # def update(self, old_strategy, new_strategy):
    #     self.remove(old_strategy)
    #     self.add(new_strategy)

    def get_strategy(self):
        return self.strategy_pool

    def get_strategy_str(self):
        return "\n".join(self.strategy_pool)

    def _generate_input_message(self):
        # ========= System Message =========
        system_prompt = STRATEGY_MERGE_SYSTEM_TEMPLATE
        system_message = {
            "role": "system",
            "content": system_prompt,
        }

        # ========= User Message =========

        user_prompt = STRATEGY_MERGE_USER_TEMPLATE.format(
            game_mechanics=self.game_mechanics,
            strategies=self.get_strategy_str(),
        )

        user_message = {
            "role": "user",
            "content": user_prompt,
        }

        return [system_message, user_message]

    def _get_llm_response(self, input_message):
        try_time = 0
        while try_time <= 3:
            response = self.llm_client.generate(input_message)
            try:
                pattern = r"# Strategy\n(.+)"
                match = re.search(pattern, response, re.DOTALL)
                response = match.group(1)

            except ValueError:
                print(response)  # print(response)
                try_time += 1
            else:
                return response

        self.error_response_num += 1
        print(f"Error response number: {self.error_response_num}")
        return None

    def update_strategy_pool(self):
        input_message = self._generate_input_message()
        write_to_file(
            self.save_path,
            [
                f"=== strategy update input ===",
                f"=== system message ===\n{input_message[0]['content']}",
                f"=== user message ===\n{input_message[1]['content']}",
            ],
        )
        if self.debug:
            response = "# Fake strategy update"
        else:
            response = self._get_llm_response(input_message)
        if response:
            self.strategy_pool = set(response.split("\n"))
            write_to_file(
                self.save_path,
                [f"=== strategy update output ===", response],
            )

        else:
            print("Error: Failed to update strategy pool")
