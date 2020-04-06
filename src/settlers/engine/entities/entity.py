from ..components import Components
from .position import Position


class Entity:
    components = [(Position, -1, -1)]

    def __init__(self):
        self.components = Components(self)

    def initialize(self):
        self.components.initialize()
