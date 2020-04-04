import weakref

from settlers.entities.components import Component


STATE_IDLE = 'idle'
STATE_MOVING = 'moving'


class Mouvement(Component):
    __slots__ = ['destination', 'state']

    exposed_as = 'mouvement'
    exposed_methods = ['travel_to']

    DIRECTION_UP = 'up'
    DIRECTION_DOWN = 'down'
    DIRECTION_LEFT = 'left'
    DIRECTION_RIGHT = 'right'

    movements_per_seconds = 1.0

    directions = [
        DIRECTION_UP,
        DIRECTION_DOWN,
        DIRECTION_LEFT,
        DIRECTION_RIGHT
    ]

    def __init__(self, owner):
        super().__init__(owner)
        self.state = STATE_IDLE

    def move(self, direction):
        if direction in self.directions:
            self.position.update(direction)
        else:
            raise

    def state_change(self, new_state):
        print("{owner}#{component} state change: {old_state} -> {new_state}".format(
                owner=self.owner,
                component=self,
                old_state=self.state,
                new_state=new_state
            )
        )
        self.state = new_state

    def tick(self):
        if self.state == STATE_IDLE:
            return

        if self.state == STATE_MOVING:
            if not self.destination:
                self.state_change(STATE_IDLE)
                return

            destination = self.destination()
            if not destination:
                self.destination = None
                self.state_change(STATE_IDLE)
                return

            if destination.position == self.owner.position:
                self.state_change(STATE_IDLE)
                return

    def travel_to(self, destination):
        print(
            "{owner} at {owner_position} moving to "
            " {destination} at {destination_position}".format(
                owner=self.owner,
                owner_position=self.owner.position,
                destination=destination,
                destination_position=destination.position,
            )
        )

        self.state_change(STATE_MOVING)
        self.destination = weakref.ref(destination)
