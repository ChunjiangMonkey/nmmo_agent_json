import nmmo.systems.combat
from nmmo.lib.event_code import EventCode
from nmmo.entity import Entity
from nmmo.systems.item import Item
from nmmo.lib import utils
from nmmo.systems.item import Stack

original_attack = nmmo.systems.combat.attack
original_give_call = nmmo.core.action.Give.call
original_record = nmmo.lib.event_log.EventLogger.record


def _new_attack(realm, attacker, target, skill_fn):

    damage = original_attack(realm, attacker, target, skill_fn)
    # 这里也增加了对攻击者是npc、被攻击者是玩家的记录
    if attacker.is_npc and target.is_player:
        realm.event_log.record(
            EventCode.SCORE_HIT,
            attacker,
            target=target,
            combat_style=skill_fn(attacker),
            damage=damage,
        )
    return damage


def _new_give_call(realm, entity, item, target):
    if item is None or item.owner_id.val != entity.ent_id or target is None:
        return

    assert entity.alive, "Dead entity cannot act"
    assert entity.is_player, "Npcs cannot give an item"
    assert item.quantity.val > 0, "Item quantity cannot be 0"  # indicates item leak

    config = realm.config
    if not config.ITEM_SYSTEM_ENABLED:
        return

    if not (target.is_player and target.alive):
        return

    if item not in entity.inventory:
        return

    # cannot give the equipped or listed item
    if item.equipped.val or item.listed_price.val:
        return

    if entity.in_combat:  # player cannot give item during combat
        return

    if not (
        config.ITEM_ALLOW_GIFT
        and entity.ent_id != target.ent_id  # but not self
        and target.is_player
    ):
        return

    # NOTE: allow give within the visual range
    if utils.linf_single(entity.pos, target.pos) > config.PLAYER_VISION_RADIUS:
        return

    if not target.inventory.space:
        # receiver inventory is full - see if it has an ammo stack with the same sig
        if isinstance(item, Stack):
            if not target.inventory.has_stack(item.signature):
                # no ammo stack with the same signature, so cannot give
                return
        else:  # no space, and item is not ammo stack, so cannot give
            return

    entity.inventory.remove(item)
    target.inventory.receive(item)
    # 这里增加了对给予者、被给予者的记录字段
    realm.event_log.record(EventCode.GIVE_ITEM, entity, item=item, target=target)


def _new_record(self, event_code: int, entity, **kwargs):
    if (
        event_code == EventCode.GIVE_ITEM
        and "item" in kwargs
        and isinstance(kwargs["item"], Item)
        and "target" in kwargs
        and isinstance(kwargs["target"], Entity)
    ):
        item = kwargs["item"]
        log = self._create_event(entity, event_code)
        log.type.update(item.ITEM_TYPE_ID)
        log.level.update(item.level.val)
        log.number.update(item.quantity.val)
        log.target_ent.update(kwargs["target"].ent_id)
        return
    return original_record(self, event_code, entity, **kwargs)


def apply_event_record_support():
    nmmo.systems.combat.attack = _new_attack
    nmmo.lib.event_log.EventLogger.record = _new_record
    nmmo.core.action.Give.call = _new_give_call
