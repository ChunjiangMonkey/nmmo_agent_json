import sys
import os
import re
import textwrap

current_dir = os.path.abspath(__file__)
sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

from game_prompt import (
    RESOURCE_DETAIL,
    COMBAT_DETAIL,
    ITEM_DETAIL,
    PROFESSION_DETAIL,
    MAP_OVERVIEW,
    FOG_OVERVIEW,
    GAME_OVERVIEW,
    SURVIVAL_OVERVIEW,
    RESOURCE_OVERVIEW,
    COMBAT_OVERVIEW,
    ITEM_OVERVIEW,
    NPC_OVERVIEW,
    PROFESSION_OVERVIEW,
)

elements = {
    # Attributes
    "Health",
    "Food",
    "Water",
    "Defense",
    "Damage",
    # Items
    "Hat",
    "Top",
    "Bottom",
    "Spear",
    "Bow",
    "Wand",
    "Rod",
    "Gloves",
    "Pickaxe",
    "Axe",
    "Chisel",
    "Whetstone",
    "Arrow",
    "Runes",
    "Ration",
    "Potion",
    # Enemy
    "Player",
    "NPC",
    # NPCs
    "Passive",
    "Neutral",
    "Aggressive",
    # Resources
    "Water",
    "Food",
    "Fish",
    "Herb",
    "Ore",
    "Tree",
    "Crystal",
    # Skills
    "Melee",
    "Range",
    "Mage",
    "Fishing",
    "Herbalism",
    "Prospecting",
    "Carving",
    "Alchemy",
}


def format_string(s):
    return textwrap.dedent(s).lstrip()


class GameRuleModule:

    def __init__(self, config):
        self.config = config
        self.element = elements
        self.element_sentences = self._identify_elements(elements, self._bearkdown_game_rules())
        self.game_rule_overview = self._generate_game_rule(add_detail_game_rule=False) 
        self.complete_game_rule = self._generate_game_rule(add_detail_game_rule=True)


    def get_detail_game_rule(self, task=None):
        """
        动态生成与任务相关的规则
        """
        if not task:
            return self.complete_game_rule
        related_elements = []
        for element in elements:
            if element in task:
                if self._find_element(element, task):
                    related_elements.append(element)

        if not related_elements:
            return self.complete_game_rule
        related_sentences = []
        for element in related_elements:
            for sentence in self.element_sentences[element]:
                if sentence not in related_sentences:
                    related_sentences.append(sentence)
        if not related_sentences:
            return self.complete_game_rule
        related_detail_game_rule = ".\n".join(related_sentences) + ". "
        return self.game_rule_overview + "\n\n##Related Game Rules\n" + related_detail_game_rule

    def _generate_game_rule(self, add_detail_game_rule=False):
        map_size = self.config.MAP_CENTER
        view_radius = self.config.PLAYER_VISION_RADIUS
        view_size = 2 * view_radius + 1

        game_rule = (
            format_string(GAME_OVERVIEW)
            + "\n"
            + format_string(SURVIVAL_OVERVIEW)
            + "\n"
            + format_string(MAP_OVERVIEW.format(map_size=map_size, view_size=view_size))
            + "\n"
            + format_string(RESOURCE_OVERVIEW)
        )
        if add_detail_game_rule:
            game_rule += format_string(RESOURCE_DETAIL)
        if self.config.DEATH_FOG_ONSET:
            game_rule += "\n" + format_string(
                FOG_OVERVIEW.format(fog_begin_time=self.config.DEATH_FOG_ONSET)
            )

        if self.config.COMBAT_SYSTEM_ENABLED:
            game_rule += "\n" + format_string(COMBAT_OVERVIEW.format(view_size=view_size))
            if add_detail_game_rule:
                game_rule += format_string(COMBAT_DETAIL)
        if (
            self.config.COMBAT_SYSTEM_ENABLED
            and self.config.PROGRESSION_SYSTEM_ENABLED
            and self.config.EQUIPMENT_SYSTEM_ENABLED
            and self.config.ITEM_SYSTEM_ENABLED
        ):
            game_rule += "\n" + format_string(ITEM_OVERVIEW)

            if add_detail_game_rule:
                game_rule += format_string(ITEM_DETAIL)
            game_rule += "\n" + format_string(PROFESSION_OVERVIEW)
            if add_detail_game_rule:
                game_rule += format_string(PROFESSION_DETAIL)

        if self.config.NPC_SYSTEM_ENABLED:
            game_rule += "\n" + format_string(NPC_OVERVIEW)
        return game_rule

    def _bearkdown_game_rules(self):
        sentences = []
        rules = [RESOURCE_DETAIL, COMBAT_DETAIL, ITEM_DETAIL, PROFESSION_DETAIL]
        for rule in rules:
            parts = re.split(r"\.(?=\s|$)", rule)
            parts = [part.strip() for part in parts if part.strip()]
            sentences.extend(parts)
        return sentences

    def _identify_elements(self, elements, sentences):
        element_sentences = {}
        for sentence in sentences:
            for element in elements:
                if element not in element_sentences.keys():
                    element_sentences[element] = []
                if self._find_element(element, sentence):
                    if sentence not in element_sentences[element]:
                        element_sentences[element].append(sentence)

        return element_sentences

    def _find_element(self, element, sentence):
        element = element.lower()
        sentence = sentence.lower()

        if element in sentence:
            pattern = r"\b" + re.escape(element) + r"\b"  # 避免部分匹配
            return bool(re.search(pattern, sentence))

        return False