import random
import structlog

from settlers.engine.components import Component
from settlers.engine.components.construction import (
    ConstructionWorker
)
from settlers.engine.components.factory import (
    FactoryWorker
)
from settlers.engine.components.harvesting import (
    Harvester, STATE_FULL as HARVESTER_STATE_FULL
)
from settlers.engine.components.movement import (
    ResourceTransport
)
from settlers.engine.components.worker import Worker as _Worker

from settlers.entities.buildings import Building

STATE_IDLE = 'idle'
STATE_BUSY = 'busy'

logger = structlog.get_logger('game.villager_ai')


class VillagerAi(Component):
    __slots__ = ['_available_tasks', 'state', 'task']

    def __init__(self, owner):
        super().__init__(owner)
        self.state = STATE_IDLE
        self.task = None
        self._available_tasks = []

    def available_tasks(self, supported_tasks):
        if self._available_tasks:
            return self._available_tasks

        for task in supported_tasks:
            if task in self.owner.components.classes():
                self._available_tasks.append(task)

        return self._available_tasks

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
            ConstructionWorker,
            FactoryWorker,
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

                    wants = entity.inventory.wants_resources()
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
        available_tasks = villager.available_tasks(self.tasks)

        if not available_tasks:
            return None

        return random.choice(available_tasks)

    def target_for_task(self, task):
        target_components = task.target_components()

        if not target_components:
            return None

        for entity in self.entities:
            intersection = target_components.intersection(
                entity.components.classes()
            )
            if intersection:
                targets = list(intersection)
                random.shuffle(intersection)

                for target_component in targets:
                    proxy = getattr(entity, target_component.exposed_as)
                    if proxy.can_add_worker():
                        return proxy.reveal()

    def __repr__(self):
        return "<{self} {id}>".format(
            self=self.__class__.__name__,
            id=hex(id(self)),
        )
