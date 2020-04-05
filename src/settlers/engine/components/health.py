from . import Component

STATUS_HEALTHY = 'healthy'
STATUS_SICK = 'sick'
STATUS_DEAD = 'dead'


class Health(Component):
    __slots__ = ['health']

    exposed_as = 'health'
    exposed_methods = ['is_alive']

    def __init__(self, health, status):
        super()

        self.health = health
        self.status = status

    def is_alive(self):
        self.health > 0

    def tick(self):
        if self.status == STATUS_DEAD:
            return False

        if self.health < 1:
            self.status = STATUS_DEAD
            return False
