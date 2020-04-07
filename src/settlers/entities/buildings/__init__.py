from settlers.engine.entities.entity import Entity


class Building(Entity):
    __slots__ = ['name', 'storages']

    def __init__(self, name, storages={}):
        super().__init__()

        self.name = name
        self.storages = storages

    def wants_resources(self):
        return [
            resource
            for resource, storage in self.storages.items()
            if storage.allows_incoming and not storage.is_full()
        ]

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            id=hex(id(self)),
            klass=self.__class__,
            name=self.name,
        )
