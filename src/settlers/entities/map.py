from typing import List
from settlers.engine.entities.entity import Entity
from settlers.engine.entities.position import Position

from settlers.entities.renderable import Renderable


class MapTile(Entity):
    __slots__ = ["column", "row", "sprite"]

    components = []

    def __init__(self, row: int, column: int) -> None:
        self.sprite = None
        self.row = row
        self.column = column

        super().__init__()

    def initialize(self) -> None:
        self.components.add((Renderable, "tile", 0))
        self.components.add((Position, self.row * 120, self.column * 140))

        super().initialize()

    def __repr__(self) -> str:
        position = getattr(self, "position", None)
        if not position:
            position = (self.row * 120, self.column * 140)

        return "<{klass} {row} {column} {position} {id}>".format(
            klass=self.__class__.__name__,
            row=self.row,
            column=self.column,
            position=position,
            id=hex(id(self)),
        )


class Map:
    def __init__(self) -> None:
        self.x: int = int(800 / 120)
        self.y: int = int(600 / 140)

    def generate(self) -> None:
        tiles = []
        for x in range(self.x):
            row = []

            for y in range(self.y):
                row.append(MapTile(x, y))
            tiles.append(row)

        self.tiles: List[MapTile] = tiles
