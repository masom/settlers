# -*- coding: utf-8 -*-

import names
from collections import defaultdict

from typing import List, Optional

from settlers.engine.entities.entity import Entity
from settlers.engine.components.movement import Travel, Velocity
from settlers.engine.entities.resources.resource_storage import (
    ResourceStorage,
    ResourceStoragesType,
)

from settlers.entities.renderable import Renderable
from settlers.engine.components import Component


class Villager(Entity):
    __slots__ = ("name", "storages")

    components = [Travel, (Velocity, 2), (Renderable, "villager", 2)]

    def __init__(self, name: Optional[str] = None):
        super().__init__()

        if not name:
            name = names.get_full_name()

        self.storages: ResourceStoragesType = defaultdict(
            self._resource_storage_factory
        )
        self.name = name

    def on_death(self) -> None:
        pass

    def on_spawn(self, components: List[Component]):
        self.initialize()

        for component in components:
            self.components.add(component)

    def _resource_storage_factory(self) -> ResourceStorage:
        return ResourceStorage(True, True, 1)

    def __repr__(self) -> str:
        return "<{klass} {name} {id}>".format(
            klass=self.__class__.__name__,
            name=self.name,
            id=hex(id(self)),
        )
