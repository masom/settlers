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


class BuilderProxy:
    __slots__ = ['_building', 'cycles', 'state', 'ticks', '_worker']

    def __init__(self, building, worker):
        self._building = building
        self.state = BUILDER_STATE_IDLE
        self.ticks = 0
        self._worker = weakref.ref(worker)

    def notify_of_building_completion(self):
        worker = self._worker()
        if not worker:
            raise RuntimeError('worker is dead')

        worker.notify_of_building_completion()

        self._building = None
        self._worker = None

    def tick(self):
        self.ticks += 1

    def __del__(self):
        print("{self} we going down!".format(self=self))


class Construction(Component):
    __slots__ = [
        'spec',
        'state',
        'ticks',
        '_workers'
    ]

    exposed_as = 'construction'
    exposed_methods = ['add_builder', 'required_abilities']

    def __init__(self, owner, spec):
        super().__init__(owner)
        self._workers = []
        self.spec = spec
        self.state = STATE_NEW
        self.ticks = 0

    def add_builder(self, builder):
        self._workers.append(BuilderProxy(self, builder))

    def can_build(self):
        if len(self._workers) == 0:
            return False

        for resource, quantity in self.spec.construction_resources.items():
            storage = self.owner.storages[resource]
            if not storage.is_full():
                return False
        return True

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

    def tick(self):
        if self.state == STATE_NEW:
            if self.can_build():
                self.state_change(STATE_IN_PROGRESS)
            return

        if self.state == STATE_IN_PROGRESS:
            if len(self._workers) < 1:
                return

            self.ticks += 1

            for worker in self._workers:
                worker.tick()

            if self.ticks >= self.spec.construction_ticks:
                self.state_change(STATE_COMPLETED)
                return

        if self.state == STATE_COMPLETED:
            for builder in self._workers:
                builder.notify_of_building_completion()

            self.owner.components.remove(self)
            self.owner.storages = {}

            for resource, storage in self.spec.storages.items():
                self.owner.storages[resource] = storage

            for component in self.spec.components:
                self.owner.components.add(component)

            self._workers = []
            self.spec = None
