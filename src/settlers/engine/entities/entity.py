from ..components import Components


class Entity:
    def __init__(self):
        self.components = Components(self)

    def initialize(self):
        self.components.initialize()
