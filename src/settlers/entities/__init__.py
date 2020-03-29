from settlers.entities.components import Components


class Position:
    __slots__ = ['x', 'y']

    def __init__(self, x, y):
        self.x = x
        self.y = y


class Entity:
    components = []

    def __init__(self):
        self.components = Components(self)
        self.position = Position(-1, -1)

    def initialize(self):
        self.components.initialize()

    def tick(self):
        self.components.tick()
