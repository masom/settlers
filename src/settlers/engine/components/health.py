from . import Component

STATUS_HEALTHY = "healthy"
STATUS_SICK = "sick"
STATUS_DEAD = "dead"


class Health(Component):
    __slots__ = ("health", "status")

    def __init__(self, health: int, status: str):
        super()

        self.health = health
        self.status = status
