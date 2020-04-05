class Position:
    __slots__ = ['x', 'y']

    def __init__(self, x, y):
        self.x = x
        self.y = y

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
