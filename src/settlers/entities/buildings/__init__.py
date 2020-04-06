from settlers.engine.entities.entity import Entity


class Building(Entity):
    __slots__ = ['name', 'storages']

    def __init__(self, name, storages={}):
        super().__init__()

        self.name = name
        self.storages = storages

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            id=hex(id(self)),
            klass=self.__class__,
            name=self.name,
        )
