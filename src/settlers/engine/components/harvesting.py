import weakref

from . import Component

STATE_DELIVERING = 'delivering'
STATE_HARVESTING = 'harvesting'
STATE_IDLE = 'idle'
STATE_FULL = 'full'


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

    def __init__(self, owner, resources, storage):
        super().__init__(owner)

        self.destination = None
        self.on_end_callbacks = []
        self.state = STATE_IDLE
        self.resources = set(resources)
        self.storage = storage
        self.source = None
        self.ticks = 0

    @classmethod
    def target_components(cls):
        return [Harvestable]

    def assign_destination(self, building):
        self.destination = weakref.ref(building)

    def can_harvest(self, resource):
        if resource not in self.resources:
            return False

        if self.storage.is_full():
            return False
        return True

    def inventory_available_for(self, resource):
        return self.storage.available()

    def start(self, source):
        if self.source:
            raise RuntimeError('already assigned')

        if not source.can_be_harvested():
            return False

        print(
            "{owner}#{component} start on {target}".format(
                owner=self.owner,
                component=self.__class__.__name__,
                target=source
            )
        )

        self.source = weakref.ref(source)
        source.add_worker(self)
        return True

    def deliver(self):
        self.state_change(STATE_IDLE)

        destination = self.destination()

        if not destination.position == self.owner.position:
            raise RuntimeError('not yet at destination')

        delivered = []
        kept = []
        for resource in self.storage:
            input_storage = destination.storage_for(resource)
            if not input_storage:
                continue

            if input_storage.add(resource):
                delivered.append(resource)
                self.storage.remove(resource)
            else:
                kept.append(resource)
                print(
                    "{owner}#{component} cannot deliver {resource} to"
                    " {destination} storage {destination_storage}".format(
                        component=self.__class__.__name__,
                        owner=self.owner,
                        destination=destination,
                        destination_storage=input_storage
                    )
                )
        print(
            "{owner}#{component} delivered: {delivered} and"
            " kept: {kept}".format(
                owner=self.owner,
                component=self.__class__.__name__,
                delivered=delivered,
                kept=kept
            )
        )

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

        print(
            "{self}#{component} we got a harvest of {harvest}."
            " Accepted {collected} out of {total} given!".format(
                self=self.owner,
                component=self.__class__.__name__,
                collected=collected,
                total=len(harvest),
                harvest=harvest,
            )
        )

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

        self.on_end_callbacks = []

    def state_change(self, new_state):
        if self.state == new_state:
            return

        print(
            "{owner}#{component} state change:"
            " {old_state} -> {new_state}".format(
                owner=self.owner,
                component=self.__class__.__name__,
                old_state=self.state,
                new_state=new_state
            )
        )
        self.state = new_state


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
        'add_worker', 'can_be_harvested', 'output', 'provides', 'remove_worker'
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

        worker_ref = weakref.ref(worker)
        self.workers.append(worker_ref)
        return True

    def can_be_harvested(self):
        return len(self.workers) < self.max_workers

    def harvestable_quantity(self):
        return getattr(self.owner, self.target_attr)

    def harvested_quantity(self, quantity):
        value = max(0, self.harvestable_quantity() - quantity)
        setattr(self.owner, self.target_attr, value)

    def provides(self):
        return self.output

    def remove_worker(self, entity):
        for worker in self.workers:
            if worker.worker() == entity:
                self.workers.remove(worker)
                return

    def position(self):
        return self.owner.position

    def __repr__(self):
        return "<{owner}#{component} {id}>".format(
            component=self.__class__.__name__,
            owner=self.owner,
            id=hex(id(self))
        )


class HarvesterSystem:
    component_types = set([Harvester])

    def process(self, workers):
        for worker in workers:
            if worker.state == STATE_IDLE:
                if not worker.source:
                    return

                self.handle_harvesting(worker)
                continue

            if worker.state == STATE_HARVESTING:
                self.handle_harvesting(worker)
                continue

            if worker.state == STATE_FULL:
                self.handle_delivery(worker)

            if worker.state == STATE_DELIVERING:
                self.handle_delivery(worker)

    def handle_delivery(self, worker):
        if not worker.destination:
            return

        destination = worker.destination()
        if not destination:
            raise RuntimeError('destination dead')

        if destination.position == worker.position():
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
            worker.state_change(STATE_IDLE)
            print('no source')
            return

        resource = source.output

        if not worker.can_harvest(resource):
            worker.state_change(STATE_IDLE)
            worker.target = None
            return

        if not worker.position() == source.position():
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

        print(
            "{system}#{harvestable} {harvested_quantity} {resource}"
            " has been collected by {worker}".format(
                harvestable=source,
                harvested_quantity=harvested_quantity,
                resource=resource,
                system=self.__class__.__name__,
                worker=worker,
            )
        )
