from settlers.entities.components import Component


class Harvester:
    __slots__ = [
        'active', 'cycles', 'entity', 'harvested', 'resource', 'ticks'
    ]

    def __init__(self, resource, entity):
        self.active = False
        self.cycles = 0
        self.entity = entity
        self.resource = resource
        self.ticks = 0
        self.harvested = 0

    def tick(self):
        if not self.active:
            self.cycles = 0
            self.ticks = 0
            return False

        if self.ticks >= self.resource.ticks_per_cycle:
            self.cycles += 1
            self.ticks = 0
            self.harvested += self.resource.harvest_value_per_cycle
            self.active = False
            return True

        self.ticks += 1
        return False


class Harvestable(Component):
    __slots__ = [
        'harvesters',
        'harvest_value_per_cycle',
        'max_harvesters',
        'target_attr',
        'ticks_per_cycle',
    ]

    def __init__(
        self, owner, target_attr, ticks_per_cycle,
        harvest_value_per_cycle, max_harvesters
    ):
        super().__init__(owner)

        self.harvesters = []
        self.harvest_value_per_cycle = harvest_value_per_cycle
        self.max_harvesters = max_harvesters
        self.target_attr = target_attr
        self.ticks_per_cycle = ticks_per_cycle

    def add_harvester(self, entity):
        if len(self.harvesters) > self.max_harvesters:
            raise

        self.harvesters.push(Harvester(self, entity))

    def tick(self):
        if len(self.harvesters) == 0:
            return False

        value = getattr(self.owner, self.target_attr)
        if value <= 0:
            return False

        for harvester in self.harvesters:
            harvest_complete = harvester.tick()
            if harvest_complete:
                change_to = value - self.harvest_value_per_cycle
                value = max(0, change_to)
                harvester.harvested += min(self.harvest_value_per_cycle, value)

            if value == 0:
                harvester.active = False

        setattr(self.owner, self.target_attr, value)
        return True
