import structlog
import weakref

from . import Component

STATE_IDLE = 'idle'
STATE_ACTIVE = 'active'

logger = structlog.get_logger('engine.worker')


class Worker(Component):
    __slots__ = [
        '_on_end_callbacks', 'pipeline', 'progress', 'state', 'workplace'
    ]

    exposed_as = 'work'
    exposed_methods = ['on_end', 'start', 'stop']

    def __init__(self, owner):
        super().__init__(owner)

        self.state = STATE_IDLE
        self.pipeline = None
        self.progress = 0
        self.workplace = None
        self._on_end_callbacks = []

    def can_work(self):
        if not self.workplace:
            return False

        workplace = self.workplace()
        if not workplace:
            return False

        return workplace.position() == self.owner.position

    def is_active(self):
        if not self.can_work():
            return False

        return self.state == STATE_ACTIVE

    def on_end(self, callback):
        self._on_end_callbacks.append(callback)

    def start(self, target):
        if self.workplace:
            raise RuntimeError('already working')

        if not target.can_add_worker():
            logger.debug(
                'start_target_rejected',
                target=target,
                owner=self.owner,
                component=self.__class__.__name__,
            )
            return False

        logger.debug(
            'start_requested',
            target=target,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        if not target.add_worker(self):
            return False

        self.workplace = weakref.ref(target)
        return True

    def state_change(self, new_state):
        if self.state == new_state:
            return

        logger.debug(
            'state_change',
            old_state=self.state,
            new_state=new_state,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.state = new_state

    def stop(self):
        self.state_change(STATE_IDLE)

        for callback in self._on_end_callbacks:
            callback(self)

        if self.workplace:
            workplace = self.workplace()
            if workplace:
                workplace.remove_worker(self)

            self.workplace = None

        logger.info(
            'stop',
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self._on_end_callbacks = []

    def __repr__(self):
        return "<{owner}#{component} {id}".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self)),
        )
