import weakref

from settlers.entities.components import Component


class Harvester:
    __slots__ = [
        'active', 'cycles', 'harvester_ref', 'harvested', 'resource_ref',
        'ticks'
    ]

    def __init__(self, resource, harvester):
        self.cycles = 0
        self.harvester_ref = weakref.ref(harvester)
        self.resource_ref = weakref.ref(resource)
        self.ticks = 0
        self.harvested = 0

    def is_active(self):
        resource = self.resource_ref()
        harvester = self.harvester_ref()

        if not resource.position() == harvester.position():
            return False

        return harvester.can_harvest()

    def tick(self):
        resource = self.resource_ref()
        harvester = self.harvester_ref()

        if not self.is_active():
            self.cycles = 0
            self.ticks = 0
            return False

        if resource is None or harvester is None:
            print("{resource} or {harvester} dead".format(
                    harvester=harvester,
                    resource=resource,
                )
            )

            self.request_unload(resource, harvester)
            return None

        if self.ticks >= resource.ticks_per_cycle:
            self.cycles += 1
            self.ticks = 0
            return True

        self.ticks += 1
        return False

    def resource_harvested(self, resources):
        harvester = self.harvester_ref()
        self.harvested += len(resources)
        harvester.notify_of_harvest(resources)

    def harvester_stopped(self):
        resource = self.resource_ref()
        if not resource:
            return

        resource.harvester_unloaded(self)

    def request_unload(self):
        resource = self.resource_ref()
        harvester = self.harvester_ref()

        print("{resource} or {harvester} is dead".format(
            resource=resource,
            harvester=harvester,
        ))

        if resource:
            resource.harvesting.harvester_unloaded(self)

        if harvester:
            harvester.harvesting.resource_unloaded(self)


class Harvestable(Component):
    __slots__ = [
        '_harvesters',
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

        self._harvesters = []
        self.harvest_value_per_cycle = harvest_value_per_cycle
        self.max_harvesters = max_harvesters
        self.output = output
        self.target_attr = target_attr
        self.ticks_per_cycle = ticks_per_cycle

    def add_harvester(self, entity):
        if len(self._harvesters) > self.max_harvesters:
            raise

        self._harvesters.append(Harvester(self, entity))

    def build_output(self, quantity):
        return [self.output() for _ in range(quantity)]

    def provides(self):
        return self.output

    def remove_harvester(self, entity):
        for harvester in self._harvesters:
            if harvester.harvester_ref() == entity:
                harvester.request_unload()
                return

    def harvester_unloaded(self, harvester):
        self.harvesters.remove(harvester)

    def position(self):
        return self.owner.position

    def tick(self):
        if len(self._harvesters) == 0:
            return False

        value = getattr(self.owner, self.target_attr)
        if value <= 0:
            return False

        for harvester in self._harvesters:
            tick_completed = harvester.tick()
            if tick_completed is None:
                print("{owner}#{self} harvester {harvester} is dead.".format(
                        owner=self.owner,
                        self=self.__class__.__name__,
                        harvester=harvester,
                    )
                )
                next

            if tick_completed:
                change_to = value - self.harvest_value_per_cycle
                value = max(0, change_to)
                harvested = min(self.harvest_value_per_cycle, value)
                harvester.resource_harvested(
                    self.build_output(harvested)
                )

            if value == 0:
                harvester.active = False

        setattr(self.owner, self.target_attr, value)
        return True
