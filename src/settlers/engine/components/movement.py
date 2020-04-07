import structlog
import weakref

from . import Component
from ..entities.position import Position

STATE_IDLE = 'idle'
STATE_MOVING = 'moving'

logger = structlog.get_logger('engine.movement')


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
    __slots__ = ['destination', 'on_end_callbacks', 'state']

    exposed_as = 'travel'
    exposed_methods = ['on_end', 'start', 'stop']

    def __init__(self, owner):
        super().__init__(owner)

        self.state = STATE_IDLE
        self.destination = None
        self.on_end_callbacks = []

    def on_end(self, callback):
        self.on_end_callbacks.append(callback)

    def start(self, destination):
        if self.destination:
            raise RuntimeError('already moving somewhere')

        self.destination = weakref.ref(destination)
        self.state_change(STATE_MOVING)

    def state_change(self, new_state):
        if self.state == new_state:
            return

        destination = self.destination
        if destination:
            destination = destination()

        logger.debug(
            'state_change',
            old_state=self.state,
            new_state=new_state,
            destination=destination,
            owner=self.owner,
            component=self.__class__.__name__,
        )
        self.state = new_state

    def stop(self):
        self.state_change(STATE_IDLE)

        for callback in self.on_end_callbacks:
            callback(self)

        self.destination = None
        self.on_end_callbacks = []


class TravelSystem:
    component_types = set([Travel, Position, Velocity])

    def process(self, entities):
        for travel, position, velocity in entities:
            if not travel.destination:
                travel.state_change(STATE_IDLE)
                continue

            destination = travel.destination()
            if not destination:
                logger.debug(
                    'process_destination_dead',
                    destination=travel.destination,
                    owner=travel.owner,
                    system=self.__class__.__name__,
                )

                travel.destination = None
                travel.state_change(STATE_IDLE)
                continue

            if travel.state == STATE_IDLE:
                travel.state_change(STATE_MOVING)
                continue

            if travel.state == STATE_MOVING:
                if destination.position == self.owner.position:
                    travel.stop()
                    continue

                position.update(velocity)
