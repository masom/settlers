# -*- coding: utf-8 -*-

import names
from collections import defaultdict

from typing import List, Optional

from settlers.engine.entities.entity import Entity
from settlers.engine.components.movement import (
    Travel, Velocity
)
from settlers.engine.entities.resources.resource_storage import (
    ResourceStorage, ResourceStoragesType
)

from settlers.entities.fauna.components.fauna_ai_system import (
    FaunaAi    
)

from settlers.entities.renderable import Renderable


class Deer(Entity):
    __slots__ = ('name', 'storages')

    components = [
        FaunaAi,
        Travel,
        (Velocity, 2),
        (Renderable, 'deer', 2)
    ]

    def on_spawn(self, components: List):
        self.initialize()

        for component in components:
            self.components.add(component)

        self.components.add(ResourceTransport)
        self.components.add((Harvester, [], self.storages))

    def __repr__(self) -> str:
        return "<{klass} {id}>".format(
            klass=self.__class__.__name__,
            id=hex(id(self)),
        )
