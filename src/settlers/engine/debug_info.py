from typing import List
from settlers.engine.components import Component
from settlers.engine.entities.entity import Entity

class DebugInfo(Component):
    __slots__ = ("data")

    def __init__(self, owner: Entity) -> None:
        super().__init__(owner)
        self.data: List[str] = []


    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner, component=self.__class__.__name__, id=hex(id(self))
        )
