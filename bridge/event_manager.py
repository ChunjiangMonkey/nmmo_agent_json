from json.encoder import py_encode_basestring_ascii
from nmmo.lib.event_code import EventCode


class EventManager:
    """
    处理游戏中的事件, 作为agent的记忆
    """

    def __init__(self, agent_num):
        self.agent_ids = list(range(1, agent_num + 1))
        self.all_attack_style = ["Melee", "Range", "Mage"]
        self.all_items = [
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
        ]
        self.item_res_map = {
            "Whetstone": "Ore",
            "Wand": "Ore",
            "Arrow": "Tree",
            "Spear": "Tree",
            "Runes": "Crystal",
            "Bow": "Crystal",
            "Ration": "Fish",
            "Potion": "Herb",
        }
        self.all_skills = [
            "Melee",
            "Range",
            "Mage",
            "Fishing",
            "Herbalism",
            "Prospecting",
            "Carving",
            "Alchemy",
        ]
        self.record_keys = [
            "tile",  # tuple
            "eat_food",
            "drink_water",
            "attack",
            "being_attacked",  # list
            "kill",
            "being_killed",
            "consume",
            "harvest",  # list
            "give",
            "being_given",  # list
            "destroy",
            "equip",
            "loot",  # list
            "skill_level_up",  # list
            "dead",
        ]

    # def update(self, events):
    #     self.update_record(events)
    #     self.generate_event_description()
    #     return self.current_record

    def update_record(self, events):
        self.current_record = {i: dict.fromkeys(self.record_keys) for i in self.agent_ids}
        for event in events:
            event_code = event[3]
            if event_code == EventCode.EAT_FOOD:
                self.update_eat_food_record(event)
            elif event_code == EventCode.DRINK_WATER:
                self.update_drink_water_record(event)
            elif event_code == EventCode.SCORE_HIT:
                self.update_attack_record(event)
            elif event_code == EventCode.PLAYER_KILL:
                self.update_player_kill_record(event)
            elif event_code == EventCode.LOOT_ITEM:
                self.update_loot_item_record(event)
            elif event_code == EventCode.CONSUME_ITEM:
                self.update_consume_item_record(event)
            elif event_code == EventCode.HARVEST_ITEM:
                self.update_harvest_item_record(event)
            elif event_code == EventCode.EQUIP_ITEM:
                self.update_equip_item_record(event)
            elif event_code == EventCode.GIVE_ITEM:
                self.update_give_item_record(event)
            elif event_code == EventCode.DESTROY_ITEM:
                self.update_destroy_item_record(event)
            elif event_code == EventCode.LEVEL_UP:
                self.update_skill_level_up_record(event)
            elif event_code == EventCode.AGENT_CULLED:
                self.update_culled_record(event)
        return self.current_record

    def update_eat_food_record(self, event):
        player_id = event[1]
        self.current_record[player_id]["eat_food"] = True

    def update_drink_water_record(self, event):
        player_id = event[1]
        self.current_record[player_id]["drink_water"] = True

    def update_attack_record(self, event):
        attacker_id = event[1]
        target_id = event[8]
        attack_style = self.all_attack_style[event[4] - 1]
        damage = event[6]

        if attacker_id > 0:  # 需要更新attacker的attack记录
            target_name = f"Player {target_id}" if target_id > 0 else f"NPC {-target_id}"

            attack_event = {
                "target": target_name,
                "style": attack_style,
                "damage": damage,
            }
            # 只能攻击一个玩家
            assert self.current_record[attacker_id]["attack"] is None
            self.current_record[attacker_id]["attack"] = attack_event

        if target_id > 0:  # 需要更新target的being_attacked记录
            attacker_name = f"Player {attacker_id}" if attacker_id > 0 else f"NPC {-attacker_id}"
            being_attacked_event = {
                "attacker": attacker_name,
                "style": attack_style,
                "damage": damage,
            }

            # 可以被多个敌人攻击
            # self.current_record[target_id]["being_attacked"] = being_attacked_event
            if self.current_record[target_id]["being_attacked"]:
                self.current_record[target_id]["being_attacked"].append(being_attacked_event)
            else:
                self.current_record[target_id]["being_attacked"] = [being_attacked_event]

    def update_player_kill_record(self, event):
        killer_id = event[1]
        target_id = event[8]
        target_level = event[5]
        if killer_id > 0:  # 需要更新killer的kill记录
            target_name = f"Player {target_id}" if target_id > 0 else f"NPC {-target_id}"
            kill_event = {
                "target": target_name,
                "level": target_level,
            }
            assert self.current_record[killer_id]["kill"] is None
            self.current_record[killer_id]["kill"] = kill_event
        if target_id > 0:
            killer_name = f"Player {target_id}" if target_id > 0 else f"NPC {-target_id}"
            being_killed_event = {
                "killer": killer_name,
                "level": target_level,
            }
            assert self.current_record[target_id]["being_killed"] is None
            self.current_record[target_id]["being_killed"] = being_killed_event

    def update_loot_item_record(self, event):
        player_id = event[1]
        item_type = event[4]
        item_name = self.all_items[item_type - 2]
        item_level = event[5]
        item_number = event[6]
        loot_item_event = {
            "item": item_name,
            "level": item_level,
            "number": item_number,
        }
        if self.current_record[player_id]["loot"]:  # 可以拾取多个物品
            self.current_record[player_id]["loot"].append(loot_item_event)
        else:
            self.current_record[player_id]["loot"] = [loot_item_event]

    def update_consume_item_record(self, event):
        player_id = event[1]
        item_type = event[4]
        item_level = event[5]
        item_number = event[6]
        restore_value = 50 + 5 * item_level
        if item_type == 16:
            item_name = "Ration"
        elif item_type == 17:
            item_name = "Potion"
        consume_item_event = {
            "item": item_name,
            "level": item_level,
            "number": item_number,
            "restore_value": restore_value,
        }
        assert self.current_record[player_id]["consume"] is None
        self.current_record[player_id]["consume"] = consume_item_event

    def update_harvest_item_record(self, event):
        player_id = event[1]
        item_type = event[4]
        item_level = event[5]
        item_number = event[6]
        item_name = self.all_items[item_type - 2]
        item_res = self.item_res_map[item_name]
        harvest_item_event = {
            "item": item_name,
            "item_res": item_res,
            "level": item_level,
            "number": item_number,
        }
        if self.current_record[player_id]["harvest"]:
            self.current_record[player_id]["harvest"].append(harvest_item_event)
        else:
            self.current_record[player_id]["harvest"] = [harvest_item_event]

    def update_equip_item_record(self, event):
        player_id = event[1]
        item_type = event[4]
        item_level = event[5]
        item_name = self.all_items[item_type - 2]
        item_number = event[6]
        equip_item_event = {
            "item": item_name,
            "level": item_level,
            "number": item_number,
        }
        assert self.current_record[player_id]["equip"] is None
        self.current_record[player_id]["equip"] = equip_item_event

    def update_give_item_record(self, event):
        giver_id = event[1]
        target_id = event[8]
        item_type = event[4]
        item_level = event[5]
        item_number = event[6]
        item_name = self.all_items[item_type - 2]

        if giver_id > 0:
            assert target_id > 0
            target_name = f"Player {target_id}"
            give_item_event = {
                "item": item_name,
                "level": item_level,
                "number": item_number,
                "target": target_name,
            }
            assert self.current_record[giver_id]["give"] is None
            self.current_record[giver_id]["give"] = give_item_event
        if target_id > 0:
            assert giver_id > 0
            giver_name = f"Player {giver_id}"
            being_given_event = {
                "item": item_name,
                "level": item_level,
                "number": item_number,
                "giver": giver_name,
            }
            if self.current_record[target_id]["being_given"]:
                self.current_record[target_id]["being_given"].append(being_given_event)
            else:
                self.current_record[target_id]["being_given"] = [being_given_event]

    def update_destroy_item_record(self, event):
        pass

    def update_skill_level_up_record(self, event):
        player_id = event[1]
        skill_type = event[4]
        skill_name = self.all_skills[skill_type - 1]
        skill_level = event[5]
        skill_level_up_event = {
            "skill": skill_name,
            "level": skill_level,
        }
        if self.current_record[player_id]["skill_level_up"]:
            self.current_record[player_id]["skill_level_up"].append(skill_level_up_event)
        else:
            self.current_record[player_id]["skill_level_up"] = [skill_level_up_event]

    def update_culled_record(self, event):
        player_id = event[1]
        assert self.current_record[player_id]["dead"] is None
        self.current_record[player_id]["dead"] = True
