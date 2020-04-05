import names

from settlers.engine.entities.entity import Entity


class Villager(Entity):
    __slots__ = ['name']
    components = []

    def __init__(self, name=None):
        super().__init__()

        if not name:
            name = names.get_full_name()

        self.name = name

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            klass=self.__class__,
            name=self.name,
            id=hex(id(self)),
        )
