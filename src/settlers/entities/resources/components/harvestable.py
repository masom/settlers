import weakref

from settlers.entities.components import Component

HARVESTER_STATE_IDLE = 'idle'
HARVESTER_STATE_HARVESTING = 'harvesting'


class HarvestableSystem:
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

    def build_output(self, harvester, quantity):
        return [harvester.output() for _ in range(quantity)]

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

        harvest = [harvestable.output() for _ in range(harvested_quantity)]

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
        'harvesters',
        'harvest_value_per_cycle',
        'max_harvesters',
        'output',
        'target_attr',
        'ticks_per_cycle',
    ]

    exposed_as = 'harvesting'
    exposed_methods = ['add_harvester', 'provides', 'remove_harvester']

    def __init__(
        self, owner, target_attr, output, ticks_per_cycle,
        harvest_value_per_cycle, max_harvesters
    ):
        super().__init__(owner)

        self.harvesters = []
        self.harvest_value_per_cycle = harvest_value_per_cycle
        self.max_harvesters = max_harvesters
        self.output = output
        self.target_attr = target_attr
        self.ticks_per_cycle = ticks_per_cycle

    def add_harvester(self, entity):
        if len(self.harvesters) > self.max_harvesters:
            raise

        self.harvesters.append(Harvester(self, entity))

    def provides(self):
        return self.output

    def remove_harvester(self, entity):
        for harvester in self._harvesters:
            if harvester.harvester_ref() == entity:
                harvester.request_unload()
                return

    def position(self):
        return self.owner.position
