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

PASSABLE_TILE = (
    "Foliage",
    "Ore",
    "Tree",
    "Crystal",
    "Herb",
    "Grass",
    "Scrub",
)

IMPASSABLE_TILE = (
    "Water",
    "Stone",
    "Slag",
    "Stump",
    "Fragment",
    "Weeds",
    "Ocean",
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

REGION_SPACE = ["center", "north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
AREA_SPACE = ["center", "north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]

DEFAULT_ACTION = {
    "Move": "Stay",
    "Attack": "Attack nothing",
    "Use": "Use nothing",
    "Destroy": "Destroy nothing",
    "Give": "Give nothing to anyone",
}
