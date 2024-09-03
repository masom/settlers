import math
import structlog
from typing import List, Optional
import weakref

from . import Component
from ..entities.position import Position
from ..entities.resources.resource_storage import ResourceStorage
STATE_IDLE = 'idle'
STATE_MOVING = 'moving'
STATE_LOADING = 'loading'
STATE_UNLOADING = 'unloading'

logger = structlog.get_logger('engine.movement')


class Velocity(Component):
    __slots__ = ['speed']

    def __init__(self, owner, speed: int = 1):
        super().__init__(owner)
        self.speed: int = speed


DIRECTION_UP: str = 'up'
DIRECTION_DOWN: str = 'down'
DIRECTION_LEFT: str = 'left'
DIRECTION_RIGHT: str = 'right'

TRANSPORT_DIRECTION_SOURCE: str = 'source'
TRANSPORT_DIRECTION_DESTINATION: str = 'destination'


class Travel(Component):
    __slots__ = ('destination')

    exposed_as = 'travel'
    exposed_methods = ('destination', 'on_end', 'start', 'stop')

    def __init__(self, owner) -> None:
        super().__init__(owner)

        self.destination: Optional[weakref.ReferenceType] = None

    def start(self, destination) -> None:
        if self.destination:
            logger.error(
                'start_failed_destination_set',
                component=self.__class__.__name__,
                owner=self.owner,
                destination=self.destination(),
                proposed_destination=destination,
            )
            raise RuntimeError('already moving somewhere')

        self.destination = weakref.ref(destination)
        self.state_change(STATE_MOVING)

    def stop(self) -> None:
        super().stop()
        self.destination = None
        self.state_change(STATE_IDLE)


class TravelSystem:
    component_types: list = [Travel, Position, Velocity]

    def process(self, tick: int, entities: List[List[Component]]) -> None:
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

                travel.stop()
                continue

            if travel.state == STATE_IDLE:
                travel.state_change(STATE_MOVING)
                continue

            if travel.state == STATE_MOVING:
                if destination.position == travel.owner.position:
                    travel.stop()
                    continue

                destination_position: Position = destination.position.reveal(
                    Position
                )

                delta_x: int = destination_position.x - position.x
                delta_y: int = destination_position.y - position.y

                distance: float = math.sqrt(
                    math.pow(delta_x, 2)
                    + math.pow(delta_y, 2)
                )

                new_x: int = 0
                new_y: int = 0

                if distance > velocity.speed:
                    ratio: float = velocity.speed / distance
                    new_x = round((ratio * delta_x) + position.x)
                    new_y = round((ratio * delta_y) + position.y)
                else:
                    new_x = destination_position.x
                    new_y = destination_position.y

                position.x = new_x
                position.y = new_y


class ResourceTransport(Component):
    __slots__ = (
        '_common_route_resources', 'destination', 'direction', 'source'
    )

    exposed_as = 'resource_transport'
    exposed_methods = ('is_valid_route', 'on_end', 'start', 'stop')

    def __init__(self, owner) -> None:
        super().__init__(owner)

        self._common_route_resources: Optional[set] = None
        self.destination: Optional[weakref.ReferenceType] = None
        self.direction: str = TRANSPORT_DIRECTION_SOURCE
        self.source: Optional[weakref.ReferenceType] = None

    def common_route_resources(self, destination=None) -> set:
        if destination is None and self.destination:
            _destination = self.destination()
        else:
            _destination = destination

        is_planned_destination: bool = (
            destination is not None and
            self.destination is not None and
            destination == self.destination()
        )

        if (
            (is_planned_destination or destination is None)
            and self._common_route_resources
        ):
            return self._common_route_resources or set()
        
        if not _destination:
            return set()

        accepted_resources = [
            r for (r, s) in _destination.storages.items()
            if s.allows_incoming
        ]

        destination_items = set(accepted_resources)
        worker_items = set(self.owner.storages.keys())

        self._common_route_resources = worker_items.intersection(
            destination_items
        )

        logger.debug(
            'common_route_resources',
            owner=self.owner,
            component=self.__class__.__name__,
            common_resources=self._common_route_resources,
        )

        return self._common_route_resources or set()

    def is_valid_route(self, destination=None) -> bool:
        return not len(self.common_route_resources(destination)) == 0

    def position(self) -> Position:
        return self.owner.position

    def start(self, destination, source=None) -> None:
        if self.destination:
            raise RuntimeError('already going somewhere')

        if source:
            self.source = weakref.ref(source)
        else:
            self.source = None

        self.destination = weakref.ref(destination)

    def stop(self) -> None:
        super().stop()
        self.owner.travel.stop()
        self.destination = None
        self.source = None
        self._common_route_resources = None


class ResourceTransportSystem:
    component_types = [ResourceTransport, Travel]

    def process(self, tick: int, entities: list) -> None:
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

            import pdb; pdb.set_trace()
            raise RuntimeError

    def handle_idle(self, resource_transport: ResourceTransport) -> None:
        if not resource_transport.source:
            return

        source = resource_transport.source()
        if not source:
            return

        resources: set = resource_transport.common_route_resources()

        if not source.inventory.available_for_transport(resources):
            return

        if not resource_transport.position() == source.position:
            resource_transport.state_change(STATE_MOVING)
            resource_transport.owner.travel.start(source)
            return

        resource_transport.state_change(STATE_LOADING)

    def handle_loading(self, resource_transport: ResourceTransport) -> None:
        if not resource_transport.source:
            resource_transport.state_change(STATE_IDLE)
            return

        source = resource_transport.source()
        if not source:
            resource_transport.state_change(STATE_IDLE)
            return

        if not resource_transport.position() == source.position:
            resource_transport.state_change(STATE_IDLE)
            return

        resources = resource_transport.common_route_resources()
        routing = source.inventory

        resource = routing.available_for_transport(resources)
        if not resource:
            resource_transport.state_change(STATE_IDLE)
            return

        storage = resource_transport.owner.storages[resource]
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

        resource_transport.state_change(STATE_MOVING)
        resource_transport.owner.travel.start(destination)

    def handle_movement(self, resource_transport):
        if resource_transport.direction == TRANSPORT_DIRECTION_SOURCE:
            if not resource_transport.source:
                resource_transport.state_change(STATE_IDLE)
                return

            source = resource_transport.source()
            if resource_transport.position() == source.position:
                resource_transport.state_change(STATE_LOADING)
                return
        else:
            if not resource_transport.destination:
                resource_transport.stop()
                return

            destination = resource_transport.destination()

            if not destination:
                resource_transport.stop()
                return

            if resource_transport.position() == destination.position:
                resource_transport.state_change(STATE_UNLOADING)
                return

    def handle_unloading(self, resource_transport: ResourceTransport) -> None:
        if not resource_transport.destination:
            resource_transport.stop()
            return

        destination = resource_transport.destination()
        if not destination:
            resource_transport.stop()
            return

        if not resource_transport.position() == destination.position:
            raise RuntimeError(
                'we are trying to unload while not at destination'
            )
            return

        if not destination.inventory.can_receive_resources():
            return

        resources = resource_transport.common_route_resources()

        accepted: List[type] = []
        rejected: List[type] = []

        for resource in resources:
            # TODO: Check if receiver will want this.
            storage: ResourceStorage = resource_transport.owner.storages[resource]

            while not storage.is_empty():
                item = storage.pop()

                if item not in resources:
                    rejected.append(item)
                    continue

                if destination.inventory.receive_resource(item):
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

        source = None
        if resource_transport.source:
            source = resource_transport.source()

        if len(rejected) == resources and len(accepted) == 0:
            logger.debug(
                'handle_unloading:nothing_accepted',
                destination=destination,
                owner=resource_transport.owner,
                component=resource_transport,
                system=self.__class__.__name__,
            )
            resource_transport.stop()
        else:
            resource_transport.direction = TRANSPORT_DIRECTION_SOURCE
            resource_transport.state_change(STATE_MOVING)

        if resource_transport.source:
            source = resource_transport.source()

            if source:
                resource_transport.owner.travel.start(source)
            else:
                resource_transport.source = None
