import structlog
from typing import Dict, List, Tuple, Type
import weakref
from settlers.engine.entities.entity import Entity
from settlers.engine.entities.resources import Resource
from settlers.engine.components import Component
from settlers.engine.components.worker import Worker

STATE_NEW = 'new'
STATE_IN_PROGRESS = 'in_progress'
STATE_COMPLETED = 'completed'

BUILDER_STATE_IDLE = 'idle'
BUILDER_STATE_WORKING = 'working'

logger = structlog.get_logger('engine.construction')

ComponentsType = List[Tuple[type, list, int]]
ConstructionResourcesType = Dict[Type[Resource], int]


class ConstructionSpec:
    __slots__ = (
        'components', 'construction_resources',
        'construction_abilities', 'construction_ticks',
        'max_workers', 'name', 'storages'
    )

    def __init__(
        self, components: ComponentsType,
        construction_abilities: list,
        construction_resources: ConstructionResourcesType,
        construction_ticks: int,
        max_workers: int,
        name: str,
        storages: dict
    ) -> None:
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
            spec=self,
            klass=self.__class__.__name__,
        )


class ConstructionWorker(Worker):
    __slots__ = ('abilities')

    exposed_as = 'construction'

    _target_components: List[Type[Component]] = []

    def __init__(self, owner: Entity, abilities: set) -> None:
        super().__init__(owner)

        self.abilities = abilities

    @classmethod
    def target_components(cls) -> List[Component]:
        if not cls._target_components:
            cls._target_components.append(Construction)
        return cls._target_components

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self))
        )

class Construction(Component):
    __slots__ = (
        'spec',
        'state',
        'ticks',
        'workers'
    )

    exposed_as = 'construction'
    exposed_methods = ('add_builder', 'can_add_worker', 'required_abilities')

    def __init__(self, owner: Entity, spec: ConstructionSpec) -> None:
        super().__init__(owner)
        self.workers: List[weakref.ReferenceType[ConstructionWorker]] = []
        self.spec = spec
        self.state = STATE_NEW
        self.ticks = 0

    def add_worker(self, worker: ConstructionWorker) -> bool:
        if not self.can_add_worker():
            return False

        if self.spec.construction_abilities:
            possible_abilities = self.spec.construction_abilities

            if not worker.abilities.intersection(possible_abilities):
                raise RuntimeError('cannot build')

        self.workers.append(weakref.ref(worker))
        return True

    def can_add_worker(self) -> bool:
        return len(self.workers) < self.spec.max_workers

    def construction_resources(self) -> ConstructionResourcesType:
        return self.spec.construction_resources

    def is_completed(self) -> bool:
        return self.ticks >= self.spec.construction_ticks

    def required_abilities(self) -> set:
        return self.spec.construction_abilities

    def state_change(self, new_state: str) -> None:
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

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self))
        )


class ConstructionSystem:
    component_types = (
        Construction,
    )

    def __init__(self) -> None:
        self._past_tick: int = 0

    def process(self, tick: int,  constructions: List[Construction]) -> None:
        past_tick = self._past_tick
        self._past_tick = tick


        for construction in constructions:
            if construction.state == STATE_NEW:
                if (tick - past_tick) < 100:
                        continue

                if not construction.workers:
                    logger.debug(
                        'process:no_workers',
                        system=self.__class__.__name__,
                        construction=construction,
                    )
                    continue

                if not self.can_build(construction):
                    logger.debug(
                        'process:cannot_build',
                        system=self.__class__.__name__,
                        construction=construction,
                    )
                    continue

                construction.state_change(STATE_IN_PROGRESS)
                continue

            if construction.state == STATE_IN_PROGRESS:
                if not construction.workers:
                    continue

                construction.ticks += len(construction.workers)

                logger.debug(
                    'process',
                    ticks=construction.ticks,
                    total_ticks=construction.spec.construction_ticks,
                    system=self.__class__.__name__,
                    construction=construction
                )

                if not construction.is_completed():
                    continue

                construction.state_change(STATE_COMPLETED)
                continue

            if construction.state == STATE_COMPLETED:
                self.complete(construction)

    def can_build(self, construction: Construction) -> bool:
        if not construction.workers:
            return False

        for resource, quantity in construction.construction_resources().items():
            storage = construction.owner.storages[resource]
            if not storage.is_full():
                return False

        return True

    def complete(self, building: Construction) -> None:
        logger.debug(
            'complete',
            building=building.owner,
            system=self.__class__.__name__,
        )

        building.stop(skip_idle_state=True)

        building.owner.components.remove(building)
        building.owner.storages = {}

        for resource, storage in building.spec.storages.items():
            building.owner.storages[resource] = storage

        for worker_ref in building.workers:
            worker = worker_ref()
            if not worker:
                continue

            worker.workplace = None
            worker.stop()

        building.workers = []

        for component_definition in building.spec.components:
            building.owner.components.add(component_definition)

        building.owner.renderable.reset_sprite()
        building.spec = None
        building.owner = None
