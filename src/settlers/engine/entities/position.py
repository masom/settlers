from ..components import Component


class Position(Component):
    __slots__ = ['x', 'y']

    exposed_as = 'position'
    exposed_methods = ['update']

    def __init__(self, owner, x, y):
        super().__init__(owner)

        self.x = x
        self.y = y

    def update(self, velocity):
        self.x += velocity.x
        self.y += velocity.y

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.x == other.x and self.y == other.y
        return False

    def __repr__(self):
        return "<{klass} at {id}, x={x} y={y}>".format(
            klass=self.__class__,
            id=hex(id(self)),
            x=self.x,
            y=self.y,
        )
