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
        self.construction_abilities = construction_abilities
        self.construction_resources = construction_resources
        self.construction_ticks = construction_ticks
        self.name = name
        self.storages = storages


class BuilderProxy:
    __slots__ = ['_builder', 'cycles', 'state', '_target', 'ticks']

    def __init__(self, builder, target):
        self._builder = builder
        self.state = BUILDER_STATE_IDLE
        self._target = target

    def tick(self):
        pass


class Construction(Component):
    __slots__ = [
        'spec',
        'state',
        'ticks',
        '_workers'
    ]

    exposed_as = 'construction'
    exposed_methods = ['add_builder']

    def __init__(self, owner, spec):
        super().__init__(owner)
        self._workers = []
        self.spec = spec
        self.state = STATE_NEW
        self.ticks = 0

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
            return

        if self.state == STATE_IN_PROGRESS:
            self.ticks += 1

            if self.ticks >= self.spec.construction_ticks:
                self.state_change(STATE_COMPLETED)
                return

        if self.state == STATE_COMPLETED:
            for builder in self._workers:
                del builder
            self._workers = []
            self.owner.components.remove(self)

            for component in self.components:
                self.owner.components.add(component)

            del self
