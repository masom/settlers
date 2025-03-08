# -*- coding: utf-8 -*-

import random
import structlog
from collections import defaultdict
from typing import Callable, List, Optional

from settlers.engine.components import Component, ComponentProxy, ComponentManager

logger = structlog.get_logger("game.fauna_ai")

STATE_IDLE = "idle"
STATE_WANDERING = "wandering"
STATE_SLEEPING = "sleeping"
STATE_FLEEING = "fleeing"
STATE_ATTACKING = "attacking"
STATE_DEAD = "dead"


class Prey(Component):
    pass


class Predator(Component):
    pass


class FaunaAi(Component):
    __slots__ = ("_available_tasks", "state", "task")

    def __init__(self, owner, task=Prey) -> None:
        super().__init__(owner)
        self.state = STATE_IDLE
        self.task = task
        self._available_tasks = []

    def available_tasks(self, supported_tasks: list[Component]):
        if self._available_tasks:
            return self._available_tasks

        for task in supported_tasks:
            if task in self.owner.components.classes():
                self._available_tasks.append(task)

        return self._available_tasks

    def on_task_ended(self, component: Component) -> None:
        logger.info("on_task_ended", component=component)
        self.task = None
        self.state_change(STATE_IDLE)

    def state_change(self, new_state: str) -> None:
        if self.state == new_state:
            return

        logger.debug(
            "state_change",
            owner=self.owner,
            component=self,
            old_state=self.state,
            new_state=new_state,
            task=self.task,
        )

        self.state = new_state

    def __repr__(self) -> str:
        return "<{self} {id}>".format(self=self.__class__.__name__, id=hex(id(self)))


class FaunaAiSystem:
    component_types = [FaunaAi]

    def __init__(self, world: object) -> None:
        self.tasks: List[Component] = [
            Predator,
            Prey,
        ]

        self.entities = world.entities
        self._awaiting_until: dict = {}

    def handle_dead(self, entity: FaunaAi):
        pass

    def handle_wandering(self, entity: FaunaAi):
        pass

    def handle_idle(self, entity: FaunaAi):
        if entity.task is Prey:
            return
        if entity.task is Predator:
            return

        if entity.task is None:
            logger.error("handle_idle", entity=entity, task=entity.task)
            raise ValueError("Task is None")

    def handle_sleeping(self, entity: FaunaAi):
        pass

    def handle_fleeing(self, entity: FaunaAi):
        pass

    def handle_attacking(self, entity: FaunaAi):
        pass

    def process(self, tick: int, animals: List[FaunaAi]) -> None:
        self.current_tick = tick

        if self.current_tick % 10 != 0:
            return

        for animal in animals:
            if animal.state == STATE_DEAD:
                self.handle_dead(animal)
                continue

            if animal.state == STATE_IDLE:
                self.handle_idle(animal)
                continue

            if animal.state == STATE_WANDERING:
                self.handle_wandering(animal)
                continue

            if animal.state == STATE_SLEEPING:
                self.handle_sleeping(animal)
                continue

            if animal.state == STATE_FLEEING:
                self.handle_fleeing(animal)
                continue

            if animal.state == STATE_ATTACKING:
                self.handle_attacking(animal)
                continue

            raise ValueError(f"Unknown state: {animal.state}")
