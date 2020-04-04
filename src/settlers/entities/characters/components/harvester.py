import weakref

from settlers.entities.components import Component


class HarvesterProxy:
    __slots__ = ['_harvester', '_target', '__weakref__']

    def __init__(self, harvester, target):
        self._harvester = weakref.ref(harvester)
        self._target = weakref.ref(target)

    def can_harvest(self):
        harvester = self._harvester()
        return not harvester.storage.is_full()

    def notify_of_harvest(self, resources):
        harvester = self._harvester()
        if not harvester:
            return None

        for resource in resources:
            added = harvester.storage.add(resource)
            if not added:
                break

        print("{harvester}: we got a harvest of {resources}!".format(
                harvester=harvester,
                resources=resources,
            )
        )

        return True

    def position(self):
        harvester = self._harvester()
        return harvester.owner.position

    def stop_harvesting(self):
        target = self._target()
        if not target:
            return

        target.harvester_stopped()


class Harvester(Component):
    __slots__ = ['storage', 'proxy', 'resources']

    exposed_as = 'harvesting'
    exposed_methods = ['harvest']

    def __init__(self, owner, resources, storage):
        super().__init__(owner)

        self.proxy = None
        self.resources = resources
        self.storage = storage

    def harvest(self, target):
        if self.proxy:
            raise

        if target.harvesting.provides() not in self.resources:
            raise

        print("{owner}: Harvesting {target}".format(
                owner=self.owner,
                target=target
            )
        )

        self.proxy = HarvesterProxy(self, target)
        target.harvesting.add_harvester(self.proxy)

    def stop(self):
        if not self.proxy:
            raise

        self.proxy.stop_harvesting()
        self.proxy = None
