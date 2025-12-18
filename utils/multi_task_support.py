import nmmo
from nmmo.lib import spawn
from nmmo.lib import event_code


# nmmo.env.Env._map_task_to_agent
def _new_map_task_to_agent(self):
    self.agent_task_map.clear()
    for agent_id in self.agents:
        self.realm.players[agent_id].my_task = None
    for task in self.tasks:
        if task.embedding is None:
            task.set_embedding(self._dummy_task_embedding)
        # map task to agents
        for agent_id in task.assignee:
            if agent_id in self.agent_task_map:
                self.agent_task_map[agent_id].append(task)
            else:
                self.agent_task_map[agent_id] = [task]
    # print(self.agent_task_map)
    # for now we only support one task per agent
    # That’s no longer the case
    if not self.config.ALLOW_MULTI_TASKS_PER_AGENT:
        for agent_id, agent_tasks in self.agent_task_map.items():
            assert len(agent_tasks) == 1, "Only one task per agent is supported"
            self.realm.players[agent_id].my_task = agent_tasks[0]
    else:
        for agent_id, agent_tasks in self.agent_task_map.items():
            self.realm.players[agent_id].my_task = agent_tasks


# nmmo.entity.player.Player.resurrect
def _new_resurrect(self, health_prop=0.5, freeze_duration=10, edge_spawn=True):
    # Respawn dead players at the edge
    assert not self.alive, "Player is not dead"
    self.status.freeze.update(freeze_duration)
    self.resources.health.update(self.config.PLAYER_BASE_HEALTH * health_prop)
    if self.config.RESOURCE_SYSTEM_ENABLED:
        self.resources.water.update(self.config.RESOURCE_BASE)
        self.resources.food.update(self.config.RESOURCE_BASE)

    if edge_spawn:
        new_spawn_pos = spawn.get_random_coord(self.config, self._np_random, edge=True)
    else:
        while True:
            new_spawn_pos = spawn.get_random_coord(
                self.config, self._np_random, edge=False
            )
            if self.realm.map.tiles[new_spawn_pos].habitable:
                break

    self.set_pos(*new_spawn_pos)
    self.message.update(0)
    self.realm.players.spawn_entity(self)  # put back to the system
    self._set_immortal(duration=freeze_duration)
    # if self.my_task and len(self.my_task.assignee) == 1:
    #     # NOTE: Only one task per agent is supported for now
    #     # Agent's task progress need to be reset ONLY IF the task is an agent task
    #     self.my_task.reset()
    if self.my_task:
        if isinstance(self.my_task, list):
            for task in self.my_task:
                task.reset()
        else:
            self.my_task.reset()


# nmmo.core.tile.Tile.update_seize
def _new_update_seize(self):
    if len(self.entities) != 1:  # only one entity can seize a tile
        return
    ent_id, entity = list(self.entities.items())[0]
    if ent_id < 0:  # not counting npcs
        return
    team_members = entity.my_task[0].assignee  # NOTE: only one task per player
    if self.seize_history and self.seize_history[-1][0] in team_members:
        # no need to add another entry if the last entry is from the same team (incl. self)
        return
    self.seize_history.append((ent_id, self.realm.tick))
    if self.realm.event_log:
        self.realm.event_log.record(
            event_code.EventCode.SEIZE_TILE, entity, tile=self.pos
        )


# nmmo.render.Render.reset
def _new_reset(self):
    self.packets = []
    self.map = None
    self._i = 0
    self.update()  # to capture the initial packet
    self._agent_task = {
        agent_id: {f"task_{i}": task.name for i, task in enumerate(agent.my_task)}
        for agent_id, agent in self._realm.players.items()
    }


def apply_multi_task_support():
    nmmo.core.env.Env._map_task_to_agent = _new_map_task_to_agent
    nmmo.entity.player.Player.resurrect = _new_resurrect
    nmmo.core.tile.Tile.update_seize = _new_update_seize
    nmmo.render.replay_helper.FileReplayHelper.reset = _new_reset