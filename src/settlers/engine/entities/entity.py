from ..components import Components
from .position import Position


class Entity:
    components = []

    def __init__(self):
        self.components = Components(self)
        self.position = Position(-1, -1)

    def initialize(self):
        self.components.initialize()
