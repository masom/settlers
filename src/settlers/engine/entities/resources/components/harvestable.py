import weakref

from ....components import Component

HARVESTER_STATE_IDLE = 'idle'
HARVESTER_STATE_HARVESTING = 'harvesting'


class Harvester:
    __slots__ = [
        'cycles', 'harvester', 'harvested', 'resource',
        'state', 'ticks'
    ]

    def __init__(self, resource, harvester):
        self.cycles = 0
        self.harvester = weakref.ref(harvester)
        self.resource = weakref.ref(resource)
        self.ticks = 0
        self.harvested = 0
        self.state = HARVESTER_STATE_IDLE

    def is_active(self):
        resource = self.resource()
        harvester = self.harvester()

        if not resource.position() == harvester.position():
            return False

        if not harvester.can_harvest():
            return False
        return True

    def state_change(self, new_state):
        if self.state == new_state:
            return

        resource = self.resource()

        print(
            "{owner}#{component} state change:"
            " {old_state} -> {new_state}".format(
                owner=resource,
                component=self,
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
    exposed_methods = ['add_harvester', 'provides', 'remove_harvester']

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

    def add_worker(self, entity):
        if len(self.workers) > self.max_workers:
            raise

        self.workers.append(Harvester(self, entity))

    def provides(self):
        return self.output

    def remove_worker(self, entity):
        for worker in self.workers:
            if worker.worker() == entity:
                self.workers.remove(worker)
                return

    def position(self):
        return self.owner.position


class HarvestableSystem:
    component_types = set([Harvestable])

    def process(self, harvestables):
        for harvestable in harvestables:
            if not harvestable.workers:
                continue

            value = getattr(harvestable.owner, harvestable.target_attr)
            if value <= 0:
                continue

            for worker in harvestable.workers:
                change = self.process_worker(worker)
                if change == 0:
                    continue

                value = max(0, value - change)

            setattr(harvestable.owner, harvestable.target_attr, value)

    def process_worker(self, harvestable, worker):
        resource = harvestable.output

        if not worker.is_active() or not worker.can_harvest(resource):
            self.state_change(HARVESTER_STATE_IDLE)
            worker.ticks = 0
            return 0

        worker.state_change(HARVESTER_STATE_HARVESTING)

        if worker.ticks < harvestable.ticks_per_cycle:
            worker.ticks += 1
            return 0

        worker.ticks = 0

        value = getattr(harvestable.owner, harvestable.target_attr)

        possible_harvest_quantity = min(
            harvestable.harvest_value_per_cycle,
            value
        )

        worker_capacity = worker.inventory_available_for(resource)

        harvested_quantity = min(possible_harvest_quantity, worker_capacity)

        # harvest = [harvestable.output() for _ in range(harvested_quantity)]

        print(
            "{system}#{harvestable} {harvested_quantity} {resource}"
            " has been collected by {worker}".format(
                harvestable={harvestable},
                harvested_quantity=harvested_quantity,
                resource=resource,
                system=self.__class__.__name__,
                worker=worker,
            )
        )

        return harvested_quantity
