import weakref

from settlers.entities.components import Component


class HarvesterProxy:
    __slots__ = ['_harvester', '_target', '__weakref__']

    def __init__(self, harvester, target):
        self._harvester = weakref.ref(harvester)
        self._target = weakref.ref(target)

    def notify_of_harvest(self, resource, quantity):
        harvester = self._harvester()
        if not harvester:
            return None

        print("{harvester}: we got a harvest of {quantity} {resource}!".format(
                harvester=harvester,
                quantity=quantity,
                resource=resource,
            )
        )

        return True

    def position(self):
        harvester = self._harvester()
        harvester.owner.position

    def stop_harvesting(self):
        target = self._target()
        if not target:
            return

        target.harvester_stopped()


class Harvester(Component):
    __slots__ = ['proxy']

    exposed_as = 'harvesting'
    exposed_methods = ['harvest']

    def __init__(self, owner):
        super().__init__(owner)

        self.proxy = None

    def harvest(self, target):
        if self.proxy:
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
