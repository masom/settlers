import random
import structlog
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple, Type

from settlers.engine.components import Component, ComponentManager
from settlers.engine.components.construction import Construction, ConstructionWorker
from settlers.engine.components.factory import Factory, FactoryWorker
from settlers.engine.components.harvesting import (
    Harvestable,
    Harvester,
    STATE_FULL as HARVESTER_STATE_FULL,
    STATE_DELIVERING as HARVESTER_STATE_DELIVERING,
)
from settlers.engine.components.spawner import (
    Spawner,
    SpawnerWorker,
)
from settlers.engine.components.inventory_routing import InventoryRouting
from settlers.engine.components.movement import ResourceTransport, Travel

from settlers.entities.buildings import Building
from settlers.entities.characters.villager import Villager
from settlers.engine.entities.entity import Entity
from settlers.entities.renderable import (
    Renderable,
    label_cache as RenderableLabelCache,
    LABEL_TASK as RENDERABLE_LABEL_TASK,
    LABEL_COLOR_TASK as RENDERABLE_LABEL_COLOR_TASK,
    LABEL_POSITION_BOTTOM as RENDERABLE_LABEL_POSITION_BOTTOM,
)

STATE_IDLE = "idle"
STATE_BUSY = "busy"

logger = structlog.get_logger("game.villager_ai")


class VillagerAi(Component):
    __slots__ = ("_available_tasks", "state", "task")

    def __init__(self, owner) -> None:
        super().__init__(owner)
        self.state: str = STATE_IDLE
        self.task: Optional[Type[Component]] = None
        self._available_tasks: List[Type[Component]] = []

    def available_tasks(
        self, supported_tasks: list[Component]
    ) -> List[Type[Component]]:
        if self._available_tasks:
            return self._available_tasks

        owner_classes = self.owner.components.classes()

        for task in supported_tasks:
            if task in owner_classes:
                self._available_tasks.append(task)

        return self._available_tasks

    def on_task_assigned(self, task: type[Component]) -> None:
        logger.debug("on_task_assigned", task=task, owner_id=self.owner_id())

        self.task = task
        self.state_change(STATE_BUSY)

        renderable = ComponentManager.fetch_optional(self.owner_id(), Renderable)
        if not renderable:
            return

        label = RenderableLabelCache.get(
            RENDERABLE_LABEL_TASK,
            f"A:{self.task.__name__}",
            RENDERABLE_LABEL_COLOR_TASK,
            position=RENDERABLE_LABEL_POSITION_BOTTOM,
        )

        renderable.add_label(label)

    def on_task_started(self) -> None:
        logger.info("on_task_started", component=self.task, owner_id=self.owner_id())

        renderable = ComponentManager.fetch_optional(self.owner_id(), Renderable)
        if not renderable:
            return

        label = RenderableLabelCache.get(
            RENDERABLE_LABEL_TASK,
            f"S:{self.task.__name__}",
            RENDERABLE_LABEL_COLOR_TASK,
        )
        renderable.add_label(label)

    def on_task_ended(self, component=None) -> None:
        logger.info("on_task_ended", task=self.task)
        self.task = None
        self.state_change(STATE_IDLE)

        renderable = ComponentManager.fetch_optional(self.owner_id(), Renderable)
        if not renderable:
            return

        renderable.remove_label(RENDERABLE_LABEL_TASK)

    def state_change(self, new_state: str) -> None:
        if self.state == new_state:
            return

        logger.debug(
            "state_change",
            owner=self.owner,
            component=self,
            old_state=self.state,
            new_state=new_state,
            task=self.task,
        )

        self.state = new_state

    def __repr__(self) -> str:
        return "<{self} {id}>".format(self=self.__class__.__name__, id=hex(id(self)))


class VillagerAiSystem:
    component_types = (VillagerAi,)

    def __init__(self) -> None:
        self.tasks: List[Type[Component]] = [
            Harvester,
            ConstructionWorker,
            FactoryWorker,
            SpawnerWorker,
        ]

        self._awaiting_until: Dict[VillagerAi, int] = {}

    def on_entity_spawn(self, entity: Entity) -> None:
        if isinstance(entity, Villager):
            entity.components.add(VillagerAi)

            self._allocate_jobs_to_villager(entity)

    def _allocate_jobs_to_villager(self, villager: Villager):
        workers: dict[type, int] = {}
        sum: int = 1
        current: int = 0

        for task in self.tasks:
            current = len(ComponentManager[task])
            workers[task] = current
            sum += current

        if not ResourceTransport in villager.components.component_classes:
            villager.components.add(ResourceTransport)

        # TODO: Assign a subset of tasks when game is running for specialization
        if workers[Harvester] < len(ComponentManager[Harvestable]):
            proportion = 100 * float(workers[Harvester]) / float(sum)
            if proportion < 0.3:
                logger.debug(
                    proportion=proportion,
                    assigned_task=Harvester,
                    villager=villager,
                )

                villager.components.add((Harvester, [], villager.storages))
                return

        if workers[SpawnerWorker] < len(ComponentManager[Spawner]):
            villager.components.add(SpawnerWorker)
            return

        if workers[FactoryWorker] < len(ComponentManager[Factory]):
            villager.components.add(FactoryWorker)
            return

        return

    def handle_busy_harvester(self, villager: VillagerAi) -> None:
        harvester: Harvester = ComponentManager.fetch(villager.owner_id(), Harvester)

        if not harvester.state == HARVESTER_STATE_FULL:
            return

        awaiting = self._awaiting_until.get(villager.owner_id(), 0)
        if awaiting > self.current_tick:
            return

        possible_destinations: List[Building] = []

        locations: List[InventoryRouting] = ComponentManager[InventoryRouting]

        random.shuffle(locations)

        for location in locations:
            target_building: Building = location.owner
            wants: list = location.wants_resources()
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

            possible_destinations.append(target_building)

        if not possible_destinations:
            logger.debug(
                "handle_busy_harvester:destination_selection_empty",
                owner=villager.owner,
                system=self.__class__.__name__,
                provides=harvester.resources,
            )

            self._awaiting_until[villager] = self.current_tick + 10000
            return

        destination = random.choice(possible_destinations)

        travel: Travel = ComponentManager.fetch(harvester.owner_id(), Travel)
        travel.stop()

        harvester.assign_destination(destination)
        harvester.state_change(HARVESTER_STATE_DELIVERING)

    def handle_busy_villager(self, villager: VillagerAi) -> None:
        if villager.task == Harvester:
            self.handle_busy_harvester(villager)

    def handle_idle_villager(self, villager: VillagerAi) -> None:
        resource_transport: Optional[ResourceTransport] = (
            ComponentManager.fetch_optional(villager.owner_id(), ResourceTransport)
        )

        logger.debug(
            "handle_idle_villager",
            resource_transport_present=bool(resource_transport),
            villager=villager.owner_id(),
        )

        if not resource_transport:
            return

        # villager.on_task_assigned(ResourceTransport)
        # villager.on_task_started()

        options: List[Callable] = [self.resource_transport_for_villager]
        task: Callable = random.choice(options)

        task(villager)

    def resource_transport_for_villager(self, villager_ai: VillagerAi) -> None:
        """
        Find a random factory and check if it has resources available for transport.
        """

        factories: List[Factory] = ComponentManager[Factory]

        # Sample will return len(factories) elements in random order
        for factory in random.sample(factories, len(factories)):
            source: Building = factory.owner
            factory_inventory: InventoryRouting = ComponentManager.fetch(
                factory.owner_id(), InventoryRouting
            )

            available_for_transport = factory_inventory.available_for_transport()

            if not available_for_transport:
                continue

            destination = self._find_destination_for_transport(
                source, available_for_transport
            )

            if not destination:
                continue

            villager: Villager = villager_ai.owner

            # TODO this is a hack to automatically setup the transport inventory for routing
            if isinstance(villager.storages, defaultdict):
                destination_inventory: InventoryRouting = ComponentManager.fetch(
                    destination.id(), InventoryRouting
                )
                wants: set[type] = destination_inventory.wants_resources()

                for want in wants:
                    villager.storages[want]

            villager_resource_transport: ResourceTransport = ComponentManager.fetch(
                villager_ai.owner_id(), ResourceTransport
            )
            villager_resource_transport.on_end(villager_ai.on_task_ended)

            logger.debug(
                "resource_transport_for_villager:process_component_accepted",
                system=self.__class__.__name__,
                task=ResourceTransport,
                target=destination,
                source=source,
                villager=villager,
                valid_route=villager_resource_transport.is_valid_route(destination),
            )

            villager_ai.on_task_assigned(ResourceTransport)

            villager_resource_transport.start(destination, source)

            return

    def _find_destination_for_transport(
        self, origin: Building, resource: type
    ) -> Building:
        destinations_by_priority: dict[str, list[Building]] = {
            "high": [],
            "normal": [],
            "low": [],
        }

        locations: List[InventoryRouting] = ComponentManager[InventoryRouting]

        for location in locations:
            destination: Building = location.owner
            if origin == destination:
                continue

            destination_inventory: InventoryRouting = ComponentManager.fetch(
                location.owner_id(), InventoryRouting
            )

            wants: set[type] = destination_inventory.wants_resources()

            if not wants:
                continue

            if resource not in wants:
                continue

            construction = ComponentManager.fetch_optional(
                destination.id(), Construction
            )

            if construction:
                destinations_by_priority["high"].append(destination)
                continue

            factory = ComponentManager.fetch_optional(destination.id(), Factory)
            if factory:
                destinations_by_priority["normal"].append(destination)
                continue

            destinations_by_priority["low"].append(destination)

        for priority, destinations in destinations_by_priority.items():
            if not destinations:
                continue

            destination = random.choice(destinations)
            logger.info(
                "_find_destination_for_transport",
                origin=origin,
                destination=destination,
                system=self.__class__.__name__,
                resource=resource,
                priority=priority,
            )
            return destination
        return

    def process(self, tick: int, villagers: List[VillagerAi]) -> None:
        self.current_tick = tick

        if self.current_tick % 10 != 0:
            return

        for villager in villagers:
            if villager.state == STATE_BUSY:
                self.handle_busy_villager(villager)
                continue

            task = self.select_task(villager)
            if not task:
                self.handle_idle_villager(villager)
                continue

            villager.on_task_assigned(task)

            target = self.target_for_task(task)
            if not target:
                self.handle_idle_villager(villager)
                continue

            component = ComponentManager.fetch(villager.owner_id(), task)

            if component.start(target):
                logger.debug(
                    "process_component_accepted",
                    system=self.__class__.__name__,
                    task=task,
                    target=target,
                    villager=villager.owner,
                )

                component.on_end(villager.on_task_ended)
                villager.on_task_started()
            else:
                logger.debug(
                    "process_component_rejected",
                    system=self.__class__.__name__,
                    task=task,
                    target=target,
                    villager=villager.owner,
                )
                self.handle_idle_villager(villager)

    def select_task(self, villager: VillagerAi) -> Optional[Component]:
        available_tasks: List[Component] = villager.available_tasks(self.tasks)

        if not available_tasks:
            self._allocate_jobs_to_villager(villager.owner)

            logger.debug(
                "select_task:no_tasks",
                system=self.__class__.__name__,
                villager=villager.owner,
            )
            return None

        return random.choice(available_tasks)

    def target_for_task(self, task: Component) -> Optional[Component]:
        """
        Select an applicable target for a given task.

        The task object will contain a list of components the desired target should contain.

        Upon a match, it will return the applicable target.
        """

        # Grab the list of components the task requires the targets to have.
        target_components: List[Type[Component]] = task.target_components()

        if not target_components:
            logger.error("target_for_task:no_target_components", task=task.__class__)
            return None

        # List of entities containing the components require by the task
        target_entities: List[Tuple[int, List[Component]]] = (
            ComponentManager.entities_matching(target_components)
        )

        # TODO: A smarter target selection based on distance from the entity requesting this work.
        # TODO: Problem is we can allocate to items that don't have a sink, resulting in a game deadlock.
        # random.shuffle(target_entities)

        entity_id: int
        components: List[Component]

        # TODO: Target entities should be sorted by distance, favouring the closests

        for entity_id, components in target_entities:
            targets = list(components)

            # Randomize what you can do on the entity... why?
            # TODO Find why this shuffle was added
            random.shuffle(targets)

            for target_component in targets:
                target_entity = ComponentManager.fetch(
                    entity_id, target_component.__class__
                )
                if target_entity.can_add_worker():
                    return target_entity

    def __repr__(self) -> str:
        return "<{self} {id}>".format(
            self=self.__class__.__name__,
            id=hex(id(self)),
        )
