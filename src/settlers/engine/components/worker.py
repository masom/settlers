import structlog
from typing import Callable, List, Optional, Protocol
import weakref

from settlers.engine.entities.position import Position

from . import Component, ComponentManager

STATE_IDLE: str = "idle"
STATE_ACTIVE: str = "active"

logger = structlog.get_logger("engine.worker")


class Worksite(Protocol):
    def can_add_worker(self) -> bool: ...
    def add_worker(self, worker: object) -> bool: ...


class Worker(Component):
    __slots__ = ("_on_end_callbacks", "pipeline", "progress", "state", "workplace")

    def __init__(self, owner: object) -> None:
        super().__init__(owner)

        self.state: str = STATE_IDLE
        self.pipeline: Optional[list] = None
        self.progress: int = 0
        self.workplace: Optional[weakref.ReferenceType] = None
        self._on_end_callbacks: List[Callable] = []

    def can_work(self) -> bool:
        if not self.workplace:
            return False

        workplace = self.workplace()
        if not workplace:
            return False

        workplace_position = ComponentManager.fetch(workplace.owner_id(), Position)
        my_position = ComponentManager.fetch(self.owner_id(), Position)

        return workplace_position == my_position

    def is_active(self) -> bool:
        if not self.can_work():
            return False

        return self.state == STATE_ACTIVE

    def on_end(self, callback: Callable) -> None:
        self._on_end_callbacks.append(callback)

    def start(self, target: Worksite) -> bool:
        if self.workplace:
            raise RuntimeError("already working")

        if not target.can_add_worker():
            logger.debug(
                "start_target_rejected",
                target=target,
                owner=self.owner,
                component=self.__class__.__name__,
            )
            return False

        logger.debug(
            "start_requested",
            target=target,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        if not target.add_worker(self):
            return False

        self.workplace = weakref.ref(target)
        return True

    def state_change(self, new_state: str) -> None:
        if self.state == new_state:
            return

        logger.debug(
            "state_change",
            old_state=self.state,
            new_state=new_state,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.state = new_state

    def stop(self, skip_idle_state=False) -> None:
        self.state_change(STATE_IDLE)

        for callback in self._on_end_callbacks:
            callback(self)

        if self.workplace:
            workplace = self.workplace()
            if workplace:
                workplace.remove_worker(self)

            self.workplace = None

        logger.info(
            "stop",
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self._on_end_callbacks = []

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self)),
        )
