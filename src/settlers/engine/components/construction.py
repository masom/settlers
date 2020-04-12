import structlog
import weakref
from settlers.engine.components import Component
from settlers.engine.components.worker import Worker as _Worker

STATE_NEW = 'new'
STATE_IN_PROGRESS = 'in_progress'
STATE_COMPLETED = 'completed'

BUILDER_STATE_IDLE = 'idle'
BUILDER_STATE_WORKING = 'working'

logger = structlog.get_logger('engine.construction')


class ConstructionSpec:
    __slots__ = [
        'components', 'construction_resources',
        'construction_abilities', 'construction_ticks',
        'max_workers', 'name', 'storages'
    ]

    def __init__(
        self, components,  construction_abilities, construction_resources,
        construction_ticks, max_workers, name, storages
    ):
        self.components = components
        self.construction_abilities = set(construction_abilities)
        self.construction_resources = construction_resources
        self.construction_ticks = construction_ticks
        self.max_workers = max_workers
        self.name = name
        self.storages = storages

    def __del__(self):
        logger.debug(
            '__del__',
            owner=self.owner,
            klass=self.__class__.__name__,
        )


class ConstructionWorker(_Worker):
    __slots__ = ['abilities']

    exposed_as = 'construction'

    _target_components = []

    def __init__(self, owner, abilities):
        super().__init__(owner)

        self.abilities = set(abilities)

    @classmethod
    def target_components(cls):
        if not cls._target_components:
            cls._target_components.append(Construction)
        return cls._target_components


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

    def add_worker(self, worker):
        if not self.workers < self.spec.max_workers:
            return False

        if not worker.abilities.intersection(self.spec.construction_abilities):
            raise RuntimeError('cannot build')

        self.workers.append(weakref.ref(worker))

    def construction_resources(self):
        return self.spec.construction_resources

    def is_completed(self):
        return self.ticks >= self.spec.construction_ticks

    def required_abilities(self):
        return self.spec.construction_abilities

    def state_change(self, new_state):
        if self.state == new_state:
            return

        logger.debug(
            'state_change',
            owner=self.owner,
            component=self.__class__.__name__,
            old_state=self.state,
            new_state=new_state
        )
        self.state = new_state

    def __del__(self):
        logger.debug(
            '__del__',
            owner=self.owner,
            component=self.__class__.__name__,
        )


class ConstructionSystem:
    def process(self, buildings):
        for building in buildings:
            if building.state == STATE_NEW:
                if not self.workers:
                    continue

                if not self.can_build(building):
                    continue

                building.state_change(STATE_IN_PROGRESS)
                continue

            if building.state == STATE_IN_PROGRESS:
                if not self.workers:
                    continue

                building.ticks += 1

                if not building.is_completed():
                    building.state_change(STATE_COMPLETED)
                    continue

            if building.state == STATE_COMPLETED:
                self.complete(building)

    def can_build(self, building):
        if not building.workers:
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

        for worker in building.workers:
            worker.workplace = None
            worker.state_change(BUILDER_STATE_IDLE)

        building.workers = []
        building.spec = None
        building.owner = None
