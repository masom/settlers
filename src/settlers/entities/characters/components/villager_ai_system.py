import random
import structlog
from typing import List

from settlers.engine.components import Component, ComponentManager
from settlers.engine.components.construction import (
    Construction, ConstructionWorker
)
from settlers.engine.components.factory import (
    Factory, FactoryWorker
)
from settlers.engine.components.harvesting import (
    Harvester,
    STATE_FULL as HARVESTER_STATE_FULL,
    STATE_DELIVERING as HARVESTER_STATE_DELIVERING
)
from settlers.engine.components.inventory_routing import (
    InventoryRouting
)
from settlers.engine.components.movement import (
    ResourceTransport
)

from settlers.entities.buildings import Building

STATE_IDLE = 'idle'
STATE_BUSY = 'busy'

logger = structlog.get_logger('game.villager_ai')


class VillagerAi(Component):
    __slots__ = ('_available_tasks', 'state', 'task')

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

    def on_task_ended(self, component: Component) -> None:
        logger.info('on_task_ended', component=component)
        self.task = None
        self.state_change(STATE_IDLE)

    def state_change(self, new_state: str) -> None:
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

    def __repr__(self) -> str:
        return "<{self} {id}>".format(
            self=self.__class__.__name__,
            id=hex(id(self))
        )


class VillagerAiSystem:
    component_types = [VillagerAi]

    def __init__(self, world: object) -> None:
        self.tasks = [
            Harvester,
            ConstructionWorker,
            FactoryWorker,
        ]

        self.entities = world.entities

    def handle_busy_harvester(self, villager: VillagerAi) -> None:
        proxy = getattr(villager.owner, Harvester.exposed_as)
        harvester: Harvester = proxy.reveal(Harvester)

        if not harvester.state == HARVESTER_STATE_FULL:
            return

        possible_destinations: List[Building] = []

        locations: List[InventoryRouting] = ComponentManager[InventoryRouting]

        for location in locations:
            entity: Building = location.owner
            wants: set = entity.inventory.wants_resources()
            common: set = harvester.resources.intersection(wants)
            if not common:
                continue

            possible_destinations.append(entity)

        if not possible_destinations:
            logger.debug(
                'handle_busy_villager_harvester_destination_selection',
                owner=villager.owner,
                system=self.__class__.__name__,
                possible_destinations=possible_destinations,
            )
            return

        destination = random.choice(possible_destinations)
        harvester.assign_destination(destination)
        harvester.owner.travel.stop()
        harvester.state_change(HARVESTER_STATE_DELIVERING)

    def handle_busy_villager(self, villager: VillagerAi) -> None:
        if villager.task == Harvester:
            self.handle_busy_harvester(villager)

    def handle_idle_villager(self, villager: VillagerAi) -> None:
        if not hasattr(villager.owner, 'resource_transport'):
            import pdb; pdb.set_trace()
            return

        options = [self.resource_transport_for_villager]
        task = random.choice(options)
        task(villager)

    def resource_transport_for_villager(self, villager: VillagerAi) -> None:
        factories: List[Factory] = ComponentManager[Factory]

        for factory in random.sample(factories, len(factories)):
            source: Building = factory.owner

            available_for_transport = (
                source
                .inventory
                .available_for_transport()
            )

            if not available_for_transport:
                continue

            destination = self._find_destination_for_transport(
                available_for_transport
            )

            if not destination:
                continue

            logger.debug(
                'process_component_accepted',
                system=self.__class__.__name__,
                task=ResourceTransport,
                target=destination,
                villager=villager.owner,
                valid_route=villager.owner.resource_transport.is_valid_route(
                    destination
                ),
            )

            villager.owner.resource_transport.on_end(villager.on_task_ended)
            villager.task = ResourceTransport
            villager.state_change(STATE_BUSY)
            villager.owner.resource_transport.start(destination, source)
            return

    def _find_destination_for_transport(self, resource) -> Building:
        destinations_by_priority = {
            'high': [],
            'normal': [],
            'low': [],
        }

        locations: List[InventoryRouting] = ComponentManager[InventoryRouting]

        for location in locations:
            destination: Building = location.owner
            wants: set = destination.inventory.wants_resources()
            if not wants:
                continue

            if resource not in wants:
                continue

            if hasattr(destination, Construction.exposed_as):
                destinations_by_priority['high'].append(
                    destination
                )
                continue
            if hasattr(destination, Factory.exposed_as):
                destinations_by_priority['normal'].append(
                    destination
                )
                continue

            destinations_by_priority['low'].append(destination)

        for priority, destinations in destinations_by_priority.items():
            if not destinations:
                continue

            return destinations[0]

    def process(self, villagers: List[VillagerAi]) -> None:
        for villager in villagers:
            if villager.state == STATE_BUSY:
                self.handle_busy_villager(villager)
                continue

            task = self.select_task(villager)
            if not task:
                self.handle_idle_villager(villager)
                continue

            target = self.target_for_task(task)
            if not target:
                self.handle_idle_villager(villager)
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
                logger.debug(
                    'process_component_rejected',
                    system=self.__class__.__name__,
                    task=task,
                    target=target,
                    villager=villager.owner,
                )
                self.handle_idle_villager(villager)

    def select_task(self, villager: VillagerAi):
        available_tasks: list = villager.available_tasks(self.tasks)

        if not available_tasks:
            return None

        return random.choice(available_tasks)

    def target_for_task(self, task):
        target_components = task.target_components()

        if not target_components:
            return None

        entities: list = ComponentManager.entities_matching(target_components)
        for entity, components in entities:
            targets = list(components)
            random.shuffle(targets)

            for target_component in targets:
                proxy = getattr(entity, target_component.exposed_as)
                if proxy.can_add_worker():
                    return proxy.reveal(target_component.__class__)

    def __repr__(self) -> str:
        return "<{self} {id}>".format(
            self=self.__class__.__name__,
            id=hex(id(self)),
        )
