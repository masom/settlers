import random
from settlers.engine.components import Component
from settlers.engine.components.factory import (
    Worker
)
from settlers.engine.components.harvesting import (
    Harvester
)

STATE_IDLE = 'idle'
STATE_BUSY = 'busy'


class VillagerAi(Component):
    __slots__ = ['state', 'task']

    def __init__(self, owner):
        super().__init__(owner)
        self.state = STATE_IDLE
        self.task = None

    def on_task_ended(self, component):
        self.task = None
        self.state_change(STATE_IDLE)

    def state_change(self, new_state):
        if self.state == new_state:
            return

        print(
            "{owner}#{component} state change:"
            " {old_state} -> {new_state}, task: {task}".format(
                owner=self.owner,
                component=self,
                old_state=self.state,
                new_state=new_state,
                task=self.task,
            )
        )

        self.state = new_state


class VillagerAiSystem:

    component_types = set([VillagerAi])

    def __init__(self, world):
        self.tasks = [
            Harvester,
            Worker,
        ]

        self.entities = world.entities

    def process(self, villagers):
        for villager in villagers:
            if not villager.state == STATE_IDLE:
                continue

            task = self.select_task(villager)
            if not task:
                print(
                    "{self} No tasks for {villager}".format(
                        self=self,
                        villager=villager
                    )
                )
                continue

            target = self.target_for_task(task)
            if not target:
                return

            component = getattr(villager.owner, task.exposed_as)
            if component.start(target):
                component.on_end(villager.on_task_ended)
                villager.task = task
                villager.state_change(STATE_BUSY)

    def select_task(self, villager):
        available_tasks = self.available_tasks_for(villager)

        if not available_tasks:
            return None

        return random.choice(available_tasks)

    def target_for_task(self, task):
        for entity in self.entities:
            target_components = task.target_components()
            random.shuffle(target_components)

            for target_component in target_components:
                if target_component in entity.components.classes():
                    proxy = getattr(entity, target_component.exposed_as)
                    return proxy.reveal()

    def available_tasks_for(self, villager):
        tasks = []
        for component in self.tasks:
            if component in villager.owner.components.classes():
                tasks.append(component)
        return tasks
