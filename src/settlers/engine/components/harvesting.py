import structlog
from typing import Callable, List, Optional, Set, Tuple, Type
import weakref
import inspect

from settlers.engine.entities.entity import Entity
from settlers.engine.entities.position import Position
from settlers.engine.components.inventory_routing import InventoryRouting

from . import Component, ComponentManager
from .movement import Travel

from settlers.engine.entities.resources import Resource
from settlers.engine.entities.resources.resource_storage import ResourceStorage


STATE_DELIVERING = "delivering"
STATE_HARVESTING = "harvesting"
STATE_IDLE = "idle"
STATE_FULL = "full"


logger = structlog.get_logger("harvesting")


class Harvester(Component):
    __slots__ = (
        "destination",
        "on_end_callbacks",
        "_resources",
        "resources",
        "state",
        "storage",
        "source",
        "ticks",
    )

    _target_components: List[Type[Component]] = []

    def __init__(
        self,
        owner,
        resources: List[Type[Resource]],
        storage: dict[Type[Resource], ResourceStorage],
    ):
        super().__init__(owner)

        self.destination: Optional[weakref.ReferenceType[Entity]] = None
        self.on_end_callbacks: List[Callable] = []
        self.state = STATE_IDLE
        self._resources: Set[Type[Resource]] = set(resources)
        self.storage: ResourceStorage = storage
        self.source: Optional[weakref.ReferenceType[Entity]] = None
        self.ticks = 0

        self.update_resources()

    def assign_destination(self, building: Entity) -> None:
        self.destination = weakref.ref(building)

    def update_resources(self) -> None:
        if self._resources:
            self.resources = self._resources
        else:
            self.resources = set(self.storage.keys())

    """
    Determines if a worker can harvest a given resource by looking at the resource storage state
    """

    def can_harvest(self, resource: Type[Resource]) -> bool:
        if len(self._resources) > 0 and resource not in self._resources:
            logger.debug(
                "cannot_harvest",
                component=self.__class__.__name__,
                owner=self.owner,
                resource=resource,
            )
            return False

        if self.storage[resource].is_full():
            return False

        return True

    def deliver(self) -> None:
        self.state_change(STATE_IDLE)

        if not self.destination:
            raise RuntimeError("no destination")

        destination = self.destination()

        if not destination:
            raise RuntimeError("destination is dead")

        destination_position: Position = ComponentManager.fetch(
            destination.id(), Position
        )
        my_position: Position = ComponentManager.fetch(self.owner_id(), Position)

        if not destination_position == my_position:
            raise RuntimeError("not yet at destination")

        delivered: List[Type[Resource]] = []
        kept: List[Type[Resource]] = []

        resource_type: Type[Resource]
        output_storage: ResourceStorage

        destination_inventory: InventoryRouting = ComponentManager.fetch(
            destination.id(), InventoryRouting
        )
        for resource_type, output_storage in self.storage.items():
            input_storage: ResourceStorage = destination_inventory.storage_for(
                resource_type
            )

            if not input_storage:
                kept.append(resource_type)
                continue

            if input_storage.add(resource_type):
                delivered.append(resource_type)
                output_storage.pop()
            else:
                kept.append(resource_type)
                logger.info(
                    "cannot deliver",
                    component=self.__class__.__name__,
                    owner=self.owner,
                    destination=destination,
                    destination_storage=input_storage,
                )
        if not delivered:
            self.destination = None

        logger.info(
            "delivered",
            owner=self.owner,
            component=self.__class__.__name__,
            delivered=delivered,
            destination=destination,
            kept=kept,
        )

    def inventory_available_for(self, resource: type) -> bool:
        return self.storage[resource].available() > 0

    def on_end(self, callback: Callable) -> None:
        self.on_end_callbacks.append(callback)

    def receive_harvest(self, harvest: List[Type[Resource]]) -> None:
        collected = 0

        for resource in harvest:
            added: bool = self.storage[resource].add(resource)
            if added:
                collected += 1
            else:
                raise RuntimeError("full...")

        if not self._resources:
            self.update_resources()

        logger.info(
            "receive_harvest",
            collected=collected,
            total=len(harvest),
            harvest=harvest,
            component=self.__class__.__name__,
            owner=self.owner,
        )

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            component=self.__class__.__name__,
            owner=self.owner,
            id=hex(id(self)),
        )

    def start(self, source) -> bool:
        if self.source:
            raise RuntimeError("already assigned")

        if not source.can_add_worker():
            logger.debug(
                "start_source_rejected",
                source=source,
                component=self.__class__.__name__,
                owner=self.owner,
            )
            return False

        logger.debug(
            "start_requested",
            source=source,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.source = weakref.ref(source)
        return source.add_worker(self)

    def state_change(self, new_state: str) -> None:
        if self.state == new_state:
            return

        logger.debug(
            "state_change",
            old_state=self.state,
            new_state=new_state,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.state = new_state

    def stop(self, skip_idle_state=False) -> None:
        if not skip_idle_state:
            self.state_change(STATE_IDLE)

        for callback in self.on_end_callbacks:
            callback(self)

        if self.source:
            source = self.source()
            if source:
                source.remove_worker(self)

            self.source = None

        if self.destination:
            self.destination = None

        logger.info(
            "stop",
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.on_end_callbacks = []

    @classmethod
    def target_components(cls):
        if not cls._target_components:
            cls._target_components.append(Harvestable)
        return cls._target_components


class Harvestable(Component):
    __slots__ = (
        "workers",
        "harvest_value_per_cycle",
        "max_workers",
        "output",
        "target_attr",
        "ticks_per_cycle",
    )

    exposed_as = "harvesting"
    exposed_methods = (
        "add_worker",
        "can_add_worker",
        "output",
        "provides",
        "remove_worker",
    )

    def __init__(
        self,
        owner,
        target_attr: str,
        output: type,
        ticks_per_cycle: int,
        harvest_value_per_cycle: int,
        max_workers: int,
    ):
        super().__init__(owner)

        self.workers: List[weakref.ReferenceType[Harvester]] = []
        self.harvest_value_per_cycle: int = harvest_value_per_cycle
        self.max_workers: int = max_workers
        self.output: type = output
        self.target_attr: str = target_attr
        self.ticks_per_cycle: int = ticks_per_cycle

    def add_worker(self, worker: Harvester) -> bool:
        if len(self.workers) > self.max_workers:
            return False

        logger.debug(
            "add_worker",
            owner=self.owner,
            component=self.__class__.__name__,
            worker=worker,
        )

        worker_ref = weakref.ref(worker)
        self.workers.append(worker_ref)
        return True

    def can_add_worker(self) -> bool:
        return len(self.workers) < self.max_workers

    def harvestable_quantity(self) -> int:
        return int(getattr(self.owner, self.target_attr))

    def harvested_quantity(self, quantity: int) -> None:
        value = max(0, self.harvestable_quantity() - quantity)

        logger.debug(
            "harvested_quantity",
            owner=self.owner,
            component=self.__class__.__name__,
            harvested_quantity=quantity,
            new_value=value,
        )

        setattr(self.owner, self.target_attr, value)

    def provides(self) -> type:
        return self.output

    def remove_worker(self, entity: Harvester) -> bool:
        for worker in self.workers:
            if worker.worker() == entity:
                logger.debug(
                    "remove_worker",
                    worker=entity,
                    owner=self.owner,
                    component=self.__class__.__name__,
                )
                self.workers.remove(worker)
                return True
        return False

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner, component=self.__class__.__name__, id=hex(id(self))
        )


class HarvesterSystem:
    component_types: Tuple[Type[Harvester], Type[Travel]] = (Harvester, Travel)

    def __init__(self) -> None:
        self._awaiting_until: dict[Harvester, int] = {}

    def process(self, tick: int, workers: List[List[Component]]) -> None:
        self._current_tick = tick

        worker: Harvester
        worker_travel: Travel

        for worker, worker_travel in workers:  # type: ignore
            if worker.state == STATE_IDLE:
                if not worker.source:
                    continue
                worker.state_change(STATE_HARVESTING)
                continue

            if worker.state == STATE_HARVESTING:
                self.handle_harvesting(worker, worker_travel)
                continue

            if worker.state == STATE_FULL:
                self.handle_delivery(worker, worker_travel)
                continue

            if worker.state == STATE_DELIVERING:
                self.handle_delivery(worker, worker_travel)

    def handle_delivery(self, worker: Harvester, worker_travel: Travel) -> None:
        awaiting = self._awaiting_until.get(worker, 0)
        if awaiting > self._current_tick:
            return

        if not worker.destination:
            source = worker.source() if worker.source else None

            logger.debug(
                "handle_delivery:no_destination",
                system=self.__class__.__name__,
                source=source or worker.source,
                worker=worker,
            )
            self._awaiting_until[worker] = self._current_tick + 1000
            return

        destination = worker.destination()
        if not destination:
            worker.stop()
            return

        destination_position = ComponentManager.fetch(destination.id(), Position)
        worker_position = ComponentManager.fetch(worker.owner_id(), Position)

        if destination_position == worker_position:
            worker.deliver()
            return

        if not worker_travel.destination:
            worker_travel.start(destination)
            return

        travel_destination: Optional[Entity] = worker_travel.destination()
        if not travel_destination:
            import pdb

            pdb.set_trace()
            return

        if not travel_destination.id() == destination.id():
            import pdb

            pdb.set_trace()
            return

    def handle_harvesting(self, worker: Harvester, worker_travel: Travel):
        if not worker.source:
            logger.debug(
                "handle_harvesting:no_source",
                system=self.__class__.__name__,
                worker=worker,
            )
            worker.stop()
            return

        source: Optional[Harvestable] = worker.source()

        if not source:
            logger.debug(
                "handle_harvesting:source_dead",
                system=self.__class__.__name__,
                source=worker.source,
                worker=worker,
            )
            worker.source = None
            worker.state_change(STATE_IDLE)
            return

        resource: Type[Resource] = source.output

        if worker.storage[resource].is_full():
            worker.state_change(STATE_FULL)
            return

        worker_position: Position = ComponentManager.fetch(worker.owner_id(), Position)
        source_position: Position = ComponentManager.fetch(source.owner_id(), Position)

        if not worker_position == source_position:
            destination_entity: Optional[Entity] = None

            if worker_travel.destination:
                destination_entity = worker_travel.destination()

            if destination_entity:
                destination_entity_id = destination_entity.id()
                source_entity_id = source.owner_id()

                if destination_entity_id == source_entity_id:
                    # we're on our way to the source.
                    return
                else:
                    import pdb

                    pdb.set_trace()
                    raise RuntimeError("we got a problem")

            logger.debug(
                "handle_harvesting:location_difference",
                system=self.__class__.__name__,
                source=source,
                worker=worker,
                source_position=source_position,
                worker_position=worker_position,
            )

            worker.ticks = 0

            worker_travel.start(source.owner)
            return

        worker_travel.stop()

        if not worker.can_harvest(resource):
            logger.debug(
                "handle_harvesting:cannot_harvest",
                system=self.__class__.__name__,
                resource=resource,
                source=source,
                worker=worker,
            )

            worker.source = None
            worker.state_change(STATE_IDLE)
            return

        value = source.harvestable_quantity()
        if value < 1:
            return

        if worker.ticks < source.ticks_per_cycle:
            worker.ticks += 1
            return

        worker.ticks = 0

        possible_harvest_quantity = min(source.harvest_value_per_cycle, value)

        worker_capacity = worker.inventory_available_for(resource)
        harvested_quantity = min(possible_harvest_quantity, worker_capacity)
        harvest = [resource for _ in range(harvested_quantity)]
        worker.receive_harvest(harvest)
        source.harvested_quantity(harvested_quantity)

        logger.info(
            "handle_harvest:completed",
            harvestable=source,
            harvested_quantity=harvested_quantity,
            resource=resource,
            system=self.__class__.__name__,
            worker=worker,
        )
