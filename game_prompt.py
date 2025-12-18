GAME_OVERVIEW = """
## Overview
In this game, players must survive on a vast map filled with resources, NPCs, and other players. Players need to keep their Health value above 0, otherwise they will die. Players can explore the map, harvest resources, equip items, engage in combat with NPCs or other players, and interact with other players. Harvesting resources from the map is crucial. It allows players to obtain essential food, water, and other consumables needed to maintain health, as well as ammunition and weapons that can increase their attack power. Players can also obtain items directly by defeating NPCs or other players. However, combat involves significant risk, and players are not always guaranteed to be the victor. Players possess a variety of skills related to resource harvesting and combat. These skills can be improved through continuous resource harvesting or engaging in combat. By continuously harvesting resources, acquiring items, and improving their skills, players become progressively stronger.
"""
# GAME_OVERVIEW = """
# ## Overview
# In this game, players must survive on a vast map filled with resources, NPCs, and other players. Players must maintain their food and water levels to preserve their overall health. Each player has 8 individual professions to help them collect resources. Players can level up their skills in each profession. Resources can be used to create consumable items that restore food, water and heath as well as to create ammunition that increases damage in combat. Higher level resources create better consumables and ammunition. Players may aquire armor to protect themselves in combat and weapons to increase their damage output. Players can attack each other using one of three styles: Melee, Range, and Mage. The world is populated by NPCs that can be defeated to obtain items and increase power.
# """

SURVIVAL_OVERVIEW = """
## Survival
Survival is the prerequisite for completing various goals. Each player has Health, Food, and Water, each with a maximum value of 100. Food/Water drop 10 each tick. If Water or Food is 0, the player loses 10 Health per tick; if both are 0, Health loses 20 per tick. Health regenerates 10 per tick if food and water are above 50. 
"""

# MAP_OVERVIEW = """
# ## Game Map
# The map is a {map_size} × {map_size} tile map. Tiles fall into two types: passable tiles and obstacle tiles. Passable tiles include: Foliage, Ore, Tree, Crystal, Herb, Grass, Scrub (Harvested Tile). Obstacle tiles include: Water, Fish, Stone. The map is partially observable, and the player can only see information on tiles within a {view_size} × {view_size} area. Players cannot leave the map edges. 
# """
MAP_OVERVIEW = """
## Tile, Game Map and Observation
A tile is the basic unit that makes up the map. The game map has a total size of {map_size} × {map_size} tiles. Each tick, a player can move only one tile.
To provide players with macro-level information about their current location, the entire game map is roughly divided into nine regions: the central region, eastern region, western region, northern region, southern region, northeastern region, southeastern region, northwestern region, and southwestern region. Players are informed of the region they are in to clarify their macro-level position on the map.
Players cannot see the entire map. They can only view an area of {view_size} × {view_size} tiles centered on themselves. To help players decide which direction to move, their field of view is also divided into nine areas: the center area, the eastern area, the western area, the northern area, the southern area, the northeastern area, the southeastern area, the northwestern area, and the southwestern area. The division logic and directional layout are identical to those of the full game map. The difference is that region refers to an absolute position on the map, while area refers to a relative position within the player's observation space. Players always occupy the center area of their field of view. When making decisions, players are informed about the resources, NPCs, and other players present in each region within their view. This provides micro-level positional information.
By combining both macro-level and micro-level information, players can effectively plan which direction to explore next.
"""

FOG_OVERVIEW = """
## Fog
The fog area appears at time {fog_begin_time} and gradually expands from the edges of the map toward the center. The fog area inflicts damage on any agent within it. The longer an agent stays inside, the more damage it takes.  A permanent safe area exists at the center of the map, which is never covered by the fog.
"""

RESOURCE_OVERVIEW = """
## Resources
Players can harvest resources by moving onto a resource tile, which grants the corresponding item. The game has 7 types of resources: Water, Foliage, Fish, Herb, Tree, Ore, Crystal. Equipping tools can improve the quality of harvested items. 
Water tile restores water. Foliage tile restores food. Fish always provides a Ration; without a Rod, it yields a level 1 Ration, and with a Rod, the Ration's level equals Rod's level + 1. Herb always provides a Potion; without a Glove, it yields a level 1 Potion, and with a Glove, the Potion's level equals Glove's level + 1.
"""


COMBAT_OVERVIEW = """
## Combat
A player can attack other entities (NPCs or other players) within their attack range. Available attack styles include: Melee, Range, or Mage. The damage depends on the attacker's attack skill level, weapon level, attacker's ammunition level, the target entity's defense value, and the counter relationship between attacker and target's attack styles. All three attack styles have an attack range of 3, which is less than the observation range {view_size}. The counter relationships between styles follow rock-paper-scissors rules: Melee counters Range, Range counters Mage, Mage counters Melee.
"""


ITEM_OVERVIEW = """
## Items
There are 17 types of items across 5 categories: Weapons, Ammunition, Armor, Tools and Consumables. Different items have different functions, acquisition methods, and skill requirements. Each player has one Hat Armor slot, one Top Armor slot, one Bottom Armor slot, one Weapon/Tool slot, and one Ammunition slot. Weapons include Spear, Bow, Wand; Ammunition include Whetstone, Arrow, Runes; Armor include Hat, Top, Bottom; Tools include Rod, Gloves, Axe, Pickaxe, Chisel; Consumables include Ration, Potion. Items can only be equipped or used outside of combat. Each Player has an inventory with a capacity of 12 slots for storing obtained items. Equipped items still occupy the inventory. Defeating an NPC always yields one Tool and one Armor of any type, both at the same level as the defeated NPC. Defeating another player grants all the items they possess. 
"""

PROFESSION_OVERVIEW = """
## Skill Level
Players can learn and level up 8 skills, include 3 combat skills: Melee, Range, Mage and 5 harvesting skills: Fishing, Herbalism, Carving, Prospecting, Alchemy. Higher-level combat skills increase the attack power of corresponding attack styles. Higher-level harvesting skills increase the yield of harvesting corresponding resources.
"""


NPC_OVERVIEW = """
## NPC
Defeating NPCs is the primary way to obtain tools and armor. The higher the NPC's level, the higher the level of the dropped equipment. Depending on their aggressiveness, NPCs can be classified into three types: Passive, Neutral, and Aggressive. Passive NPCs are generally low-level and never attack players under any circumstances. Neutral NPCs only attack players who attack them first, and will stop attacking players who no longer attack them. Aggressive NPCs are high-level and will actively chase and attack players within a certain range. Passive NPCs spawn at the map edges. Neutral NPCs spawn between the edges and center. Aggressive NPCs spawn in the center. NPCs spawn at various levels. 
"""


RESOURCE_DETAIL = """
Water tile restores water. Foliage tile restores food. Fish always provides a Ration; without a Rod, it yields a level 1 Ration, and with a Rod, the Ration's level equals Rod's level + 1. Herb always provides a Potion; without a Glove, it yields a level 1 Potion, and with a Glove, the Potion's level equals Glove's level + 1. Tree always provides an Arrow (Range ammunition) and has a 2.5% chance to drop a Spear (Melee weapon); without an Axe, the Arrow or Spear is level 1, and with an Axe, its level equals Axe's level + 1. Ore always provides a Whetstone (Melee ammunition) and has a 2.5% chance to drop a Wand (Mage weapon); without a Pickaxe, the Whetstone or Wand is level 1, and with a Pickaxe, its level equals Pickaxe's level + 1. Crystal always provides Runes (Mage ammunition) and has a 2.5% chance to drop a Bow (Range weapon); without a Chisel, the Runes or Bow is level 1, and with a Chisel, its level equals Chisel's level + 1.
"""

COMBAT_DETAIL = """
The attack power of Melee style is determined by the Melee skill level, the level of the equipped Spear, and the level of the equipped Whetstone; higher levels result in higher attack power. The attack power of Range style is determined by the Range skill level, the level of the equipped Bow, and the level of the equipped Arrow; higher levels result in higher attack power. The attack power of Mage style is determined by the Mage skill level, the level of the equipped Wand, and the level of the equipped Runes; higher levels result in higher attack power. Using a combat style that counters enemies deals higher damage. Armor consists of three types: Hat, Top, Bottom, which provides defense and reduces damage taken by enemies. Higher-level armor offers higher defense values. Equipping tools of any type (Rod, Gloves, Axe, Pickaxe, Chisel) increases defense.
"""

ITEM_DETAIL = """
Hat can be equipped to increase defense; occupy the hat armor slot if equipped; can be obtained by defeating NPCs/other players; can only be equipped when any skill level is higher than the Hat's level. 
Top can be equipped to increase defense; occupy the top armor slot if equipped; can be obtained by defeating NPCs/other players; can only be equipped when any skill level is higher than the Top's level. 
Bottom can be equipped to increase defense; occupy the bottom armor slot if equipped; can be obtained by defeating NPCs/other players; can only be equipped when any skill level is higher than the Bottom's level.
Spear can be equipped to increase melee attack damage; occupy the weapon/tool slot if equipped; can be obtained by harvesting Tree tiles or defeating other players; can only be equipped when melee level is higher than the Spear's level. 
Bow can be equipped to increase range attack damage; occupy the weapon/tool slot if equipped; can be obtained by harvesting Crystal tiles or defeating other players; can only be equipped when range level is higher than the Bow's level. 
Wand can be equipped to increase mage attack damage; occupy the weapon/tool slot if equipped; can be obtained by harvesting Ore tiles or defeating other players; can only be equipped when mage level is higher than the Wand's level.
Whetstone can be equipped to increase melee attack damage; occupy the ammunition slot if equipped; can be obtained by harvesting Ore tiles or defeating other players; can only be equipped when melee level is higher than the Whetstone's level. 
Arrow can be equipped to increase range attack damage; occupy the ammunition slot if equipped; can be obtained by harvesting Tree tiles or defeating other players; can only be equipped when range level is higher than the Arrow's level. 
Runes can be equipped to increase mage attack damage; occupy the ammunition slot if equipped; can be obtained by harvesting Crystal tiles or defeating other players; can only be equipped when mage level is higher than the Runes's level.
Rod can be equipped to increase the yield of harvesting Fish if equipped; occupy the weapon/tool slot if equipped; can be obtained by defeating NPCs/other players; can only be equipped when Fishing level is higher than the Rod's level. 
Gloves can be equipped to increase the yield of harvesting Herb if equipped; occupy the weapon/tool slot if equipped; can be obtained by defeating NPCs/other players; can only be equipped when Herbalism level is higher than the Gloves's level.
Axe can be equipped to increase the yield of harvesting Tree if equipped; occupy the weapon/tool slot if equipped; can be obtained by defeating NPCs/other players; can only be equipped when Carving level is higher than the Axe's level.
Pickaxe can be equipped to increase the yield of harvesting Ore if equipped; occupy the weapon/tool slot if equipped; can be obtained by defeating NPCs/other players; can only be equipped when Prospecting level is higher than the Pickaxe's level.
Chisel can be equipped to increase the yield of harvesting Crystal if equipped; occupy the weapon/tool slot if equipped; can be obtained by defeating NPCs/other players; can only be equipped when Alchemy level is higher than the Chisel's level.
Ration can be used to restore Food and Water; can be obtained by harvesting Fish tiles or defeating NPCs/other players; can only be used when any skill level is higher than the Ration's level. 
Potion can be used to restore Health; can be obtained by harvesting Herb tiles or defeating NPCs/other players; can only be used when any skill level is higher than the Potion's level.
"""

PROFESSION_DETAIL = """
Higher-level Melee skill can increase melee damage and the level of Spear and Whetstone that can be equipped; Melee skill can be improved by attacking with melee style.
Higher-level Range skill can increase range damage and the level of Bow and Arrow that can be equipped; Range skill can be improved by attacking with range style.
Higher-level Mage skill can increase mage damage and the level of Wand and Runes that can be equipped; Mage skill can be improved by attacking with mage style.
Higher-level Fishing skill can increase the yield of harvesting Fish and the level of Rod that can be equipped; Fishing skill can be improved by harvesting Fish.
Higher-level Herbalism skill can increase the yield of harvesting Herb and the level of Glove that can be equipped; Herbalism skill can be improved by harvesting Herb.
Higher-level Carving skill can increase the yield of harvesting Tree and the level of Axe that can be equipped; Carving skill can be improved by harvesting Tree.
Higher-level Prospecting skill can increase the yield of harvesting Ore and the level of Pickaxe that can be equipped; Prospecting skill can be improved by harvesting Ore.
Higher-level Alchemy skill can increase the yield of harvesting Crystal and the level of Chisel that can be equipped; Alchemy skill can be improved by harvesting Crystal.
"""
