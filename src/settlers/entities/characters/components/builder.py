import weakref

from settlers.entities.components import Component


BUILDER_ABILITY_CARPENTER = 'carpenter'

STATE_IDLE = 'idle'
STATE_BUILDING = 'building'


class BuilderProxy:
    __slots__ = ['_builder', '_target', '__weakref__']

    def __init__(self, builder, target):
        self._builder = weakref.ref(builder)
        self._target = weakref.ref(target)

    def begin_building(self):
        builder = self._builder()
        if not builder:
            return None

        builder.begin_building()

    def can_build(self):
        builder = self._builder()
        target = self._target()

        if not target.position == self.position():
            return False

        if not builder.state == STATE_BUILDING:
            builder.state_change(STATE_BUILDING)

        return True

    def notify_of_building_completion(self, building):
        builder = self._builder()
        if not builder:
            return None

        print(
            "{builder}: we built {building}.".format(
                builder=builder,
                building=building,
            )
        )

        builder.state_change(STATE_IDLE)

    def position(self):
        harvester = self._harvester()
        return harvester.owner.position

    def stop_building(self):
        target = self._target()
        if not target:
            return

        target.progress_stopped()


class Builder(Component):
    __slots__ = ['abilities', 'proxy', 'state']

    exposed_as = 'builder'
    exposed_methods = ['build']

    def __init__(self, owner, abilities):
        super().__init__(owner)

        self.abilities = abilities
        self.proxy = None
        self.state = STATE_IDLE

    def build(self, target):
        if self.proxy:
            raise RuntimeError('already allocated to a target')

        if target.construction.requires() not in self.abilities:
            raise RuntimeError('cannot build')

        print("{owner}#{component}: Building {target}".format(
                owner=self.owner,
                component=self.__class__.__name__,
                target=target
            )
        )

        target.harvesting.add_harvester(self.proxy)

        self.proxy = BuilderProxy.new(self, target)
        target.construction.add_builder(self.oroxy)

    def begin_building(self):
        if self.state == STATE_BUILDING:
            return

        self.state_change(STATE_BUILDING)

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

        if new_state == STATE_BUILDING:
            destination = self.destination()
            self.owner.mouvement.travel_to(destination)
            return
