import structlog
import weakref

from . import Component
from ..entities.position import Position

STATE_IDLE = 'idle'
STATE_MOVING = 'moving'
STATE_LOADING = 'loading'
STATE_UNLOADING = 'unloading'

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

TRANSPORT_DIRECTION_SOURCE = 'source'
TRANSPORT_DIRECTION_DESTINATION = 'destination'


class Travel(Component):
    __slots__ = ['destination']

    exposed_as = 'travel'
    exposed_methods = ['on_end', 'start', 'stop']

    def __init__(self, owner):
        super().__init__(owner)

        self.destination = None

    def start(self, destination):
        if self.destination:
            raise RuntimeError('already moving somewhere')

        self.destination = weakref.ref(destination)
        self.state_change(STATE_MOVING)

    def stop(self):
        super().stop()
        self.destination = None


class TravelSystem:
    component_types = set([Travel, Position, Velocity])

    def process(self, entities):
        for position, travel, velocity in entities:
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


class ResourceTransport(Component):
    __slots__ = [
        '_common_route_resources', 'destination', 'direction', 'source'
    ]

    exposed_as = 'resource_transport'
    exposed_methods = ['on_end', 'start', 'stop']

    def __init__(self, owner):
        super().__init__(owner)

        self._common_route_resources = None
        self.destination = None
        self.direction = TRANSPORT_DIRECTION_SOURCE
        self.source = None

    def common_route_resources(self, destination=None):
        if destination is None:
            _destination = self.destination()
        else:
            _destination = destination

        is_planned_destination = (
            destination and
            self.destination and
            destination == self.destination()
        )

        if (
            (is_planned_destination or destination is None)
            and self._common_route_resources
        ):
            return self._common_route_resources

        accepted_resources = [
            r for (r, s) in _destination.storages.items()
            if s.allows_incoming
        ]

        destination_items = set(accepted_resources)
        worker_items = set(self.owner.resources.keys())

        self._common_route_resources = worker_items.intersection(
            destination_items
        )

        logger.debug(
            'common_route_items',
            owner=self.owner,
            component=self.__class__.__name__,
            common_resources=self._common_route_resources,
        )

        return self._common_route_resources

    def is_valid_route(self, destination=None):
        return not len(self.common_route_items(destination)) == 0

    def position(self):
        return self.owner.position

    def start(self, destination):
        if self.destination:
            raise RuntimeError('already going somewhere')

        self.destination = weakref.ref(destination)

    def stop(self):
        super().stop()
        self.destination = None
        self.source = None
        self._common_route_resources = None

    @classmethod
    def target_components(self):
        return None


class ResourceTransportSystem:
    component_types = set([ResourceTransport, Travel])

    def process(self, entities):
        for resource_transport, _travel in entities:
            if resource_transport.state == STATE_IDLE:
                self.handle_idle(resource_transport)
                continue

            if resource_transport.state == STATE_LOADING:
                self.handle_loading(resource_transport)
                continue

            if resource_transport.state == STATE_UNLOADING:
                self.handle_unloading(resource_transport)
                continue

            if resource_transport.state == STATE_MOVING:
                self.handle_movement(resource_transport)
                continue

    def handle_idle(self, resource_transport):
        if not resource_transport.source:
            return

        source = resource_transport.source()
        if not source:
            return

        resources = resource_transport.common_route_items()

        if not source.inventory.available_for_transport(resources):
            return

        if not resource_transport.position() == source.position():
            resource_transport.state_change(STATE_MOVING)
            resource_transport.owner.travel.start(source)
            return

        self.state_change(STATE_LOADING)

    def handle_loading(self, resource_transport):
        source = resource_transport.source()
        if not source:
            self.state_change(STATE_IDLE)

        if not resource_transport.position() == source.position():
            self.state_change(STATE_IDLE)
            return

        resources = resource_transport.common_route_items()
        routing = source.inventory_routing

        resource = routing.available_for_transport(resources)
        if not resource:
            resource_transport.state_change(STATE_IDLE)
            return

        storage = resource_transport.resources[resource]

        accepted = []

        while not storage.is_full():
            item = routing.remove_inventory(resource)
            if not item:
                break

            storage.add(item)
            accepted.append(item)

        logger.debug(
            'handle_loading',
            accepted=accepted,
            source=source,
            owner=resource_transport.owner,
            system=self.__class__.__name__,
        )

        resource_transport.direction = TRANSPORT_DIRECTION_DESTINATION
        if not resource_transport.destination:
            resource_transport.state_change(STATE_IDLE)
            return

        destination = resource_transport.destination()
        if not destination:
            resource_transport.destination = None
            resource_transport.state_change(STATE_IDLE)
            return

        resource_transport.owner.travel.start(destination)

    def handle_movement(self, resource_transport):
        if self.direction == TRANSPORT_DIRECTION_SOURCE:
            if not resource_transport.source:
                resource_transport.state_change(STATE_IDLE)
                return

            source = resource_transport.source()
            if resource_transport.position() == source.position():
                resource_transport.state_change(STATE_LOADING)
                return
        else:
            if not resource_transport.destination:
                resource_transport.state_change(STATE_IDLE)
                return

            destination = resource_transport.destination()

            if not destination:
                resource_transport.destination = None
                resource_transport.state_change(STATE_IDLE)
                return

            if resource_transport.position() == destination.position():
                resource_transport.state_change(STATE_UNLOADING)
                return

    def handle_unloading(self, resource_transport):
        if not resource_transport.destination:
            resource_transport.state_change(STATE_IDLE)
            resource_transport.destination = None
            return

        destination = resource_transport.destination()
        if not destination:
            resource_transport.state_change(STATE_IDLE)
            resource_transport.destination = None
            return

        if not resource_transport.position() == destination.position:
            raise RuntimeError(
                'we are trying to unload while not at destination'
            )
            return

        if not destination.can_receive_resources():
            return

        resources = resource_transport.common_route_resources()

        accepted = []
        rejected = []

        for resource in resources:
            storage = resource_transport.resources[resource]

            while not storage.is_empty():
                item = storage.pop()
                if item.__class__ not in resources:
                    rejected.append(item)
                    continue

                if destination.receive_resource(item):
                    accepted.append(item)
                    continue

            rejected.append(item)

        for item in rejected:
            storage.add(item)

        logger.debug(
            'handle_unloading',
            accepted=accepted,
            rejected=rejected,
            destination=destination,
            owner=resource_transport.owner,
            component=resource_transport,
            system=self.__class__.__name__,
        )

        resource_transport.direction = TRANSPORT_DIRECTION_SOURCE
        resource_transport.state_change(STATE_IDLE)

        if resource_transport.source:
            source = resource_transport.source()

            if source:
                resource_transport.owner.travel.start(source)
            else:
                resource_transport.source = None
