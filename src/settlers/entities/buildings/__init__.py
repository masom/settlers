from settlers.engine.entities.entity import Entity
from settlers.engine.components import ComponentManager
from settlers.engine.components.inventory_routing import InventoryRouting
from settlers.entities.renderable import (
    Renderable,
    label_cache as RenderableLabelCache,
    Label as RenderableLabel,
    LABEL_TYPE_NAME as RENDERABLE_LABEL_TYPE_NAME,
    LABEL_COLOR_NAME as RENDERABLE_LABEL_COLOR_NAME,
    LABEL_POSITION_TOP as RENDERABLE_LABEL_POSITION_TOP,
)


class Building(Entity):
    __slots__ = ("inventory_routing_priority", "name", "storages", "renderable_type")

    """
    renderable_type allows overriding what the renderable will be. 
    """

    def __init__(
        self, name, storages={}, inventory_routing_priority=[], renderable_type=None
    ) -> None:
        super().__init__()

        self.name: str = name
        self.storages: dict = storages
        self.inventory_routing_priority: list = inventory_routing_priority
        self.renderable_type: str = renderable_type or "building"

    def initialize(self):
        self.components.add((InventoryRouting, self.inventory_routing_priority))

        self.components.add((Renderable, self.renderable_type, 1))

        renderable = ComponentManager.fetch(self.id(), Renderable)
        name_label = RenderableLabelCache.get(
            RENDERABLE_LABEL_TYPE_NAME,
            self.name,
            RENDERABLE_LABEL_COLOR_NAME,
            position=RENDERABLE_LABEL_POSITION_TOP,
            shadow=True,
        )
        renderable.add_label(name_label)

        super().initialize()

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            id=hex(id(self)),
            klass=self.__class__,
            name=self.name,
        )
