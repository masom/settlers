import structlog
import weakref
from typing import List, Optional, Type, Tuple

from settlers.engine.components.worker import Worker
from settlers.engine.entities.entity import Entity
from settlers.engine.entities.position import Position
from settlers.engine.entities.resources import Resource
from settlers.engine.entities.resources.resource_storage import ResourceStorage
from settlers.engine.components.factory import Factory, FactorySystem, Pipeline as FactoryPipeline 
from settlers.engine.components.movement import (
    ResourceTransport
)
from settlers.engine.components.harvesting import Harvester

STATE_IDLE = 'idle'
STATE_ACTIVE = 'active'

ComponentsType = List[Tuple[type, list, int]]

logger = structlog.get_logger('engine.spawner')


class EntitySpawnSpec:
    __slots__ = (
        'components',
        'fabrication_ticks',
        'name',
        'renderable_type',
        'storages'
    )

    def __init__(
        self, components: ComponentsType,
        fabrication_ticks: int,
        name: str,
        renderable_type: str,
        storages: dict
    ) -> None:
        self.components: ComponentsType = components
        self.fabrication_ticks: int = fabrication_ticks
        self.name: str = name
        self.renderable_type: str = renderable_type
        self.storages: dict = storages

    def __del__(self):
        logger.debug(
            '__del__',
            spec=self,
            klass=self.__class__.__name__,
        )


class SpawnerOutput:
    __slots__ = ('quantity', 'entity_class')

    def __init__(
        self, quantity: int, entity: Type[Entity] 
    ) -> None:
        self.entity_class: Type[Entity] = entity
        self.quantity: int = quantity

    def build(self) -> Entity:
        # TODO Update spawn position to the spawner
        spawned = self.entity_class()

        return spawned

class SpawnerPipeline(FactoryPipeline):
    def build_outputs(self) -> List[Entity]:
        outputs: List[Type[Entity]] = []

        for _ in range(self.output.quantity):
            output: Type[Entity] = self.output.build()
            outputs.append(output)

        return outputs

    def is_available(self) -> bool:
        if self.reserved:
            return False

        for input in self.inputs:
            if not input.can_consume():
                return False

        return True

class SpawnerWorker(Worker):
    _target_components: List[type] = []

    @classmethod
    def target_components(cls) -> list:
        if not cls._target_components:
            cls._target_components.append(Spawner)
        return cls._target_components


class Spawner(Factory):
    exposed_as = 'spawner'

class SpawnerSystem(FactorySystem):
    component_types = [Spawner]

    def __init__(self, world) -> None:
        super().__init__()
        self.world = world

        self.on_production(self._on_spawns)

    def _on_spawns(self, factory: Spawner, spawns: List[Entity]) -> None:
        factory_position: Position = factory.owner.position.reveal(
            Position
        )

        for spawn in spawns:
            spawn.components.add(ResourceTransport)
            spawn.components.add((Harvester, [], spawn.storages))
            spawn.components.add((Position, factory_position.x + 1, factory_position.y + 10))

            self.world.add_entity(spawn)

    def process(self, tick: int, factories: List[Spawner]) -> None:
        logger.debug('process', system=self.__class__.__name__)
        super().process(tick, factories)
