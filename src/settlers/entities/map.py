from settlers.engine.entities.entity import Entity
from settlers.engine.entities.position import Position

from settlers.entities.renderable import Renderable


class MapTile(Entity):
    __slots__ = ['column', 'row', 'sprite']

    components = [
        (Renderable, 'tile', 0)
    ]

    def __init__(self, row, column):
        self.sprite = None
        self.row = row
        self.column = column

        super().__init__()

    def initialize(self):
        position = (Position, self.row * 120, self.column * 140)
        self.components.add(
            position
        )

        super().initialize()

    def __repr__(self):
        position = getattr(self, 'position', None)
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
    def __init__(self):
        self.x = int(800 / 120)
        self.y = int(600 / 140)

    def generate(self):
        tiles = []
        for x in range(self.x):
            row = []

            for y in range(self.y):
                row.append(MapTile(x, y))
            tiles.append(row)

        self.tiles = tiles
