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

    def __repr__(self):
        return "<{self} {id}>".format(
            self=self.__class__.__name__,
            id=hex(id(self))
        )


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
            if villager.state == STATE_BUSY:
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
                print(
                    "{owner}#{self} no target for task {task}".format(
                        self=villager,
                        owner=villager.owner,
                        task=task,
                    )
                )
                continue

            component = getattr(villager.owner, task.exposed_as)
            if component.start(target):
                component.on_end(villager.on_task_ended)
                villager.task = task
                villager.state_change(STATE_BUSY)
            else:
                print(
                    "{self}#{villager} could not start"
                    " {task} at {target}".format(
                        self=self,
                        villager=villager,
                        task=task,
                        target=target,
                    )
                )

    def select_task(self, villager):
        available_tasks = self.available_tasks_for(villager)

        if not available_tasks:
            return None

        return random.choice(available_tasks)

    def target_for_task(self, task):
        target_components = set(task.target_components())

        for entity in self.entities:
            intersection = list(target_components.intersection(
                entity.components.classes()
            ))
            if intersection:
                random.shuffle(intersection)
                proxy = getattr(entity, intersection[0].exposed_as)
                if proxy.can_add_worker():
                    return proxy.reveal()

    def available_tasks_for(self, villager):
        tasks = []
        for component in self.tasks:
            if component in villager.owner.components.classes():
                tasks.append(component)
        return tasks

    def __repr__(self):
        return "<{self} {id}>".format(
            self=self.__class__.__name__,
            id=hex(id(self)),
        )
