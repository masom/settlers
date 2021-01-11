import structlog
from typing import Callable, List, Optional, Type
import weakref

from . import Component
from settlers.engine.entities.resources import Resource
from settlers.engine.entities.resources.resource_storage import ResourceStorage


STATE_DELIVERING = 'delivering'
STATE_HARVESTING = 'harvesting'
STATE_IDLE = 'idle'
STATE_FULL = 'full'


logger = structlog.get_logger('harvesting')


class Harvester(Component):
    __slots__ = (
        'destination',
        'on_end_callbacks',
        'resources',
        'state',
        'storage',
        'source',
        'ticks'
    )

    exposed_as = 'harvest'
    exposed_methods = (
        'assign_destination', 'can_harvest', 'on_end', 'start', 'stop'
    )

    _target_components = []

    def __init__(
        self, owner, resources: List[Type[Resource]], storage: ResourceStorage
    ):
        super().__init__(owner)

        self.destination: Optional[weakref.ReferenceType] = None
        self.on_end_callbacks: List[Callable] = []
        self.state = STATE_IDLE
        self.resources = set(resources)
        self.storage = storage
        self.source = None
        self.ticks = 0

    def assign_destination(self, building) -> None:
        self.destination = weakref.ref(building)

    def can_harvest(self, resource: Type[Resource]) -> bool:
        if resource not in self.resources:
            return False

        if self.storage.is_full():
            return False
        return True

    def deliver(self) -> None:
        self.state_change(STATE_IDLE)

        if not self.destination:
            raise RuntimeError('no destination')

        destination = self.destination()

        if not destination.position == self.owner.position:
            raise RuntimeError('not yet at destination')

        delivered: List[Resource] = []
        kept: List[Resource] = []

        for resource in self.storage:
            input_storage: ResourceStorage = destination.inventory.storage_for(
                resource
            )

            if not input_storage:
                continue

            if input_storage.add(resource):
                delivered.append(resource)
                self.storage.remove(resource)
            else:
                kept.append(resource)
                logger.info(
                    'cannot deliver',
                    component=self.__class__.__name__,
                    owner=self.owner,
                    destination=destination,
                    destination_storage=input_storage
                )
        logger.info(
            'delivered',
            owner=self.owner,
            component=self.__class__.__name__,
            delivered=delivered,
            destination=destination,
            kept=kept
        )

    def inventory_available_for(self, resource: type) -> bool:
        return self.storage.available()

    def on_end(self, callback: Callable) -> None:
        self.on_end_callbacks.append(callback)

    def position(self):
        return self.owner.position

    def receive_harvest(self, harvest: List[Type[Resource]]) -> None:
        collected = 0

        for resource in harvest:
            added: bool = self.storage.add(resource)
            if added:
                collected += 1
            else:
                raise RuntimeError('full...')

        logger.info(
            'receive_harvest',
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
            raise RuntimeError('already assigned')

        if not source.can_add_worker():
            logger.debug(
                'start_source_rejected',
                source=source,
                component=self.__class__.__name__,
                owner=self.owner,
            )
            return False

        logger.debug(
            'start_requested',
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
            'state_change',
            old_state=self.state,
            new_state=new_state,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.state = new_state

    def stop(self) -> None:
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
            'stop',
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
        'workers',
        'harvest_value_per_cycle',
        'max_workers',
        'output',
        'target_attr',
        'ticks_per_cycle',
    )

    exposed_as = 'harvesting'
    exposed_methods = (
        'add_worker', 'can_add_worker', 'output', 'provides', 'remove_worker'
    )

    def __init__(
        self, owner, target_attr: str, output: type, ticks_per_cycle: int,
        harvest_value_per_cycle: int, max_workers: int
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
            'add_worker',
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
            'harvested_quantity',
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
                    'remove_worker',
                    worker=entity,
                    owner=self.owner,
                    component=self.__class__.__name__,
                )
                self.workers.remove(worker)
                return True
        return False

    def position(self):
        return self.owner.position

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self))
        )


class HarvesterSystem:
    component_types = [Harvester]

    def process(self, workers: List[Harvester]) -> None:
        for worker in workers:
            if worker.state == STATE_IDLE:
                if not worker.source:
                    continue
                worker.state_change(STATE_HARVESTING)
                continue

            if worker.state == STATE_HARVESTING:
                self.handle_harvesting(worker)
                continue

            if worker.state == STATE_FULL:
                self.handle_delivery(worker)
                continue

            if worker.state == STATE_DELIVERING:
                self.handle_delivery(worker)

    def handle_delivery(self, worker: Harvester) -> None:
        if not worker.destination:
            logger.debug(
                'handle_delivery_no_destination',
                system=self.__class__.__name__,
                source=worker.source,
                worker=worker,
            )
            return

        destination = worker.destination()
        if not destination:
            worker.stop()
            return

        if destination.position == worker.position():
            worker.deliver()
            worker.state_change(STATE_IDLE)
            return

        if not worker.owner.travel.destination:
            worker.owner.travel.start(destination)
            return

        travel_destination = worker.owner.travel.destination()
        if not travel_destination.position == destination.position:
            import pdb; pdb.set_trace()
            return

    def handle_harvesting(self, worker: Harvester):
        if worker.storage.is_full():
            worker.state_change(STATE_FULL)
            return

        if not worker.source:
            worker.stop()
            return

        source = worker.source()
        if not source:
            logger.debug(
                'handle_harvesting source dead',
                system=self.__class__.__name__,
                source=worker.source,
                worker=worker,
            )
            worker.source = None
            worker.state_change(STATE_IDLE)
            return

        resource = source.output

        if not worker.position() == source.position():
            travel = worker.owner.travel
            destination = travel.destination

            if destination:
                if destination().position == source.position():
                    return
                else:
                    raise RuntimeError('we got a problem')

            logger.debug(
                'handle_harvesting_location_difference',
                system=self.__class__.__name__,
                source=source,
                worker=worker,
                source_position=source.position(),
                worker_position=worker.position(),
            )

            worker.ticks = 0

            travel.start(source.owner)
            return

        if not worker.can_harvest(resource):
            logger.debug(
                'handle_harvesting_cannot_harvest',
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

        possible_harvest_quantity = min(
            source.harvest_value_per_cycle,
            value
        )

        worker_capacity = worker.inventory_available_for(resource)
        harvested_quantity = min(possible_harvest_quantity, worker_capacity)
        harvest = [source.output() for _ in range(harvested_quantity)]
        worker.receive_harvest(harvest)
        source.harvested_quantity(harvested_quantity)

        logger.info(
            'handle_harvest_completed',
            harvestable=source,
            harvested_quantity=harvested_quantity,
            resource=resource,
            system=self.__class__.__name__,
            worker=worker,
        )
