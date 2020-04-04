import weakref

from settlers.entities.components import Component


class HarvesterProxy:
    __slots__ = ['_harvester', '_target', '__weakref__']

    def __init__(self, harvester, target):
        self._harvester = weakref.ref(harvester)
        self._target = weakref.ref(target)

    def can_harvest(self):
        harvester = self._harvester()
        target = self._target()

        if not target.position == self.position():
            return False

        if harvester.storage.is_full():
            return False

        if harvester.state == STATE_DELIVERING:
            return False

        if not harvester.state == STATE_HARVESTING:
            harvester.state_change(STATE_HARVESTING)

        return True

    def begin_harvesting(self):
        harvester = self._harvester()
        if not harvester:
            return None

        harvester.begin_harvesting()

    def notify_of_harvest(self, resources):
        harvester = self._harvester()
        if not harvester:
            return None

        carrying = 0

        for resource in resources:
            added = harvester.storage.add(resource)
            if added:
                carrying += 1
            else:
                break

        print(
            "{harvester}: we got a harvest of {resources}."
            " Carrying {carrying} out of {total}!".format(
                carrying=carrying,
                total=len(resources),
                harvester=harvester,
                resources=resources,
            )
        )

        if harvester.storage.is_full():
            harvester.begin_delivery()

        return carrying

    def position(self):
        harvester = self._harvester()
        return harvester.owner.position

    def stop_harvesting(self):
        target = self._target()
        if not target:
            return

        target.harvester_stopped()


STATE_DELIVERING = 'delivering'
STATE_HARVESTING = 'harvesting'
STATE_IDLE = 'idle'


class Harvester(Component):
    __slots__ = ['destination', 'proxy', 'resources', 'state', 'storage']

    exposed_as = 'harvesting'
    exposed_methods = ['assign_destination', 'harvest']
    requires = ['mouvement']

    def __init__(self, owner, resources, storage):
        super().__init__(owner)

        self.destination = None
        self.state = STATE_IDLE
        self.proxy = None
        self.resources = resources
        self.storage = storage

    def harvest(self, target):
        if self.proxy:
            raise RuntimeError('already allocated to a target')

        if target.harvesting.provides() not in self.resources:
            raise RuntimeError('cannot harvest')

        print("{owner}: Harvesting {target}".format(
                owner=self.owner,
                target=target
            )
        )

        self.proxy = HarvesterProxy(self, target)
        target.harvesting.add_harvester(self.proxy)

    def assign_destination(self, building):
        self.destination = weakref.ref(building)

    def begin_delivery(self):
        if self.state == STATE_DELIVERING:
            return

        if not self.destination:
            raise RuntimeError('no destination')

        destination = self.destination()
        if not destination:
            raise RuntimeError('destination dead')

        self.state_change(STATE_DELIVERING)

    def begin_harvesting(self):
        if self.state == STATE_HARVESTING:
            return

        self.state_change(STATE_HARVESTING)

    def deliver(self):
        self.state_change(STATE_IDLE)

        destination = self.destination()

        if not destination.position == self.owner.position:
            raise RuntimeError('not yet at destination')

        delivered = []
        kept = []
        for resource in self.storage:
            input_storage = destination.storage_for(resource)
            if not input_storage:
                continue

            if input_storage.add(resource):
                delivered.append(resource)
                self.storage.remove(resource)
            else:
                kept.append(resource)
                print(
                    "{owner}#{component} cannot deliver {resource} to"
                    " {destination} storage {destination_storage}".format(
                        component=self,
                        owner=self.owner,
                        destination=destination,
                        destination_storage=input_storage
                    )
                )
        print(
            "{owner}#{component} delivered: {delivered} and"
            " kept: {kept}".format(
                owner=self.owner,
                component=self,
                delivered=delivered,
                kept=kept
            )
        )

    def stop(self):
        self.state_change(STATE_IDLE)

        if not self.proxy:
            raise

        self.proxy.stop_harvesting()
        self.proxy = None

    def state_change(self, new_state):
        if self.state == new_state:
            return

        print(
            "{owner}#{component} state change:"
            " {old_state} -> {new_state}".format(
                owner=self.owner,
                component=self,
                old_state=self.state,
                new_state=new_state
            )
        )
        self.state = new_state

        if new_state == STATE_DELIVERING:
            destination = self.destination()
            self.owner.mouvement.travel_to(destination)
            return

    def tick(self):
        if self.state == STATE_HARVESTING:
            return

        if self.state == STATE_DELIVERING:
            destination = self.destination()
            if not destination:
                raise RuntimeError('destination dead')

            if destination.position == self.owner.position:
                self.deliver()

                target = self.proxy._target()
                self.owner.mouvement.travel_to(target)
