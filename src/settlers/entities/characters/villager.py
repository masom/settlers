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

from settlers.entities.renderable import (
    Renderable,
    label_cache as RenderableLabelCache,
    Label as RenderableLabel,
    LABEL_NAME as RENDERABLE_LABEL_NAME,
    LABEL_COLOR_NAME as RENDERABLE_LABEL_COLOR_NAME,
    LABEL_POSITION_TOP as RENDERABLE_LABEL_POSITION_TOP,
)

from settlers.engine.components import Component, ComponentManager


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

    def initialize(self) -> None:
        super().initialize()

        renderable = ComponentManager.fetch(self.id(), Renderable)
        name_label = RenderableLabelCache.get(
            RENDERABLE_LABEL_NAME,
            self.name,
            RENDERABLE_LABEL_COLOR_NAME,
            position=RENDERABLE_LABEL_POSITION_TOP,
            shadow=True,
        )
        renderable.add_label(name_label)

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
