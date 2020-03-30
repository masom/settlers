import weakref

from settlers.entities.components import Component


class OccupantProxy:
    __slots__ = ['target', 'occupant']

    def __init__(self, target, occupant):
        self.target = weakref.ref(target)
        self.occupant = weakref.ref(occupant)


class Occupancy(Component):
    __slots__ = ['max_occupancy', 'occupants']

    exposed_as = 'occupancy'
    exposed_methods = ['add_tenant', 'evict']

    def __init__(self, owner, max_occupancy):
        super().__init__(owner)

        self.max_occupancy = max_occupancy
        self.occupants = []

    def add_tenant(self, entity):
        if self.occupants.size >= self.max_occupancy:
            raise

        self.occupants.append(OccupantProxy(self, entity))

    def evict(self, entity):
        pass
