import random
import structlog
from collections import defaultdict
from typing import Callable, List, Optional

from settlers.engine.components import (
    Component, ComponentProxy, ComponentManager
)
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
from settlers.engine.components.spawner import (
    SpawnerWorker,
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

    def available_tasks(self, supported_tasks: list[Component]):
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
        self.tasks: List[Component] = [
            Harvester,
            ConstructionWorker,
            FactoryWorker,
            SpawnerWorker,
        ]

        self.entities = world.entities
        self._awaiting_until: dict = {}

    def handle_busy_harvester(self, villager: VillagerAi) -> None:
        proxy: ComponentProxy = getattr(villager.owner, Harvester.exposed_as)
        harvester: Harvester = proxy.reveal(Harvester)

        if not harvester.state == HARVESTER_STATE_FULL:
            return

        awaiting = self._awaiting_until.get(villager, 0)
        if awaiting > self.current_tick:
            return

        possible_destinations: List[Building] = []

        locations: List[InventoryRouting] = ComponentManager[InventoryRouting]

        for location in locations:
            entity: Building = location.owner
            wants: set = entity.inventory.wants_resources()
            common: set = harvester.resources.intersection(wants)
            if not common:
                """
                    logger.debug(
                    'handle_busy_harvester:no_common_resources',
                    owner=villager.owner,
                    system=self.__class__.__name__,
                    entity=entity,
                    provides=harvester.resources,
                    wants=wants,
                    common=common,
                )
                """
                continue

            possible_destinations.append(entity)

        if not possible_destinations:
            logger.debug(
                'handle_busy_harvester:destination_selection_empty',
                owner=villager.owner,
                system=self.__class__.__name__,
                provides=harvester.resources,
            )

            self._awaiting_until[villager] = self.current_tick + 10000
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
            return

        options: List[Callable] = [
            self.resource_transport_for_villager
        ]
        task: Callable = random.choice(options)

        task(villager)

    '''
    Find a random factory and check if it has resources available for transport.
    '''
    def resource_transport_for_villager(self, villager: VillagerAi) -> None:
        factories: List[Factory] = ComponentManager[Factory]

        # Sample will return len(factories) elements in random order
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
                source,
                available_for_transport
            )

            if not destination:
                continue

            # TODO this is a hack to automatically setup the transport inventory for routing
            if isinstance(villager.owner.storages, defaultdict):
                wants: set[type] = destination.inventory.wants_resources()

                for want in wants:
                    villager.owner.storages[want]

            logger.debug(
                'resource_transport_for_villager:process_component_accepted',
                system=self.__class__.__name__,
                task=ResourceTransport,
                target=destination,
                source=source,
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

    def _find_destination_for_transport(self, origin: Building, resource: type) -> Building:
        destinations_by_priority: dict[str, list[Building]] = {
            'high': [],
            'normal': [],
            'low': [],
        }

        locations: List[InventoryRouting] = ComponentManager[InventoryRouting]

        for location in locations:
            destination: Building = location.owner
            if origin == destination:
                continue

            wants: set[type] = destination.inventory.wants_resources()

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

            destination = random.choice(destinations)
            logger.info(
                '_find_destination_for_transport',
                origin=origin,
                destination=destination,
                system=self.__class__.__name__,
                resource=resource,
                priority=priority
            )
            return destination

    def process(self, tick: int, villagers: List[VillagerAi]) -> None:
        self.current_tick = tick

        if self.current_tick % 10 == 0:
            logger.debug(
                'process',
                system=self.__class__.__name__,
                tick=self.current_tick,
                villagers=len(villagers),
            )

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

            component: Component = getattr(villager.owner, task.exposed_as)
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

    def select_task(self, villager: VillagerAi) -> Optional[Component]:
        available_tasks: List[Component] = villager.available_tasks(self.tasks)

        if not available_tasks:
            logger.debug(
                'select_task:no_tasks',
                system=self.__class__.__name__,
                villager=villager.owner,
            )
            return None

        return random.choice(available_tasks)

    def target_for_task(self, task: Component):
        target_components: List[Component] = task.target_components()

        if not target_components:
            return None

        entities: List[tuple] = ComponentManager.entities_matching(
            target_components
        )

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
