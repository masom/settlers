import structlog
import weakref

from . import Component

STATE_DELIVERING = 'delivering'
STATE_HARVESTING = 'harvesting'
STATE_IDLE = 'idle'
STATE_FULL = 'full'

logger = structlog.get_logger('harvesting')


class Harvester(Component):
    __slots__ = [
        'destination',
        'on_end_callbacks',
        'resources',
        'state',
        'storage',
        'source',
        'ticks'
    ]

    exposed_as = 'harvest'
    exposed_methods = [
        'assign_destination', 'can_harvest', 'on_end', 'start', 'stop'
    ]

    _target_components = []

    def __init__(self, owner, resources, storage):
        super().__init__(owner)

        self.destination = None
        self.on_end_callbacks = []
        self.state = STATE_IDLE
        self.resources = set(resources)
        self.storage = storage
        self.source = None
        self.ticks = 0

    def assign_destination(self, building):
        self.destination = weakref.ref(building)

    def can_harvest(self, resource):
        if resource not in self.resources:
            return False

        if self.storage.is_full():
            return False
        return True

    def deliver(self):
        self.state_change(STATE_IDLE)

        destination = self.destination()

        if not destination.position == self.owner.position:
            raise RuntimeError('not yet at destination')

        delivered = []
        kept = []
        for resource in self.storage:
            input_storage = destination.inventory.storage_for(resource)
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
            kept=kept
        )

    def inventory_available_for(self, resource):
        return self.storage.available()

    def on_end(self, callback):
        self.on_end_callbacks.append(callback)

    def position(self):
        return self.owner.position

    def receive_harvest(self, harvest):
        collected = 0
        for resource in harvest:
            added = self.storage.add(resource)
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

    def __repr__(self):
        return "<{owner}#{component} {id}>".format(
            component=self.__class__.__name__,
            owner=self.owner,
            id=hex(id(self)),
        )

    def start(self, source):
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

    def state_change(self, new_state):
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

    def stop(self):
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
    __slots__ = [
        'workers',
        'harvest_value_per_cycle',
        'max_workers',
        'output',
        'target_attr',
        'ticks_per_cycle',
    ]

    exposed_as = 'harvesting'
    exposed_methods = [
        'add_worker', 'can_add_worker', 'output', 'provides', 'remove_worker'
    ]

    def __init__(
        self, owner, target_attr, output, ticks_per_cycle,
        harvest_value_per_cycle, max_workers
    ):
        super().__init__(owner)

        self.workers = []
        self.harvest_value_per_cycle = harvest_value_per_cycle
        self.max_workers = max_workers
        self.output = output
        self.target_attr = target_attr
        self.ticks_per_cycle = ticks_per_cycle

    def add_worker(self, worker):
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

    def can_add_worker(self):
        return len(self.workers) < self.max_workers

    def harvestable_quantity(self):
        return getattr(self.owner, self.target_attr)

    def harvested_quantity(self, quantity):
        value = max(0, self.harvestable_quantity() - quantity)

        logger.debug(
            'harvested_quantity',
            owner=self.owner,
            component=self.__class__.__name__,
            harvested_quantity=quantity,
            new_value=value,
        )

        setattr(self.owner, self.target_attr, value)

    def provides(self):
        return self.output

    def remove_worker(self, entity):
        for worker in self.workers:
            if worker.worker() == entity:
                logger.debug(
                    'remove_worker',
                    worker=entity,
                    owner=self.owner,
                    component=self.__class__.__name__,
                )
                self.workers.remove(worker)
                return

    def position(self):
        return self.owner.position

    def __repr__(self):
        return "<{owner}#{component} {id}>".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self))
        )


class HarvesterSystem:
    component_types = set([Harvester])

    def process(self, workers):
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

    def handle_delivery(self, worker):
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
            worker.destination = None
            worker.state_change(STATE_IDLE)
            return

        if destination.position == worker.position():
            worker.deliver()
            worker.state_change(STATE_IDLE)
            return

        if hasattr(worker.owner, 'travel'):
            worker.owner.travel.start(destination)

    def handle_harvesting(self, worker):
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

        if not worker.position() == source.position():
            logger.debug(
                'handle_harvesting_location_difference',
                system=self.__class__.__name__,
                source=source,
                worker=worker,
                source_position=source.position(),
                worker_position=worker.position(),
            )

            worker.ticks = 0
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
