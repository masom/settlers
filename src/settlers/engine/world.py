from typing import Optional

from settlers.engine.entities.entity import Entity
from settlers.engine.components import ComponentManager


class World:
    __slots__ = ('entities', 'map', 'random_seed', 'systems')

    def __init__(self, random_seed: Optional[int] = None, map=None) -> None:
        self.entities: list[Entity] = []
        self.systems: list[type] = []
        self.random_seed = random_seed

    def add_system(self, system: type) -> None:
        self.systems.append(system)

    def add_entity(self, entity: Entity) -> None:
        self.entities.append(entity)

    def initialize(self) -> None:
        for entity in self.entities:
            entity.initialize()

    def process(self, tick: int) -> None:
        for system in self.systems:
            components = self.components_matching(system.component_types)

            if not components:
                continue

            system.process(tick, components)

    def components_matching(self, wants: list) -> list:
        components = []
        len_wants = len(wants)
        entities = ComponentManager.entities_matching(wants)

        method_name = 'extend'
        if len_wants > 1:
            method_name = 'append'

        method = getattr(components, method_name)

        for entity, entity_components in entities:
            method(entity_components)

        return components
