import weakref

from settlers.entities.components import Component

TRANSPORT_DIRECTION_SOURCE = 'source'
TRANSPORT_DIRECTION_DESTINATION = 'destination'


class TransporterProxy:
    __slots__ = [
        '_common_route_items',
        'destination', 'source', 'ticks', 'worker'
    ]

    def __init__(self, worker, source):
        self._common_route_items = None
        self.destination = None
        self.source = weakref.ref(source)
        self.ticks = 0
        self.worker = weakref.ref(worker)

    def common_route_items(self, destination=None):
        if destination is None:
            destination = self.destination()

        worker = self.worker()

        if self._common_route_items is None:
            accepted_resources = [
                r for (r, s) in destination.storages.items()
                if s.allows_incoming
            ]

            destination_items = set(accepted_resources)
            worker_items = set(worker.resources.keys())

            self._common_route_items = worker_items.intersection(
                destination_items
            )

            print("{self}#{component} matching items: {items}".format(
                    self=worker,
                    component=self.__class__.__name__,
                    items=self._common_route_items,
                )
            )
        return self._common_route_items

    def assign_destination(self, destination):
        self.destination = weakref.ref(destination)

    def tick(self):
        worker = self.worker()

        if not worker:
            self.implode()
            return

        self.ticks += 1

    def _implode(self):
        self._destination = None
        self._source = None
        self._worker = None

    def is_valid_route(self, destination=None):
        return not len(self.common_route_items(destination)) == 0


STATE_IDLE = 'idle'
STATE_TRANSPORTING = 'transporting'


class Transport(Component):
    __slots__ = [
        'current_distance', 'direction', 'distance',
        'proxy', 'resources', 'state'
    ]

    exposed_as = 'transport'
    exposed_methods = ['pickup_from', 'assign_destination']

    def __init__(self, owner, resources):
        super().__init__(owner)

        self.current_distance = 0
        self.direction = TRANSPORT_DIRECTION_SOURCE
        self.distance = 0
        self.proxy = None
        self.resources = resources
        self.state = STATE_IDLE

    def pickup_from(self, source):
        if self.proxy:
            raise RuntimeError('already assigned')

        self.proxy = TransporterProxy(self, source)

    def assign_destination(self, destination):
        if not self.proxy.is_valid_route(destination):
            raise RuntimeError('Invalid route')
        self.proxy.assign_destination(destination)

    def handle_idle_tick(self, source):
        resources = self.proxy.common_route_items()

        if source.inventory_routing().available_for_transport(resources):
            self.state_change(STATE_TRANSPORTING)

    def handle_transport_tick(self, destination, source):
        worker = self.proxy.worker()

        if self.direction == TRANSPORT_DIRECTION_SOURCE:
            if not worker.position() == source.position:
                return

            resources = self.proxy.common_route_items()
            routing = source.inventory_routing()
            resource = routing.available_for_transport(resources)

            if not resource:
                self.state_change(STATE_IDLE)
                return

            storage = self.resources[resource]

            accepted = []
            while not storage.is_full():
                item = routing.remove_inventory(resource)
                if not item:
                    break

                storage.add(item)
                accepted.append(item)

            print(
                "{self}#{component} accepted {accepted} from {source}".format(
                    accepted=accepted,
                    self=worker,
                    component=self.__class__.__name__,
                    source=source,
                )
            )

            self.direction = TRANSPORT_DIRECTION_DESTINATION
            if destination:
                self.owner.mouvement.travel_to(destination)
        else:
            if not worker.position() == destination.position:
                return

            if not destination.can_receive_resources():
                return

            print(
                "{self}#{component} transported"
                " from {source} to {destination}".format(
                    self=worker,
                    component=self.__class__.__name__,
                    source=source,
                    destination=destination,
                )
            )

            resources = self.proxy.common_route_items()

            accepted = []
            rejected = []

            for resource in resources:
                storage = self.resources[resource]
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

            print(
                "{self}#{component}"
                " accepted: {accepted}, rejected: {rejected}".format(
                    self=self,
                    component=self.__class__.__name__,
                    accepted=accepted,
                    rejected=rejected,
                )
            )
            self.direction = TRANSPORT_DIRECTION_SOURCE
            if source:
                self.owner.mouvement.travel_to(source)

    def position(self):
        return self.owner.position

    def state_change(self, new_state):
        if self.state == new_state:
            return

        print(
            "{owner}#{component} state change:"
            " {old_state} -> {new_state}".format(
                owner=self.owner,
                component=self.__class__.__name__,
                old_state=self.state,
                new_state=new_state
            )
        )
        self.state = new_state

        if self.state == STATE_TRANSPORTING:
            if self.direction == TRANSPORT_DIRECTION_SOURCE:
                destination = self.proxy.source()
            else:
                destination = self.proxy.destination()

            self.owner.mouvement.travel_to(destination)
            return

    def tick(self):
        if not self.proxy:
            return

        if self.proxy.destination:
            destination = self.proxy.destination()
        source = self.proxy.source()

        if not destination:
            self.state_change(STATE_IDLE)
            return

        if self.state == STATE_IDLE:
            self.handle_idle_tick(source)
            return

        if self.state == STATE_TRANSPORTING:
            self.handle_transport_tick(destination, source)
            return

    def __repr__(self):
        return "<{owner}#{klass} {id}>".format(
            klass=self.__class__.__name__,
            owner=self.owner,
            id=hex(id(self)),
        )
