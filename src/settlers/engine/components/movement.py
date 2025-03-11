import inspect
import math
import structlog
from typing import List, Optional, Tuple, Type
import weakref
from collections import deque
import inspect

from . import Component, ComponentManager
from ..entities.entity import Entity
from ..entities.position import Position
from ..entities.resources.resource_storage import ResourceStorage

STATE_IDLE = "idle"
STATE_MOVING = "moving"
STATE_LOADING = "loading"
STATE_UNLOADING = "unloading"

logger = structlog.get_logger("engine.movement")


class Velocity(Component):
    __slots__ = ["speed"]

    def __init__(self, owner, speed: int = 1):
        super().__init__(owner)
        self.speed: int = speed


DIRECTION_UP: str = "up"
DIRECTION_DOWN: str = "down"
DIRECTION_LEFT: str = "left"
DIRECTION_RIGHT: str = "right"

TRANSPORT_DIRECTION_SOURCE: str = "source"
TRANSPORT_DIRECTION_DESTINATION: str = "destination"


class Travel(Component):
    __slots__ = ["destination", "past"]

    def __init__(self, owner) -> None:
        super().__init__(owner)
        self.past = deque(maxlen=10)

        self.destination: Optional[weakref.ReferenceType[Entity]] = None

    def stuck_detection(self) -> None:
        if self.destination:
            self.past.append(self.destination())

        if len(self.past) < 3:
            return

        same = set(self.past)
        if len(same) == 1:
            import pdb

            pdb.set_trace()

    def start(self, destination: Entity) -> None:
        if self.destination:
            logger.error(
                "start_failed_destination_set",
                component=self.__class__.__name__,
                owner=self.owner,
                destination=self.destination(),
                proposed_destination=destination,
            )
            raise RuntimeError("already moving somewhere")

        caller = inspect.stack()[1]

        logger.debug(
            "start",
            component=self.__class__.__name__,
            caller=caller,
            owner=self.owner,
            destination=destination,
        )
        self.destination = weakref.ref(destination)
        self.state_change(STATE_MOVING)
        self.stuck_detection()

    def stop(self, skip_idle_state=False) -> None:
        caller = inspect.stack()[1]
        logger.debug(
            "stop",
            caller=caller,
            owner=self.owner,
        )
        self.stuck_detection()
        self.destination = None
        super().stop(skip_idle_state)


class TravelSystem:
    """
    The TravelSystem is responsible for moving components in the game.

    It looks for entities that have `Travel`, `Position`, and `Velocity` components attached.
    """

    component_types: Tuple[Type[Component], Type[Component], Type[Component]] = (
        Travel,
        Position,
        Velocity,
    )

    def process(self, tick: int, entities: List[List[Component]]) -> None:
        travel: Travel
        position: Position
        velocity: Velocity

        # Ignoring types is required here as kinda need generics + type casting down
        # to the actual types to use for completion.
        for travel, position, velocity in entities:  # type: ignore
            if travel.state == STATE_IDLE and not travel.destination:
                continue

            if not travel.destination:
                travel.state_change(STATE_IDLE)
                continue

            destination = travel.destination()

            if not destination:
                logger.debug(
                    "process_destination_dead",
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
                destination_position: Position = ComponentManager.fetch(
                    destination.id(), Position
                )

                if destination_position == position:
                    logger.debug(
                        "process_destination_reached",
                        destination=destination,
                        owner=travel.owner,
                        system=self.__class__.__name__,
                    )

                    travel.stop()
                    continue

                delta_x: int = destination_position.x - position.x
                delta_y: int = destination_position.y - position.y

                distance: float = math.sqrt(math.pow(delta_x, 2) + math.pow(delta_y, 2))

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
    __slots__ = ("_common_route_resources", "destination", "direction", "source")

    def __init__(self, owner: Entity) -> None:
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
            destination is not None
            and self.destination is not None
            and destination == self.destination()
        )

        if (
            is_planned_destination or destination is None
        ) and self._common_route_resources:
            return self._common_route_resources or set()

        if not _destination:
            return set()

        accepted_resources = [
            r for (r, s) in _destination.storages.items() if s.allows_incoming
        ]

        destination_items = set(accepted_resources)

        # TODO Here we assume the workers already have items, that they are not going to get new ones...
        worker_items = set(self.owner.storages.keys())

        self._common_route_resources = worker_items.intersection(destination_items)

        logger.debug(
            "common_route_resources",
            owner=self.owner,
            component=self.__class__.__name__,
            common_resources=self._common_route_resources,
        )

        return self._common_route_resources or set()

    def is_valid_route(self, destination=None) -> bool:
        return not len(self.common_route_resources(destination)) == 0

    def position(self) -> Position:
        return self.owner.position

    def start(self, destination: Entity, source: Entity = None) -> None:
        if self.destination:
            raise RuntimeError("already going somewhere")

        if source:
            self.source = weakref.ref(source)
        else:
            self.source = None

        self.destination = weakref.ref(destination)

    def stop(self, skip_idle_state=False) -> None:
        super().stop(skip_idle_state=skip_idle_state)

        caller = caller = inspect.stack()[1]
        logger.debug(
            "stop",
            caller=caller,
        )
        travel: Travel = ComponentManager.fetch(self.owner.id(), Travel)
        travel.stop()

        self.destination = None
        self.source = None
        self._common_route_resources = None

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self)),
            source=self.source,
            destination=self.destination,
        )


class ResourceTransportSystem:
    component_types = (ResourceTransport, Travel)

    def process(self, tick: int, entities: list[list[Component]]) -> None:
        if tick % 2 == 1:
            return

        resource_transport: ResourceTransport
        travel: Travel

        for resource_transport, travel in entities:  # type: ignore
            if resource_transport.state == STATE_IDLE:
                self.handle_idle(resource_transport, travel)
                continue

            if resource_transport.state == STATE_LOADING:
                self.handle_loading(resource_transport, travel)
                continue

            if resource_transport.state == STATE_UNLOADING:
                self.handle_unloading(resource_transport, travel)
                continue

            if resource_transport.state == STATE_MOVING:
                self.handle_movement(resource_transport, travel)
                continue

            import pdb

            pdb.set_trace()
            raise RuntimeError

    def handle_idle(
        self, resource_transport: ResourceTransport, travel: Travel
    ) -> None:
        if not resource_transport.source:
            return

        source = resource_transport.source()
        if not source:
            resource_transport.stop()
            return

        resources: set = resource_transport.common_route_resources()

        if not source.inventory.available_for_transport(resources):
            return

        if not resource_transport.position() == source.position:
            resource_transport.direction = TRANSPORT_DIRECTION_SOURCE
            resource_transport.state_change(STATE_MOVING)
            travel.start(source, inspect.currentframe().f_code.co_name)
            return

        resource_transport.state_change(STATE_LOADING)

    def handle_loading(
        self, resource_transport: ResourceTransport, travel: Travel
    ) -> None:
        if not resource_transport.source:
            resource_transport.stop()
            return

        source = resource_transport.source()
        if not source:
            resource_transport.stop()
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
            "handle_loading",
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
            # TODO HERE MIGHT BE BUG?
            logger.debug(
                "handle_loading.no_destination",
                resource_transport=resource_transport,
                source=source,
                owner=resource_transport.owner,
                system=self.__class__.__name__,
            )
            resource_transport.stop()
            return

        resource_transport.state_change(STATE_MOVING)
        travel.start(destination)

    def handle_movement(
        self, resource_transport: ResourceTransport, worker_travel: Travel
    ) -> None:
        if resource_transport.direction == TRANSPORT_DIRECTION_SOURCE:
            if not resource_transport.source:
                resource_transport.stop()
                return

            source = resource_transport.source()
            import pdb

            pdb.set_trace()
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

    def handle_unloading(
        self, resource_transport: ResourceTransport, travel: Travel
    ) -> None:
        if not resource_transport.destination:
            resource_transport.stop()
            return

        destination = resource_transport.destination()
        if not destination:
            resource_transport.stop()
            return

        position: Position = resource_transport.position()

        if not position == destination.position:
            logger.debug(
                "resource_transport.handle_unloading.not_at_destination",
                resource_transport=resource_transport,
                position=position,
                destination=destination,
            )

            raise RuntimeError("we are trying to unload while not at destination")
            return

        if not destination.inventory.can_receive_resources():
            logger.debug(
                "handle_unloading:cannot_receive_resources",
                source=resource_transport.source,
                destination=destination,
                owner=resource_transport.owner,
                system=self.__class__.__name__,
                component=resource_transport,
            )

            resource_transport.destination = None
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
            "handle_unloading",
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
                "handle_unloading:nothing_accepted",
                destination=destination,
                owner=resource_transport.owner,
                component=resource_transport,
                system=self.__class__.__name__,
            )
            resource_transport.stop()
        else:
            resource_transport.destination = None

        if resource_transport.source:
            source = resource_transport.source()

            if source:
                travel.start(source)
            else:
                resource_transport.source = None
