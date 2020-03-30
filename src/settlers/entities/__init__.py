from settlers.entities.components import Components


class Position:
    __slots__ = ['x', 'y']

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if issubclass(other, self.__class__):
            return self.x == other.x and self.y == other.y
        return False


class Entity:
    components = []

    def __init__(self):
        self.components = Components(self)
        self.position = Position(-1, -1)

    def initialize(self):
        self.components.initialize()

    def tick(self):
        self.components.tick()
