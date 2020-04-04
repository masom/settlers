from settlers.entities import Entity


class Building(Entity):
    __slots__ = ['name', 'storages']

    def __init__(self, name, storages={}):
        super().__init__()

        self.name = name
        self.storages = storages

    def storage_for(self, resource):
        for stored_resource, storage in self.storages.items():
            if stored_resource == resource.__class__:
                return storage

    def __repr__(self):
        return "<{klass} {name} {id}>".format(
            id=hex(id(self)),
            klass=self.__class__,
            name=self.name,
        )
