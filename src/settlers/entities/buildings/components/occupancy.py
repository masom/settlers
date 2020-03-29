from settlers.entities.components import Component, ComponentEvent
from settlers.entities.components.message_queue import EventMessage, Messages


OCCUPANCY_EVICTION = 'eviction'


class Occupancy(Component):
    __slots__ = ['max_occupancy', 'occupants']

    exposed_as = 'occupancy'
    exposed_methods = ['add', 'evict']

    def __init__(self, owner, max_occupancy):
        super()

        self.max_occupancy = max_occupancy
        self.occupants = []

    def add(self, entity):
        if self.occupants.size >= self.max_occupancy:
            raise

        self.occupants.push(entity)

    def evict(self):
        for occupant in self.occupants:
            message = EventMessage(
                Messages.TYPE_SYSTEM,
                Messages.PRIORITY_HIGH,
                Messages.INTERUPT_FALSE,
                ComponentEvent(
                    'Occupancy',
                    OCCUPANCY_EVICTION,
                    self
                )
            )
            occupant.message_queue.add(message)
