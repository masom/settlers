import weakref
from . import Component
from ..entities.position import Position

STATE_IDLE = 'idle'
STATE_MOVING = 'moving'


class Velocity(Component):
    __slots__ = ['x', 'y']

    def __init__(self, owner):
        super().__init__(owner)

        self.x = 0
        self.y = 0


DIRECTION_UP = 'up'
DIRECTION_DOWN = 'down'
DIRECTION_LEFT = 'left'
DIRECTION_RIGHT = 'right'


class Travel(Component):
    __slots__ = ['destination', 'state']

    exposed_as = 'travel'
    exposed_methods = ['travel_to']

    def __init__(self, owner):
        super().__init__(owner)

        self.state = STATE_IDLE
        self.destination = None

    def state_change(self, new_state):
        print(
            "{owner}#{component} state change: "
            "{old_state} -> {new_state}".format(
                owner=self.owner,
                component=self.__class__.__name__,
                old_state=self.state,
                new_state=new_state
            )
        )
        self.state = new_state

    def travel_to(self, destination):
        print(
            "{owner}#{component} at {owner_position} moving to "
            " {destination} at {destination_position}".format(
                owner=self.owner,
                owner_position=self.owner.position,
                component=self.__class__.__name__,
                destination=destination,
                destination_position=destination.position,
            )
        )

        self.destination = weakref.ref(destination)


class TravelSystem:
    component_types = set([Travel, Position, Velocity])

    def process(self, entities):
        for entity, travel, position, velocity in entities:
            if not travel.destination:
                travel.state_change(STATE_IDLE)
                continue

            destination = travel.destination()
            if not destination:
                travel.destination = None
                travel.state_change(STATE_IDLE)

            if self.state == STATE_MOVING:
                if destination.position == self.owner.position:
                    self.destination = None
                    self.state_change(STATE_IDLE)
                    return

                position.update(velocity)


class PhysicsSystem:
    component_types = set([Position])

    def __init__(self, world):
        self.world = world

    def process(self, entities):
        for entity in entities:
            pass
