MATERIAL_NAME_TO_ID = {
    "Void": 0,
    "Water": 1,
    "Grass": 2,
    "Scrub": 3,
    "Foliage": 4,
    "Stone": 5,
    "Slag": 6,
    "Ore": 7,
    "Stump": 8,
    "Tree": 9,
    "Fragment": 10,
    "Crystal": 11,
    "Weeds": 12,
    "Herb": 13,
    "Ocean": 14,
    "Fish": 15,
}

ITEM_NAME_TO_ID = {
    # Armor
    "Hat": 2,
    "Top": 3,
    "Bottom": 4,
    # Weapon
    "Spear": 5,
    "Bow": 6,
    "Wand": 7,
    # Tool
    "Rod": 8,
    "Gloves": 9,
    "Pickaxe": 10,
    "Axe": 11,
    "Chisel": 12,
    # Ammunition
    "Whetstone": 13,
    "Arrow": 14,
    "Runes": 15,
    # Consumable
    "Ration": 16,
    "Potion": 17,
}


IMPASSIBLE_TILE = (
    "Water",
    "Stone",
    "Ocean",
    "Fish",
    "Void",
)

RESOURCE_TILE = (
    "Foliage",
    "Ore",
    "Tree",
    "Crystal",
    "Herb",
    "Water",
    "Fish",
)

HARVESTED_NAME_TO_RESOURCE_NAME = {
    "Scrub": "Foliage",
    "Slag": "Ore",
    "Stump": "Tree",
    "Fragment": "Crystal",
    "Weeds": "Herb",
}

NPC_TYPE_ID_TO_NAME = {
    0: "player",
    1: "passive",
    2: "neutral",
    3: "aggressive",
}

DIRECTION_TO_INDEX = {
    (-1, 0): 0,
    (1, 0): 1,
    (0, 1): 2,
    (0, -1): 3,
    (0, 0): 4,
}

ATTACK_STYLE_TO_INDEX = {
    "melee": 0,
    "range": 1,
    "mage": 2,
}

REGION_SPACE = ["central", "northern", "northeastern", "eastern", "southeastern", "southern", "southwestern", "western", "northwestern"]
AREA_SPACE = ["center", "north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]

DEFAULT_ACTION = {
    "Move": "Stay",
    "Attack": "Attack nothing",
    "Use": "Use nothing",
    "Destroy": "Destroy nothing",
    "Give": "Give nothing to anyone",
}
