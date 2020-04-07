import random
import structlog

from settlers.engine.components import Component
from settlers.engine.components.factory import (
    Worker
)
from settlers.engine.components.harvesting import (
    Harvester, STATE_FULL as HARVESTER_STATE_FULL
)
from settlers.entities.buildings import Building

STATE_IDLE = 'idle'
STATE_BUSY = 'busy'

logger = structlog.get_logger('game.villager_ai')


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

        logger.debug(
            'state_change',
            owner=self.owner,
            component=self,
            old_state=self.state,
            new_state=new_state,
            task=self.task,
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

    def handle_busy_villager(self, villager):
        if villager.task == Harvester:
            proxy = getattr(villager.owner, Harvester.exposed_as)

            harvester = proxy.reveal()

            if harvester.state == HARVESTER_STATE_FULL:
                if harvester.destination:
                    return

                logger.debug(
                    'handle_busy_villager_harvester_destination_selection',
                    owner=villager.owner,
                    system=self.__class__.__name__,
                )

                for entity in self.entities:
                    if not isinstance(entity, Building):
                        continue

                    wants = entity.wants_resources()
                    common = harvester.resources.intersection(wants)
                    if not common:
                        continue

                    harvester.assign_destination(entity)

                    return True

        return False

    def process(self, villagers):
        for villager in villagers:
            if villager.state == STATE_BUSY:
                self.handle_busy_villager(villager)
                continue

            task = self.select_task(villager)
            if not task:
                continue

            target = self.target_for_task(task)
            if not target:
                continue

            component = getattr(villager.owner, task.exposed_as)
            if component.start(target):
                logger.debug(
                    'process_component_accepted',
                    system=self.__class__.__name__,
                    task=task,
                    target=target,
                    villager=villager.owner,
                )

                component.on_end(villager.on_task_ended)
                villager.task = task
                villager.state_change(STATE_BUSY)
            else:
                logger.info(
                    'process_component_rejected',
                    system=self.__class__.__name__,
                    task=task,
                    target=target,
                    villager=villager.owner,
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
