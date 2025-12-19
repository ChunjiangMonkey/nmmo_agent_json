import numpy as np
import re
from game_rule import RESOURCE_DETAIL, COMBAT_DETAIL, ITEM_DETAIL, PROFESSION_DETAIL

# import nltk

# nltk.download("punkt_tab")

# from nltk.tokenize import sent_tokenize

entities = {
    "Attributes": ["Health", "Food", "Water", "Defense", "Damage"],
    "Items": [
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
    ],
    "Enemy": ["Player", "NPC"],
    "NPCs": ["Passive", "Neutral", "Aggressive"],
    "Resources": ["Water", "Food", "Fish", "Herb", "Ore", "Tree", "Crystal"],
    "Skills": [
        "Melee",
        "Range",
        "Mage",
        "Fishing",
        "Herbalism",
        "Prospecting",
        "Carving",
        "Alchemy",
    ],
}


def bearkdown_game_rules():
    sentences = []
    rules = [RESOURCE_DETAIL, COMBAT_DETAIL, ITEM_DETAIL, PROFESSION_DETAIL]
    for rule in rules:
        parts = re.split(r"\.(?=\s|$)", rule)
        parts = [part.strip() for part in parts if part.strip()]
        sentences.extend(parts)
    return sentences


def find_entity(entity, sentence):
    """判断单个实体是否在句子中"""
    if not entity or not sentence:
        return False

    # 不区分大小写的完整单词匹配
    entity_lower = entity.lower()
    sentence_lower = sentence.lower()

    # 先检查是否包含
    if entity_lower in sentence_lower:
        # 再检查是否是完整单词（避免部分匹配）
        pattern = r"\b" + re.escape(entity_lower) + r"\b"
        return bool(re.search(pattern, sentence_lower))

    return False


def identify_entities(entities, sentences):
    """识别句子中包含的所有实体"""
    result = {}
    for sentence in sentences:
        # 遍历每种实体类型
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                if entity not in result.keys():
                    result[entity] = []
                if find_entity(entity, sentence):
                    if sentence not in result[entity]:
                        result[entity].append(sentence)

    return result


if __name__ == "__main__":
    import json

    sentences = bearkdown_game_rules()
    # for sentence in sentences:
    #     print(sentence)
    #     print(".........")

    identification_result = identify_entities(entities, sentences)
    print(identification_result)
    json.dump(identification_result, open("new_identification_result.json", "w"), indent=4)
