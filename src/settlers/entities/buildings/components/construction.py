import weakref
from settlers.entities.components import Component

STATE_NEW = 'new'
STATE_IN_PROGRESS = 'in_progress'
STATE_COMPLETED = 'completed'

BUILDER_STATE_IDLE = 'idle'
BUILDER_STATE_WORKING = 'working'


class ConstructionSpec:
    __slots__ = [
        'components', 'construction_resources',
        'construction_abilities', 'construction_ticks',
        'name', 'storages'
    ]

    def __init__(
        self, components,  construction_abilities, construction_resources,
        construction_ticks, name, storages
    ):
        self.components = components
        self.construction_abilities = set(construction_abilities)
        self.construction_resources = construction_resources
        self.construction_ticks = construction_ticks
        self.name = name
        self.storages = storages

    def __del__(self):
        print("{self} we going down!".format(self=self))


class BuilderProxy:
    __slots__ = ['_building', 'cycles', 'state', '_worker']

    def __init__(self, building, worker):
        self._building = building
        self.state = BUILDER_STATE_IDLE
        self._worker = weakref.ref(worker)

    def notify_of_building_completion(self):
        worker = self._worker()
        if not worker:
            raise RuntimeError('worker is dead')

        worker.notify_of_building_completion()

        self._building = None
        self._worker = None

    def __del__(self):
        print("{self} we going down!".format(self=self))


class ConstructionSystem:
    def process(self, buildings):
        for building in buildings:
            if not self.can_build(building):
                continue

            if building.state == STATE_NEW:
                building.state_change(STATE_IN_PROGRESS)
                continue

            if building.state == STATE_IN_PROGRESS:
                building.ticks += 1

                if not building.is_completed():
                    building.state_change(STATE_COMPLETED)
                    continue

            if building.state == STATE_COMPLETED:
                for builder in building.workers:
                    builder.notify_of_building_completion()

                self.complete(building)

    def can_build(self, building):
        if len(building.workers) == 0:
            return False

        for resource, quantity in building.construction_resources.items():
            storage = building.storages[resource]
            if not storage.is_full():
                return False

        return True

    def complete(self, building):
        building.owner.components.remove(building)
        building.owner.storages = {}

        for resource, storage in building.spec.storages.items():
            building.owner.storages[resource] = storage

        for component in building.spec.components:
            building.owner.components.add(component)

        building.workers = []
        building.spec = None
        building.owner = None


class Construction(Component):
    __slots__ = [
        'spec',
        'state',
        'ticks',
        'workers'
    ]

    exposed_as = 'construction'
    exposed_methods = ['add_builder', 'required_abilities']

    def __init__(self, owner, spec):
        super().__init__(owner)
        self.workers = []
        self.spec = spec
        self.state = STATE_NEW
        self.ticks = 0

    def add_worker(self, builder):
        self.workers.append(BuilderProxy(self, builder))

    def construction_resources(self):
        return self.spec.construction_resources

    def is_completed(self):
        return self.ticks >= self.spec.construction_ticks

    def required_abilities(self):
        return self.spec.construction_abilities

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
