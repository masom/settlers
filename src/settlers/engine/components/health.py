from . import Component

STATUS_HEALTHY = 'healthy'
STATUS_SICK = 'sick'
STATUS_DEAD = 'dead'


class Health(Component):
    __slots__ = ('health')

    exposed_as = 'health'
    exposed_methods = ('is_alive')

    def __init__(self, health: int, status: str):
        super()

        self.health = health
        self.status = status
